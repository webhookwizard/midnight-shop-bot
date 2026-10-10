"""The bot's brain: bilingual intent detection + a dialogue state machine.

Everything here runs offline on keyword scoring — no API keys, no network.
It is deliberately transparent: every decision (which intent won, which state
we are in) can be inspected, which is exactly what a shop owner wants from
a customer-facing bot at 2am.
"""

import re
from dataclasses import dataclass

from . import catalog
from .memory import OrderLog, Session

# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------

# Bilingual keyword lists. Each hit scores 1 point; the intent with the most
# points wins. Zero hits -> "fallback".
INTENT_KEYWORDS = {
    "greeting": ["在吗", "在么", "有人吗", "你好", "您好", "在不在", "hello", "hi", "hey"],
    "hours": ["营业", "开门", "关门", "几点", "营业时间", "hours", "open", "close"],
    "shipping": ["运费", "邮费", "快递", "发货", "几天到", "到货", "多久", "shipping", "delivery", "deliver"],
    "returns": ["退货", "退款", "换货", "refund", "return"],
    "price": ["价格", "多少钱", "贵", "便宜", "price", "cost", "how much"],
    "product": ["蜡烛", "candle", "香薰", "味道", "香味", "scent", "哪款", "推荐"],
    "order": ["买", "订", "购", "下单", "order", "buy", "purchase"],
    "confirm": ["好的", "可以", "确认", "是的", "没问题", "行", "yes", "ok"],
    "cancel": ["取消", "不要了", "算了", "不用了", "cancel"],
    "thanks": ["谢谢", "感谢", "多谢", "thanks", "thank"],
    "human": ["人工", "真人", "客服", "转人工", "human", "agent", "real person"],
    "bye": ["再见", "拜拜", "晚安", "bye", "good night", "goodnight"],
}

# Order states (the checkout flow)
IDLE = "IDLE"
ORDER_PRODUCT = "ORDER_PRODUCT"
ORDER_QTY = "ORDER_QTY"
ORDER_NAME = "ORDER_NAME"
ORDER_ADDRESS = "ORDER_ADDRESS"
ORDER_PHONE = "ORDER_PHONE"
ORDER_CONFIRM = "ORDER_CONFIRM"

CN_NUMERALS = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
               "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def _affirms(text: str) -> bool:
    """Does this read as 'yes' in the confirm step?"""
    if any(w in text for w in ("好的", "可以", "确认", "是的", "没问题", "行")):
        return True
    return re.search(r"\b(yes|ok|yeah|y)\b", text.lower()) is not None


def _denies(text: str) -> bool:
    """Does this read as 'no / cancel' in the confirm step?"""
    if any(w in text for w in ("不要", "取消", "算了", "不用")):
        return True
    return re.search(r"\b(no|cancel|nope)\b", text.lower()) is not None


@dataclass
class IntentResult:
    intent: str
    confidence: float   # 0.0–1.0, share of keyword hits (informational)
    product: "catalog.Product | None" = None


def detect_language(text: str) -> str:
    """'zh' if the message contains CJK characters, else 'en'."""
    return "zh" if re.search(r"[\u4e00-\u9fff]", text) else "en"


def detect_intent(text: str) -> IntentResult:
    lowered = text.lower()
    scores = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw.lower() in lowered)
        if hits:
            scores[intent] = hits
    if not scores:
        return IntentResult(intent="fallback", confidence=0.0)
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    return IntentResult(
        intent=best,
        confidence=round(scores[best] / total, 2),
        product=catalog.find_product(text),
    )


def parse_quantity(text: str):
    """Extract a purchase quantity: Arabic digits first, then Chinese numerals
    next to a measure word (只/个/份/件). Returns None if not found."""
    m = re.search(r"(\d+)", text)
    if m:
        return int(m.group(1))
    for char, value in CN_NUMERALS.items():
        if char in text and any(mw in text for mw in ("只", "个", "份", "件")):
            return value
    return None


# ---------------------------------------------------------------------------
# Dialogue manager
# ---------------------------------------------------------------------------

