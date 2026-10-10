# 🌙 midnight-shop-bot（中文说明）

> 你的小店半夜也有人值班。一个"午夜客服" demo：零 API key，下载即跑。

## 它是干什么的

这是给小网店做的 AI 客服演示——也是 $499「AI 自动客服」服务的活广告。
场景：凌晨 2 点，顾客发来一句"在吗"，店主在睡觉。机器人自己完成整套接待：
打招呼 → 回答营业时间/运费/价格 → 帮顾客下单（商品、数量、姓名、地址、电话、确认）→
把订单记进 `orders.log`。店主早上醒来，直接发货就行。

## 跑一下（2 分钟）

```bash
git clone https://github.com/webhookwizard/midnight-shop-bot.git
cd midnight-shop-bot
python3 demo_conversation.py
```

不需要任何 key 和网络。想看测试：`pip install -r requirements.txt && pytest`（44 个测试全过）。

## 亮点

- 中英双语：自动识别顾客用中文还是英文
- 懂上下文：问完"薰衣草多少钱"直接说"那我要两只吧"，它知道是哪款、要几只
- 下单全流程带校验：数量、地址、手机号写错了会温柔地让你重填
- 订单落盘：每笔订单追加到 `orders.log`（JSON），对账、导表格都方便
- 留了升级口：`src/llm_adapter.py` 里写好了 `ReplyProvider` 接口，
  以后接真正的 AI 大模型不用重写，一行切换

## 能省多少

每周漏 1 个半夜订单（约 $48），一年就是 **约 $2,500** 睡着了流给竞争对手。

---

> 想给你的店定制一个？DM [@saulgoodmanc99](https://t.me/saulgoodmanc99) — 定制开发 $99 起，USDT 结算。
