"""MidnightBot: the shop's night-shift assistant.

One class wires everything together: sessions in, replies out.
Drop in any ``ReplyProvider`` (rule-based for the demo, an LLM for
production) — the interface never changes.
"""

from datetime import datetime

from .llm_adapter import LocalBrainProvider, ReplyProvider
from .memory import OrderLog, SessionStore


class MidnightBot:
    def __init__(self,
                 provider: ReplyProvider | None = None,
                 order_log: OrderLog | None = None,
                 shop_name: str = "Moonlight Candle Co.") -> None:
        self.shop_name = shop_name
        self.sessions = SessionStore()
        self.order_log = order_log or OrderLog()
        self.provider = provider or LocalBrainProvider(order_log=self.order_log)

    def handle_message(self, customer_id: str, text: str,
                       timestamp: datetime | None = None) -> str:
        """Process one incoming message, return the bot's reply.

        Safe to call from any chat adapter (Telegram/Discord/WhatsApp):
        no network, no exceptions leak — a confused bot apologizes,
        it never crashes the conversation.
        """
        timestamp = timestamp or datetime.now()
        session = self.sessions.get(customer_id)
        try:
            return self.provider.generate(session, text, timestamp.hour)
        except Exception:  # noqa: BLE001 — the shop must never go silent
            return ("抱歉，我刚才没反应过来，能再说一遍吗？\n"
                    "Sorry, I missed that — could you say it once more?")