class DialogueManager:
    """Turns intents + order state into replies. Owns the checkout flow."""

    def __init__(self, order_log: OrderLog | None = None) -> None:
        self.order_log = order_log or OrderLog()

    # -- entry point ------------------------------------------------------

    def respond(self, session: Session, text: str, hour: int) -> str:
        text = text.strip()
        if not session.history:  # first message sets the language for the session
            session.language = detect_language(text)
        session.history.append(("customer", text))

        if session.state != IDLE:
            reply = self._continue_order(session, text)
        else:
            result = detect_intent(text)
            result._raw = text  # stash for entity extraction in handlers
            if result.product:  # remember what they asked about — used at checkout
                session.cart["last_product_id"] = result.product.id
            reply = self._dispatch(session, result, text, hour)

        session.history.append(("bot", reply))
        return reply

    # -- idle intents -----------------------------------------------------

    def _dispatch(self, session: Session, result: IntentResult, text: str, hour: int) -> str:
        zh = session.language == "zh"
        # Smart routing: a quantity plus a product they asked about earlier
        # ("那我要两只吧" right after the lavender price) is an order even
        # without explicit order keywords.
        if (result.intent == "fallback"
                and parse_quantity(text)
                and session.cart.get("last_product_id")):
            result = IntentResult(
                intent="order", confidence=0.6,
                product=self._product_by_id(session.cart["last_product_id"]),
            )
            result._raw = text
        handler = {
            "greeting": self._greeting,
            "hours": self._hours,
            "shipping": self._shipping,
            "returns": self._returns,
            "price": self._price,
            "product": self._product,
            "order": self._start_order,
            "thanks": self._thanks,
            "human": self._human,
            "bye": self._bye,
        }.get(result.intent, self._fallback)
        return handler(session, result, hour, zh)

    def _greeting(self, session, result, hour, zh):
        night = hour >= 22 or hour < 7
        if zh:
            if night:
                return ("在的，我是 Moonlight 的夜间小助手🌙\n"
                        "人工客服 9:00–18:00 在线，深夜就由我来接待你。\n"
                        "想问营业时间、运费、价格，或者直接下单，都可以跟我说。")
            return ("你好呀，我是 Moonlight 的小助手。\n"
                    "想问营业时间、运费、价格，或者直接下单，都可以跟我说。")
        if night:
            return ("Hi, I'm Moonlight's night assistant🌙\n"
                    "Our human team is online 9:00–18:00; I'm covering the night shift.\n"
                    "Ask me about hours, shipping, prices — or just place an order.")
        return ("Hi, I'm Moonlight's assistant.\n"
                "Ask me about hours, shipping, prices — or just place an order.")

    def _hours(self, session, result, hour, zh):
        if zh:
            return (f"我们是线上小店，24 小时都可以下单。\n"
                    f"人工客服在线时间 {catalog.HUMAN_HOURS}，其他时间都由我来接待，不用等天亮。")
        return (f"We're an online shop — order anytime, 24/7.\n"
                f"Our human team is online {catalog.HUMAN_HOURS}; I cover the rest, no need to wait for morning.")

    def _shipping(self, session, result, hour, zh):
        if zh:
            return (f"运费很简单：满 ${catalog.FREE_SHIPPING_THRESHOLD:.0f} 包邮，不满收 "
                    f"${catalog.SHIPPING_FLAT_FEE:.2f}。\n"
                    f"工作日 24 小时内发货，3–5 天送达。")
        return (f"Simple: free shipping over ${catalog.FREE_SHIPPING_THRESHOLD:.0f}, "
                f"otherwise ${catalog.SHIPPING_FLAT_FEE}.\n"
                f"{catalog.DISPATCH_PROMISE.capitalize()}, delivered in {catalog.DELIVERY_WINDOW}.")

    def _returns(self, session, result, hour, zh):
        if zh:
            return f"支持 {catalog.RETURN_POLICY_DAYS} 天无理由退货（未拆封），运费我们承担。"
        return f"{catalog.RETURN_POLICY_DAYS}-day returns on unopened items — on us."

    def _price(self, session, result, hour, zh):
        product = result.product
        if product and zh:
            return (f"{product.name_zh}（{product.name}）${product.price_usd:.0f}，"
                    f"{product.weight_g}g，{product.blurb_zh}。")
        if product:
            return (f"{product.name} is ${product.price_usd:.0f}, {product.weight_g}g — "
                    f"{product.blurb}.")
        if zh:
            return "我们的蜡烛 $19 起：\n" + catalog.product_menu_zh() + "\n想了解哪一款？"
        return "Our candles start at $19:\n" + catalog.product_menu_en() + "\nWhich one catches your eye?"

    def _product(self, session, result, hour, zh):
        product = result.product
        if product and zh:
            return (f"{product.name_zh}（{product.name}）${product.price_usd:.0f}，"
                    f"{product.blurb_zh}。要来一只试试吗？")
        if product:
            return (f"{product.name} — ${product.price_usd:.0f}, {product.blurb}. "
                    f"Want to try one?")
        if zh:
            return "我们现在有这几款：\n" + catalog.product_menu_zh() + "\n有看中的吗？"
        return "Here's the lineup:\n" + catalog.product_menu_en() + "\nAnything you like?"

    def _start_order(self, session, result, hour, zh):
        product = result.product
        qty = parse_quantity(result._raw)
        session.state = ORDER_PRODUCT if product is None else ORDER_QTY
        if product:
            session.cart["product_id"] = product.id
            if qty and 1 <= qty <= 99:
                session.cart["qty"] = qty
                session.state = ORDER_NAME
                return self._ask_name(session, zh, product, qty)
            return self._ask_qty(session, zh, product)
        if zh:
            return "好呀，请问要哪一款？\n" + catalog.product_menu_zh()
        return "Sure — which one?\n" + catalog.product_menu_en()

    def _thanks(self, session, result, hour, zh):
        return "不客气，祝你有个好梦🌙" if zh else "You're welcome — sweet dreams🌙"

    def _human(self, session, result, hour, zh):
        if zh:
            return (f"人工客服 {catalog.HUMAN_HOURS} 在线。我已经把这通对话记下来了，"
                    f"他们一上班就会跟进。你也可以先跟我说，我能处理下单和查询。")
        return (f"Our human team is online {catalog.HUMAN_HOURS}. I've saved this chat "
                f"so they'll follow up first thing. Meanwhile I can handle orders and questions.")

    def _bye(self, session, result, hour, zh):
        return "晚安，好梦🌙 明早见！" if zh else "Good night🌙 See you in the morning!"

    def _fallback(self, session, result, hour, zh):
        if zh:
            return ("我没太明白，不过这些我都在行：\n"
                    "· 查营业时间、运费、退货\n"
                    "· 查价格、介绍蜡烛\n"
                    "· 直接下单（比如：我要买两只薰衣草）")
        return ("Not sure I got that — but I can help with:\n"
                "· hours, shipping, returns\n"
                "· prices and recommendations\n"
                "· placing an order (e.g. \"I'd like 2 lavenders\")")

    # -- order flow -------------------------------------------------------

    def _continue_order(self, session: Session, text: str) -> str:
        zh = session.language == "zh"
        state = session.state
        if state == ORDER_PRODUCT:
            return self._order_product(session, text, zh)
        if state == ORDER_QTY:
            return self._order_qty(session, text, zh)
        if state == ORDER_NAME:
            return self._order_name(session, text, zh)
        if state == ORDER_ADDRESS:
            return self._order_address(session, text, zh)
        if state == ORDER_PHONE:
            return self._order_phone(session, text, zh)
        if state == ORDER_CONFIRM:
            return self._order_confirm(session, text, zh)
        session.state = IDLE  # unknown state: fail safe, never get stuck
        return self._fallback(session, IntentResult("fallback", 0.0), 0, zh)

    def _product_by_id(self, pid):
        return next((p for p in catalog.PRODUCTS if p.id == pid), None)

    def _order_product(self, session, text, zh):
        product = catalog.find_product(text)
        if not product:
            if zh:
                return "没找到这款，麻烦从下面选一下：\n" + catalog.product_menu_zh()
            return "Couldn't find that one — pick from the list:\n" + catalog.product_menu_en()
        session.cart["product_id"] = product.id
        session.state = ORDER_QTY
        return self._ask_qty(session, zh, product)

    def _ask_qty(self, session, zh, product):
        name = product.name_zh if zh else product.name
        if zh:
            return f"好的，{name}。请问要几只？"
        return f"{name} — how many?"

    def _ask_name(self, session, zh, product, qty):
        name = product.name_zh if zh else product.name
        if zh:
            return f"记下了：{qty} × {name}。请问怎么称呼您？"
        return f"Got it: {qty} × {name}. Your name, please?"

    def _order_qty(self, session, text, zh):
        qty = parse_quantity(text)
        product = self._product_by_id(session.cart["product_id"])
        if not qty or not 1 <= qty <= 99:
            if zh:
                return "数量没听清，麻烦说个数（比如：2 只）。"
            return "Didn't catch the quantity — a number please (e.g. 2)."
        session.cart["qty"] = qty
        session.state = ORDER_NAME
        return self._ask_name(session, zh, product, qty)

    def _order_name(self, session, text, zh):
        name = text.strip()
        if len(name) < 1:
            return "请问怎么称呼您？" if zh else "Your name, please?"
        session.cart["name"] = name
        session.state = ORDER_ADDRESS
        if zh:
            return f"好的 {name}，收货地址是？"
        return f"Thanks {name} — shipping address?"

    def _order_address(self, session, text, zh):
        if len(text.strip()) < 6:
            if zh:
                return "地址好像太短了，麻烦写完整一点（省市区 + 门牌号）。"
            return "That address looks short — please include street and number."
        session.cart["address"] = text.strip()
        session.state = ORDER_PHONE
        if zh:
            return "收到。最后留个手机号，快递到了好联系你。"
        return "Got it. And a phone number so the courier can reach you?"

    def _order_phone(self, session, text, zh):
        digits = re.sub(r"\D", "", text)
        if not 7 <= len(digits) <= 15:
            if zh:
                return "手机号好像不对，麻烦重新输一下。"
            return "That phone number doesn't look right — try again?"
        session.cart["phone"] = digits
        session.state = ORDER_CONFIRM
        return self._order_summary(session, zh)

    def _order_summary(self, session, zh):
        product = self._product_by_id(session.cart["product_id"])
        qty = session.cart["qty"]
        subtotal = product.price_usd * qty
        fee = catalog.shipping_fee(subtotal)
        total = subtotal + fee
        ship = "包邮" if fee == 0 else f"运费 ${fee:.2f}"
        pname = product.name_zh if zh else product.name
        if zh:
            return (f"帮你核对一下：\n"
                    f"· {pname} × {qty} = ${subtotal:.0f}（{ship}）\n"
                    f"· 收货人：{session.cart['name']}\n"
                    f"· 地址：{session.cart['address']}\n"
                    f"· 电话：{session.cart['phone']}\n"
                    f"合计 ${total:.2f}，确认下单吗？（回复 好的 / 取消）")
        return (f"Quick check:\n"
                f"· {pname} × {qty} = ${subtotal:.0f} (shipping ${fee:.2f})\n"
                f"· Name: {session.cart['name']}\n"
                f"· Address: {session.cart['address']}\n"
                f"· Phone: {session.cart['phone']}\n"
                f"Total ${total:.2f} — confirm? (yes / cancel)")

    def _order_confirm(self, session, text, zh):
        if _affirms(text):
            return self._place_order(session, zh)
        if _denies(text):
            session.state = IDLE
            session.cart.clear()
            if zh:
                return "好的，订单已取消。还想看看别的吗？"
            return "Cancelled — no problem. Want to look at something else?"
        if zh:
            return "麻烦回复 好的 确认，或 取消 放弃这单。"
        return "Please reply yes to confirm, or cancel to drop it."

    def _place_order(self, session, zh):
        product = self._product_by_id(session.cart["product_id"])
        qty = session.cart["qty"]
        subtotal = round(product.price_usd * qty, 2)
        fee = catalog.shipping_fee(subtotal)
        order = {
            "customer_id": session.customer_id,
            "customer_name": session.cart["name"],
            "phone": session.cart["phone"],
            "address": session.cart["address"],
            "items": [{
                "product_id": product.id,
                "name": product.name,
                "qty": qty,
                "unit_price": product.price_usd,
            }],
            "subtotal_usd": subtotal,
            "shipping_usd": fee,
            "total_usd": round(subtotal + fee, 2),
        }
        order_id = self.order_log.record(order)
        session.state = IDLE
        session.cart.clear()
        if zh:
            return (f"下单成功🎉 订单号 {order_id}，合计 ${order['total_usd']:.2f}。\n"
                    f"工作日 24 小时内发出，3–5 天送达，"
                    f"明早 9 点人工客服会再跟你确认。\n"
                    f"谢谢惠顾，晚安🌙")
        return (f"Order placed🎉 {order_id}, total ${order['total_usd']:.2f}.\n"
                f"{catalog.DISPATCH_PROMISE.capitalize()}, delivered in {catalog.DELIVERY_WINDOW}. "
                f"Our team will confirm at 9am.\nThanks — good night🌙")
