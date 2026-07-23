import os
import threading
import logging
import requests
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import BOT_TOKEN, TARGET_CHAT_ID

# ================= 基础配置 =================
API_URL = "https://macaumarksix.com/api/live11"
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

app = Flask(__name__)
@app.route('/')
def home():
    return "快三开奖机器人运行中！"
def run_flask():
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ================= 核心逻辑：检测开奖并播报 =================
async def scheduled_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        # 1. 检查开关状态
        if not context.bot_data.get('is_broadcast_enabled', True):
            return

        # 2. 抓取 API 数据
        resp = requests.get(API_URL, timeout=10)
        if resp.status_code != 200:
            return
        data = resp.json()
        if not data or len(data) == 0:
            return
        
        latest = data[0]
        current_expect = latest.get("expect")
        if not current_expect:
            return

        # 3. 判断是否有新的一期
        last_expect = context.bot_data.get('last_expect', "")
        if last_expect == current_expect:
            return
        if last_expect == "":
            context.bot_data['last_expect'] = current_expect
            return

        # 4. 提取字段（接口数据的 key 是你截图里的那些）
        open_code = latest.get("openCode", "")
        big_small = latest.get("bigSmall", "")
        odd_even = latest.get("oddEven", "")
        left3 = latest.get("left3", "")

        msg = (
            f"📟 期号：{current_expect}\n"
            f"🎲 开奖号码：{open_code}\n"
            f"📊 大小单双：{big_small}{odd_even}\n"
            f"📌 形态：{left3 if left3 else '无'}"
        )

        # 5. 发送消息（如果配置了群聊/私聊ID）
        if TARGET_CHAT_ID:
            await context.bot.send_message(chat_id=TARGET_CHAT_ID, text=msg)
        
        # 更新已播报的期号
        context.bot_data['last_expect'] = current_expect

    except Exception as e:
        logging.error(f"快三播报任务异常: {e}")

# ================= 机器人指令 =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.application.bot_data['is_broadcast_enabled'] = True
    await update.message.reply_text("🤖 快三开奖播报已开启！发送 `/ce` 立即测试当前期，发送 `/guanbi` 可关闭播报。")

async def guanbi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.application.bot_data['is_broadcast_enabled'] = False
    await update.message.reply_text("✅ 快三开奖播报已关闭。")

async def ce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ 正在尝试获取最新一期数据...")
    resp = requests.get(API_URL, timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        if data and len(data) > 0:
            latest = data[0]
            expect = latest.get("expect", "未知")
            open_code = latest.get("openCode", "")
            big_small = latest.get("bigSmall", "")
            odd_even = latest.get("oddEven", "")
            left3 = latest.get("left3", "")
            msg = (
                f"📟 期号：{expect}\n"
                f"🎲 开奖号码：{open_code}\n"
                f"📊 大小单双：{big_small}{odd_even}\n"
                f"📌 形态：{left3 if left3 else '无'}"
            )
            await update.message.reply_text(f"✅ 抓取成功！当前最新一期数据：\n\n{msg}")
            return
    await update.message.reply_text("❌ 抓取失败，请稍后重试。")

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    application = Application.builder().token(BOT_TOKEN).build()
    application.bot_data['is_broadcast_enabled'] = True

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("guanbi", guanbi))
    application.add_handler(CommandHandler("ce", ce))

    # 快三通常是 3 分钟（180秒）开一次
    application.job_queue.run_repeating(scheduled_job, interval=180, first=10)

    logging.info("✅ 快三开奖机器人已上线！")
    application.run_polling()

if __name__ == "__main__":
    main()
