"""Tests for the persistent order log."""

import re

from src.memory import OrderLog, SessionStore, make_order_id


def test_order_id_format():
    assert re.match(r"MC-\d{8}-[A-F0-9]{4}$", make_order_id())


def test_order_ids_are_unique():
    assert len({make_order_id() for _ in range(50)}) == 50


def test_record_and_read(tmp_path):
    log = OrderLog(str(tmp_path / "orders.log"))
    order_id = log.record({
        "customer_id": "c1",
        "customer_name": "林晓",
        "items": [{"product_id": "lavender-dusk", "qty": 2, "unit_price": 24.0}],
        "total_usd": 48.0,
    })
    orders = log.read_all()
    assert len(orders) == 1
    assert orders[0]["order_id"] == order_id
    assert orders[0]["customer_name"] == "林晓"
    assert "created_at" in orders[0]


def test_read_empty_log(tmp_path):
    log = OrderLog(str(tmp_path / "orders.log"))
    assert log.read_all() == []


def test_session_store_returns_same_session():
    store = SessionStore()
    s1 = store.get("alice")
    s2 = store.get("alice")
    assert s1 is s2
    assert store.get("bob") is not s1
