#!/usr/bin/env python3
"""Midnight demo: a full 2am customer conversation, end to end.

Run it::

    python3 demo_conversation.py

No API keys, no network — every reply is generated locally by the bot.
Record your terminal while it runs and you have your product demo video.
"""

import sys
import textwrap
from datetime import datetime, timedelta

sys.path.insert(0, ".")  # run from the repo root

from src.bot import MidnightBot
from src.memory import OrderLog

# (minutes after 02:13, customer message) — a realistic late-night shopper
SCRIPT = [
    (0, "在吗"),
    (1, "你们家晚上几点关门啊？"),
    (3, "运费怎么算，江浙沪几天到？"),
    (5, "薰衣草那款多少钱？"),
    (7, "那我要两只吧"),
    (8, "林晓"),
    (9, "上海市静安区南京西路88号301室"),
    (10, "13800138000"),
    (11, "好的，确认"),
    (12, "谢谢，晚安"),
]

BANNER = """\
=============================================================
  🌙  Moonlight Candle Co. — midnight customer-service demo
  Every reply below is generated locally. Zero API keys.
  (Record this terminal — it's the product demo.)
============================================================="""


def stamp(base: datetime, minutes: int) -> str:
    return (base + timedelta(minutes=minutes)).strftime("%H:%M")


def main() -> None:
    log = OrderLog("orders.log")  # the shop's real record, same file every run
    bot = MidnightBot(order_log=log)
    base = datetime.now().replace(hour=2, minute=13, second=0, microsecond=0)

    print(BANNER)
    for minutes, message in SCRIPT:
        when = stamp(base, minutes)
        print(f"\n[{when}]  customer: {message}")
        reply = bot.handle_message("demo-customer-001", message,
                                   timestamp=base + timedelta(minutes=minutes))
        for line in reply.splitlines():
            wrapped = textwrap.fill(line, width=62) if line else ""
            print(f"[{when}]       bot: {wrapped}" if wrapped else f"[{when}]       bot:")

    orders = log.read_all()
    last = orders[-1]
    print("\n-------------------------------------------------------------")
    print("📦  Order written to orders.log (the shop wakes up to this):")
    print(f"   {last['order_id']} | {last['customer_name']} | "
          f"{last['items'][0]['qty']}× {last['items'][0]['name']} | "
          f"total ${last['total_usd']:.2f}")
    print("-------------------------------------------------------------")
    print("Done. Nobody was awake — the shop still made the sale. 🌙")


if __name__ == "__main__":
    main()
