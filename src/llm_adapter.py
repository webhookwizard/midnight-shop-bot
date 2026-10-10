"""The production seam: where a real LLM plugs in.

The demo runs 100% offline on the rule-based brain (zero API keys, zero
cost). When a shop outgrows scripted replies, you do NOT rewrite the bot —
you implement ``ReplyProvider`` with your model of choice and hand it to
``MidnightBot``. Sessions, the checkout state machine, and the order log
keep working exactly as before; only the wording engine changes.

Concrete swap (production)::

    from src.llm_adapter import ReplyProvider
    from src.bot import MidnightBot

    class ClaudeProvider(ReplyProvider):
        def generate(self, session, user_text, hour):
            # call your LLM here; fall back to the local brain on error
            ...

    bot = MidnightBot(provider=ClaudeProvider())
"""

from abc import ABC, abstractmethod

from .brain import DialogueManager
from .memory import OrderLog, Session


class ReplyProvider(ABC):
    """Produces one reply for one incoming message."""

    @abstractmethod
    def generate(self, session: Session, user_text: str, hour: int) -> str:
        """Return the bot's reply text.

        :param session: the customer's conversation state (history, cart, …)
        :param user_text: the raw incoming message
        :param hour: local hour 0–23, for time-aware greetings
        """


class LocalBrainProvider(ReplyProvider):
    """Offline provider used by the demo: deterministic, free, no keys.

    This is what makes the 2-minute quickstart possible. Swap it for an
    LLM-backed provider in production without touching anything else.
    """

    def __init__(self, order_log: OrderLog | None = None) -> None:
        self._dialogue = DialogueManager(order_log=order_log)

    def generate(self, session: Session, user_text: str, hour: int) -> str:
        return self._dialogue.respond(session, user_text, hour)
