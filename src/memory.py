"""Conversation sessions and the persistent order log.

Sessions live in memory (one per customer). Orders are appended as JSON
lines to ``orders.log`` — the shop's real record, readable by anything.
"""

import json
import os
import time
import uuid
from dataclasses import dataclass, field


@dataclass
class Session:
    """One customer's ongoing conversation."""
    customer_id: str
    state: str = "IDLE"          # dialogue state machine position (see brain.py)
    language: str = "zh"         # "zh" or "en", detected from first message
    history: list = field(default_factory=list)   # [(who, text), ...]
    cart: dict = field(default_factory=dict)      # order-in-progress + context
    # cart keys: product_id, qty, name, address, phone, last_product_id


class SessionStore:
    """In-memory registry of sessions, keyed by customer id."""

    def __init__(self) -> None:
        self._sessions: dict = {}

    def get(self, customer_id: str) -> Session:
        if customer_id not in self._sessions:
            self._sessions[customer_id] = Session(customer_id=customer_id)
        return self._sessions[customer_id]


def make_order_id() -> str:
    """Human-readable order id, e.g. MC-20261010-7F3A."""
    date = time.strftime("%Y%m%d")
    rand = uuid.uuid4().hex[:4].upper()
    return f"MC-{date}-{rand}"


class OrderLog:
    """Append-only JSON-lines order log."""

    def __init__(self, path: str = "orders.log") -> None:
        self.path = path

    def record(self, order: dict) -> str:
        """Stamp an order id + timestamp, append it, return the order id."""
        order = dict(order)
        order["order_id"] = make_order_id()
        order["created_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(order, ensure_ascii=False) + "\n")
        return order["order_id"]

    def read_all(self) -> list:
        """Read every recorded order (returns [] if none yet)."""
        if not os.path.exists(self.path):
            return []
        orders = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    orders.append(json.loads(line))
        return orders
