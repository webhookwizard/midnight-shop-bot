"""Tests for intent detection, dialogue flow, and the checkout state machine."""

import re

import pytest

from src.brain import (
    DialogueManager,
    detect_intent,
    detect_language,
    parse_quantity,
)
from src.memory import OrderLog, Session


@pytest.fixture
def manager(tmp_path):
    return DialogueManager(order_log=OrderLog(str(tmp_path / "orders.log")))


@pytest.fixture
def session():
    return Session(customer_id="test-1")


# --- intent detection ------------------------------------------------------

@pytest.mark.parametrize("text,intent", [
    ("在吗", "greeting"),
    ("hello, anyone there?", "greeting"),
    ("你们几点关门？", "hours"),
    ("what are your hours?", "hours"),
    ("运费怎么算？", "shipping"),
    ("how long is delivery?", "shipping"),
    ("可以退货吗？", "returns"),
    ("薰衣草多少钱？", "price"),
    ("how much is the gift set?", "price"),
    ("有什么味道推荐吗", "product"),
    ("我想买两只", "order"),
    ("I want to order one", "order"),
    ("谢谢！", "thanks"),
    ("转人工", "human"),
    ("晚安", "bye"),
])
def test_intents(text, intent):
    assert detect_intent(text).intent == intent


def test_fallback_on_gibberish():
    result = detect_intent("asdfghjkl qwerty")
    assert result.intent == "fallback"
    assert result.confidence == 0.0


def test_product_entity_extracted():
    result = detect_intent("薰衣草那款多少钱？")
    assert result.intent == "price"
    assert result.product is not None
    assert result.product.id == "lavender-dusk"


# --- language & quantity helpers -------------------------------------------

def test_detect_language():
    assert detect_language("在吗") == "zh"
    assert detect_language("hello") == "en"
    assert detect_language("hello 你好") == "zh"


@pytest.mark.parametrize("text,qty", [
    ("两只", 2),
    ("那我要两只吧", 2),
    ("3个", 3),
    ("来10件", 10),
    ("十个", 10),
    ("随便看看", None),
])
def test_parse_quantity(text, qty):
    assert parse_quantity(text) == qty


# --- greetings ---------------------------------------------------------------

def test_night_greeting_mentions_night_shift(manager, session):
    reply = manager.respond(session, "在吗", hour=2)
    assert "夜间" in reply or "night" in reply.lower()


def test_day_greeting_has_no_night_shift(manager, session):
    reply = manager.respond(session, "hello", hour=10)
    assert "夜间" not in reply


# --- full checkout flow ------------------------------------------------------

def test_full_order_flow_zh(manager, session, tmp_path):
    assert "夜间" in manager.respond(session, "在吗", hour=2)
    manager.respond(session, "薰衣草那款多少钱？", hour=2)          # sets product context
    r = manager.respond(session, "那我要两只吧", hour=2)            # smart routing: qty + context
    assert "2" in r and session.state == "ORDER_NAME"              # skipped straight past product+qty
    r = manager.respond(session, "林晓", hour=2)
    assert session.state == "ORDER_ADDRESS"
    r = manager.respond(session, "上海市静安区南京西路88号301室", hour=2)
    assert session.state == "ORDER_PHONE"
    r = manager.respond(session, "13800138000", hour=2)
    assert session.state == "ORDER_CONFIRM"
    assert "$48" in r and "包邮" in r                              # 2×$24, free shipping ≥ $35
    r = manager.respond(session, "好的，确认", hour=2)
    assert re.search(r"MC-\d{8}-[A-F0-9]{4}", r)
    assert session.state == "IDLE"

    orders = OrderLog(str(tmp_path / "orders.log")).read_all()
    assert len(orders) == 1
    order = orders[0]
    assert order["customer_name"] == "林晓"
    assert order["items"][0]["product_id"] == "lavender-dusk"
    assert order["total_usd"] == 48.0


def test_order_asks_which_product_when_unknown(manager, session):
    r = manager.respond(session, "我想买", hour=2)
    assert session.state == "ORDER_PRODUCT"
    assert "薰衣草" in r or "Lavender" in r


def test_order_reasks_on_bad_quantity(manager, session):
    manager.respond(session, "我要买雪松那款", hour=2)
    assert session.state == "ORDER_QTY"
    r = manager.respond(session, "随便", hour=2)
    assert session.state == "ORDER_QTY"  # still waiting
    assert "数量" in r or "quantity" in r.lower()


def test_order_reasks_on_bad_phone(manager, session):
    for msg in ["买1只海盐", "陈晨", "北京市朝阳区建国路1号"]:
        manager.respond(session, msg, hour=14)
    r = manager.respond(session, "abc", hour=14)
    assert session.state == "ORDER_PHONE"
    assert "手机" in r or "phone" in r.lower()


def test_order_cancel_at_confirm(manager, session):
    for msg in ["buy 1 sea salt", "Ann", "1 Main St, Springfield", "5551234567"]:
        manager.respond(session, msg, hour=14)
    assert session.state == "ORDER_CONFIRM"
    r = manager.respond(session, "cancel", hour=14)
    assert session.state == "IDLE"
    assert "cancel" in r.lower()


def test_english_checkout(manager, session, tmp_path):
    manager.respond(session, "hi", hour=23)
    manager.respond(session, "how much is cedar?", hour=23)
    r = manager.respond(session, "I'll take 2", hour=23)
    assert session.state == "ORDER_NAME"
    manager.respond(session, "Bob", hour=23)
    manager.respond(session, "99 Ocean Ave, Miami", hour=23)
    manager.respond(session, "13055550199", hour=23)
    r = manager.respond(session, "yes", hour=23)
    assert re.search(r"MC-\d{8}-[A-F0-9]{4}", r)
    orders = OrderLog(str(tmp_path / "orders.log")).read_all()
    assert orders[0]["total_usd"] == 56.0  # 2 × $28, free shipping


def test_fallback_lists_capabilities(manager, session):
    r = manager.respond(session, "blablabla", hour=2)
    assert "营业时间" in r or "hours" in r.lower()
