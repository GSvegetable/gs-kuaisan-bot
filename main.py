import os
import threading
import logging
import requests
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import BOT_TOKEN, TARGET_CHAT_ID

API_URL = "https://macaumarksix.com/api/macaujc11.com"
API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36"
}
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

app = Flask(__name__)
@app.route('/')
def home():
    return "快三开奖机器人运行中！"
def run_flask():
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

async def check_chat_permission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    if chat.type == "private":
        return True
    if chat.type in ["group", "supergroup"]:
        try:
            member = await context.bot.get_chat_member(chat_id=chat.id, user_id=7857605443)
            if member.status in ['creator', 'administrator']:
                return True
            await update.message.reply_text("❌ 群组无权限：确保开发者号在此群组中是管理员。")
        except Exception:
            await update.message.reply_text("❌ 权限验证出错。")
        return False
    return False

async def scheduled_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        resp = requests.get(API_URL, headers=API_HEADERS, timeout=10)
        if resp.status_code != 200: return
        data = resp.json()
        if not data or len(data) == 0: return
        latest = data[0]
        current_expect = latest.get("expect")
        if not current_expect: return
        last_expect = context.bot_data.get('last_expect', "")
        if last_expect == current_expect: return
        if last_expect == "":
            context.bot_data['last_expect'] = current_expect
            return

        open_code = latest.get("openCode", "")
        big_small = latest.get("bigSmall", "")
        odd_even = latest.get("oddEven", "")
        left3 = latest.get("left3", "")

        msg = f"📟 期号：{current_expect}\n🎲 开奖号码：{open_code}\n📊 大小单双：{big_small}{odd_even}\n📌 形态：{left3 if left3 else '无'}"
        if TARGET_CHAT_ID:
            await context.bot.send_message(chat_id=TARGET_CHAT_ID, text=msg)
        context.bot_data['last_expect'] = current_expect
    except Exception as e:
        logging.error(f"快三播报任务异常: {e}")

async def ks_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_chat_permission(update, context): return
    # 检查任务是否存在，不存在则创建
    has_job = any(job.name == "kuaisan_job" for job in context.job_queue.jobs())
    if not has_job:
        context.job_queue.run_repeating(scheduled_job, interval=180, first=10, name="kuaisan_job")
    await update.message.reply_text("🤖 快三开奖播报已开启！")

async def ks_guanbi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_chat_permission(update, context): return
    # 彻底删除后台定时任务
    for job in context.job_queue.jobs():
        if job.name == "kuaisan_job":
            job.schedule_removal()
    await update.message.reply_text("✅ 快三开奖播报已关闭（定时任务已销毁）。")

async def ks_ce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_chat_permission(update, context): return
    await update.message.reply_text("⏳ 正在获取最新一期数据...")
    try:
        resp = requests.get(API_URL, headers=API_HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                latest = data[0]
                expect = latest.get("expect", "未知")
                open_code = latest.get("openCode", "")
                big_small = latest.get("bigSmall", "")
                odd_even = latest.get("oddEven", "")
                left3 = latest.get("left3", "")
                msg = f"📟 期号：{expect}\n🎲 开奖号码：{open_code}\n📊 大小单双：{big_small}{odd_even}\n📌 形态：{left3 if left3 else '无'}"
                await update.message.reply_text(f"✅ 抓取成功！当前最新一期数据：\n\n{msg}")
                return
        await update.message.reply_text("❌ 抓取失败，请稍后重试。")
    except Exception as e:
        await update.message.reply_text(f"❌ 请求发生网络错误：\n{str(e)}")

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    application = Application.builder().token(BOT_TOKEN).build()
    # 注意：不再默认开启定时任务，完全靠用户指令触发
    application.add_handler(CommandHandler("ks_start", ks_start))
    application.add_handler(CommandHandler("ks_guanbi", ks_guanbi))
    application.add_handler(CommandHandler("ks_ce", ks_ce))
    logging.info("✅ 快三开奖机器人（独立指令版）已上线！")
    application.run_polling()

if __name__ == "__main__":
    main()
