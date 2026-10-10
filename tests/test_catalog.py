"""Tests for the shop catalog: product lookup and shipping math."""

from src import catalog


def test_find_product_chinese():
    assert catalog.find_product("薰衣草那款多少钱？").id == "lavender-dusk"


def test_find_product_english():
    assert catalog.find_product("tell me about the cedar one").id == "cedar-smoke"


def test_find_product_gift_set():
    assert catalog.find_product("礼盒怎么卖").id == "night-trio"


def test_find_product_unknown_returns_none():
    assert catalog.find_product("你们卖咖啡吗") is None


def test_all_products_have_sane_prices():
    for p in catalog.PRODUCTS:
        assert p.price_usd > 0
        assert p.name and p.name_zh


def test_shipping_fee_threshold():
    assert catalog.shipping_fee(34.99) == catalog.SHIPPING_FLAT_FEE
    assert catalog.shipping_fee(35.00) == 0.0
    assert catalog.shipping_fee(120.0) == 0.0
