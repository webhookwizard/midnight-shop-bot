"""Shop catalog: products, pricing, and FAQ facts for Moonlight Candle Co.

All numbers live here so the bot answers from one source of truth —
change a price once, and every reply (and order total) follows.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    id: str
    name: str          # English display name
    name_zh: str       # Chinese display name
    blurb: str         # one-line sales description (English)
    blurb_zh: str      # one-line sales description (Chinese)
    price_usd: float
    weight_g: int
    keywords: tuple    # bilingual match words, e.g. ("lavender", "薰衣草")


PRODUCTS: tuple = (
    Product(
        id="lavender-dusk",
        name="Lavender Dusk",
        name_zh="薰衣草暮色",
        blurb="French lavender + vanilla, 45h burn",
        blurb_zh="法国薰衣草配香草，燃烧约45小时",
        price_usd=24.0,
        weight_g=220,
        keywords=("lavender", "薰衣草", "dusk", "暮色"),
    ),
    Product(
        id="cedar-smoke",
        name="Cedar & Smoke",
        name_zh="雪松烟火",
        blurb="Cedarwood + smoked amber, 45h burn",
        blurb_zh="雪松木配烟熏琥珀，燃烧约45小时",
        price_usd=28.0,
        weight_g=220,
        keywords=("cedar", "雪松", "smoke", "烟"),
    ),
    Product(
        id="sea-salt-morning",
        name="Sea Salt Morning",
        name_zh="海盐清晨",
        blurb="Sea salt + white tea, 30h burn",
        blurb_zh="海盐配白茶，燃烧约30小时",
        price_usd=19.0,
        weight_g=160,
        keywords=("sea salt", "seasalt", "海盐", "salt"),
    ),
    Product(
        id="night-trio",
        name='Gift Set "Night Trio"',
        name_zh="礼盒「夜之三重奏」",
        blurb="3 × 100g minis, gift-boxed",
        blurb_zh="3 颗 100g 迷你蜡烛，礼盒装",
        price_usd=49.0,
        weight_g=300,
        keywords=("trio", "gift", "set", "礼盒", "套装", "三重奏"),
    ),
)

# --- Shop facts (single source of truth for FAQ answers) ---

SHOP_NAME = "Moonlight Candle Co."
HUMAN_HOURS = "09:00–18:00"          # human staff online; the bot covers the rest
FREE_SHIPPING_THRESHOLD = 35.0       # USD
SHIPPING_FLAT_FEE = 4.90             # USD, waived above the threshold
DISPATCH_PROMISE = "ships within 24h on weekdays"
DELIVERY_WINDOW = "3–5 days"
RETURN_POLICY_DAYS = 7


def find_product(text: str) -> "Product | None":
    """Return the first product whose keywords appear in *text* (case-insensitive)."""
    lowered = text.lower()
    for product in PRODUCTS:
        if any(kw.lower() in lowered for kw in product.keywords):
            return product
    return None


def shipping_fee(subtotal_usd: float) -> float:
    """Flat fee below the free-shipping threshold, free above it."""
    return 0.0 if subtotal_usd >= FREE_SHIPPING_THRESHOLD else SHIPPING_FLAT_FEE


def product_menu_zh() -> str:
    lines = [f"· {p.name_zh}（{p.name}）${p.price_usd:.0f}" for p in PRODUCTS]
    return "\n".join(lines)


def product_menu_en() -> str:
    lines = [f"· {p.name} — ${p.price_usd:.0f}" for p in PRODUCTS]
    return "\n".join(lines)
