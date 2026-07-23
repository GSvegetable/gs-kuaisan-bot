import os

# 🟢 机器人的 Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "8631297840:AAFjH4CAHFgjSPQW4gVSBplI8MVDnl7dAvg")

# 🟢 要播报的群组/私聊 ID（不填则定时播报无效，但私聊指令能用）
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
