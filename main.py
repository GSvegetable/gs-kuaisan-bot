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

# ================= 权限校验 =================
async def check_chat_permission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    if chat.type == "private":
        logging.info(f"✅ 私聊权限通过，用户ID: {update.effective_user.id}")
        return True
    if chat.type in ["group", "supergroup"]:
        try:
            member = await context.bot.get_chat_member(chat_id=chat.id, user_id=7857605443)
            if member.status in ['creator', 'administrator']:
                logging.info(f"✅ 群组 {chat.id} 中已找到管理员身份")
                return True
            await update.message.reply_text("❌ 群组无权限：确保开发者号在此群组中是管理员。")
        except Exception as e:
            logging.error(f"❌ 权限验证出错: {e}")
            await update.message.reply_text("❌ 权限验证出错，可能开发者不在该群。")
        return False
    return False

# ================= 核心播报 =================
async def scheduled_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.bot_data.get('is_broadcast_enabled', True):
            return
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
        # ===== 新增：计算三个数字之和 =====
        total_sum = sum(int(x) for x in open_code.split(',')) if open_code else 0

        big_small = latest.get("bigSmall", "")
        odd_even = latest.get("oddEven", "")
        left3 = latest.get("left3", "")

        # ===== 更新播报文本，加入和值 =====
        msg = (
            f"📟 期号：{current_expect}\n"
            f"🎲 开奖号码：{open_code}\n"
            f"🧮 和值：{total_sum}\n"
            f"📊 大小单双：{big_small}{odd_even}\n"
            f"📌 形态：{left3 if left3 else '无'}"
        )
        if TARGET_CHAT_ID:
            await context.bot.send_message(chat_id=TARGET_CHAT_ID, text=msg)
        context.bot_data['last_expect'] = current_expect
    except Exception as e:
        logging.error(f"快三播报任务异常: {e}")

# ================= 指令 =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 快三机器人已连接，可用指令如下：\n"
        "/ks_start - 开启开奖播报\n"
        "/ks_guanbi - 关闭开奖播报\n"
        "/ks_ce - 手动测试当前最新一期"
    )

async def ks_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_chat_permission(update, context): return
    context.bot_data['is_broadcast_enabled'] = True
    has_job = any(job.name == "kuaisan_job" for job in context.job_queue.jobs())
    if not has_job:
        context.job_queue.run_repeating(scheduled_job, interval=180, first=10, name="kuaisan_job")
    await update.message.reply_text("🤖 快三开奖播报已开启！")

async def ks_guanbi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_chat_permission(update, context): return
    context.bot_data['is_broadcast_enabled'] = False
    for job in context.job_queue.jobs():
        if job.name == "kuaisan_job":
            job.schedule_removal()
    await update.message.reply_text("✅ 快三开奖播报已关闭。")

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
                # ===== 新增：手动测试时也计算和值 =====
                total_sum = sum(int(x) for x in open_code.split(',')) if open_code else 0
                big_small = latest.get("bigSmall", "")
                odd_even = latest.get("oddEven", "")
                left3 = latest.get("left3", "")
                msg = (
                    f"📟 期号：{expect}\n"
                    f"🎲 开奖号码：{open_code}\n"
                    f"🧮 和值：{total_sum}\n"
                    f"📊 大小单双：{big_small}{odd_even}\n"
                    f"📌 形态：{left3 if left3 else '无'}"
                )
                await update.message.reply_text(f"✅ 抓取成功！当前最新一期数据：\n\n{msg}")
                return
        await update.message.reply_text("❌ 抓取失败，请稍后重试。")
    except Exception as e:
        await update.message.reply_text(f"❌ 请求发生网络错误：\n{str(e)}")

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    application = Application.builder().token(BOT_TOKEN).build()
    application.bot_data['is_broadcast_enabled'] = True

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ks_start", ks_start))
    application.add_handler(CommandHandler("ks_guanbi", ks_guanbi))
    application.add_handler(CommandHandler("ks_ce", ks_ce))

    logging.info("✅ 快三开奖机器人（加入和值版）已上线！")
    application.run_polling()

if __name__ == "__main__":
    main()
