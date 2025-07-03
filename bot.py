from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from datetime import datetime
from collections import defaultdict
import asyncio
import re
import os

user_data = {}
last_summary_time = {}
# Handle plain text messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    message_text = update.message.text or update.message.caption
    if not message_text:
        return

    lines = message_text.strip().split("\n")
    now = datetime.now()

    if chat_id not in user_data:
        user_data[chat_id] = []

    count = 0
    failed = []

    for line in lines:
        line = line.strip()
        if not line:
            continue  # skip empty lines

        match = re.match(r"(.+?)\s+([\d.,kKrbRB]+)$", line)
        if not match:
            failed.append(line)
            continue

        label = match.group(1).strip()
        raw_amount = match.group(2).lower()

        try:
            if 'k' in raw_amount or 'rb' in raw_amount:
                raw_amount = raw_amount.replace('rb', '').replace('k', '')
                amount = int(float(raw_amount.replace(',', '.')) * 1000)
            else:
                amount = int(re.sub(r"[^\d]", "", raw_amount))
        except:
            failed.append(line)
            continue

        if not label:
            failed.append(line)
            continue

        user_data[chat_id].append((now, label, amount))
        count += 1

# /excel - tampil dengan markdown dan koma
async def export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    entries = user_data.get(chat_id, [])

    if not entries:
        await update.message.reply_text("📭 Belum ada data yang disimpan.")
        return

    rows = []
    for t, label, amount in entries:
        date_str = t.strftime("%d/%m")
        label_clean = label.replace(",", "")  # hindari gangguan di CSV
        rows.append(f"{date_str},{label_clean},{amount}")

    output = "\n".join(rows)

    # Kirim sebagai code block Markdown (csv)
    await update.message.reply_text(
        f"```csv\n{output}\n```",
        parse_mode="Markdown"
    )

# /summary command
async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    now = datetime.now()
    last_time = last_summary_time.get(chat_id, datetime.min)

    entries = user_data.get(chat_id, [])
    filtered = [(label.strip(), amount) for t, label, amount in entries if t > last_time and label.strip()]

    if not filtered:
        await update.message.reply_text("Tidak ada pengeluaran baru sejak /sum terakhir.")
        return

    # hitung summary
    grouped = defaultdict(int)
    total = 0
    for label, amount in filtered:
        grouped[label] += amount
        total += amount   

    await update.message.reply_text(
        f"Total Pengeluaran: Rp{total:,}".replace(",", ".")
    )

    last_summary_time[chat_id] = now
    
     # Group and sum by label
    # grouped = defaultdict(int)
    # total = 0
    # for label, amount in filtered:
    #     grouped[label] += amount
    #     total += amount

    # detail_lines = [f"{label}: Rp{amount:,}".replace(",", ".") for label, amount in grouped.items()]
    # detail = "\n".join(detail_lines)

    # await update.message.reply_text(
    #     f"📋 Rangkuman sejak /summary terakhir:\n{detail}\n\n💰 Total: Rp{total:,}".replace(",", ".")
    # )


# /reset command
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_data[chat_id] = []
    last_summary_time[chat_id] = datetime.min
    await update.message.reply_text("Data has been reset.")

# Main async function
async def main():
    print("🤖 Bot is starting...")

    TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("sum", summary))
    app.add_handler(CommandHandler("exl", export_excel))
    app.add_handler(CommandHandler("reset", reset))
    text_filter = (filters.TEXT & ~filters.COMMAND) | (filters.PHOTO & filters.Caption())
    app.add_handler(MessageHandler(text_filter, handle_message))
    print("✅ Bot is running...")
    await app.run_polling()

# Run main
if __name__ == "__main__":
    import nest_asyncio
    import asyncio

    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
