# 🌙 midnight-shop-bot

> Your shop answers while you sleep. A demo night-shift customer-service bot — zero API keys, runs anywhere.

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![No API keys](https://img.shields.io/badge/API%20keys-zero-green.svg)](#-try-it-in-2-minutes)

## 🖥 Demo

Real terminal session (`python3 demo_conversation.py`) — a customer messages at 2am, nobody is awake:

```
[02:13]  customer: 在吗
[02:13]       bot: 在的，我是 Moonlight 的夜间小助手🌙
         人工客服 9:00–18:00 在线，深夜就由我来接待你。

[02:16]  customer: 运费怎么算，江浙沪几天到？
[02:16]       bot: 运费很简单：满 $35 包邮，不满收 $4.90。
         工作日 24 小时内发货，3–5 天送达。

[02:18]  customer: 薰衣草那款多少钱？
[02:18]       bot: 薰衣草暮色（Lavender Dusk）$24，220g，法国薰衣草配香草，燃烧约45小时。

[02:20]  customer: 那我要两只吧
[02:20]       bot: 记下了：2 × 薰衣草暮色。请问怎么称呼您？

[02:24]  customer: 好的，确认
[02:24]       bot: 下单成功🎉 订单号 MC-20261010-B16F，合计 $48.00。
         工作日 24 小时内发出，明早 9 点人工客服会再跟你确认。
```

The shop woke up to a finished order in `orders.log`. Nobody lifted a finger.

## 😴 The problem

Mei runs a small candle shop. Every night, messages like "在吗" arrive at 1–2am — and sit unanswered until morning.
By then, half those shoppers already bought from someone else. She's losing orders in her sleep.

## ✨ What it does

- 🌙 **Greets the 2am "在吗"** instead of letting it sit until morning — the conversation starts in seconds
- ❓ **Answers the repeat questions** (hours, shipping, prices, returns) so you stop typing the same replies daily
- 🛒 **Takes the whole order itself** — product, quantity, name, address, phone, confirmation — then logs it
- 📦 **Hands you a finished order** in `orders.log` when you wake up; your 9am self just ships it
- 🧠 **Understands context** ("那我要两只吧" after asking about lavender) and speaks Chinese + English
- 🔌 **Grows with you**: runs offline today; a real AI plugs into one documented seam tomorrow (no rewrite)

## 🚀 Try it in 2 minutes

```bash
git clone https://github.com/webhookwizard/midnight-shop-bot.git
cd midnight-shop-bot
python3 demo_conversation.py
```

That's it — no keys, no signup, no network. Watch the full midnight sale play out in your terminal.

Run the tests:

```bash
pip install -r requirements.txt   # pytest only; the bot itself needs nothing
pytest                            # 44 tests, all green
```

## 💰 What you save

One lost midnight order a week at ~$48 = **~$2,500/year** walking to competitors while you sleep.

## 🛠 How it works

<details>
<summary>Technical details (for the curious)</summary>

- **Stack:** Python 3.9+ standard library only. No dependencies, no API keys, no network calls.
- **Architecture:** `src/bot.py` (`MidnightBot`) wires three parts —
  `src/brain.py` (bilingual keyword intent engine + checkout state machine),
  `src/memory.py` (per-customer sessions, JSON-lines order log),
  `src/llm_adapter.py` (the `ReplyProvider` seam).
- **Intent engine:** keyword scoring across 12 intents (Chinese + English), with
  context-aware routing — a bare quantity ("两只") right after a product question
  is treated as an order for that product.
- **Checkout flow:** `IDLE → PRODUCT → QTY → NAME → ADDRESS → PHONE → CONFIRM`,
  with gentle re-asks on invalid input (bad quantity, short address, bad phone)
  and a human-readable order id (`MC-YYYYMMDD-XXXX`).
- **Production path:** implement `ReplyProvider.generate()` with your LLM and pass
  it to `MidnightBot(provider=...)`. Sessions, checkout, and order logging stay untouched.
- **Tests:** 44 pytest cases covering intents (both languages), quantity parsing
  (Arabic + Chinese numerals), the full checkout in Chinese and English,
  cancellation, invalid-input recovery, and order-log persistence.

</details>

---

> Want this customized for your shop? DM [@saulgoodmanc99](https://t.me/saulgoodmanc99) — custom builds from $99, settled in USDT.

中文说明 → [README_CN.md](README_CN.md)
