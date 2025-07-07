from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from datetime import datetime
from collections import defaultdict
import asyncio
import re
import os

# Now maps: chat_id -> message_id -> (timestamp, label, amount)
user_data = defaultdict(dict)
last_summary_time = {}

# Handle plain text messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    message = update.effective_message
    message_text = message.text or message.caption
    message_id = message.message_id

    if not message_text:
        return

    lines = message_text.strip().split("\n")
    now = datetime.now()
    updated = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = re.match(r"(.+?)\s+([\d.,kKrbRB]+)$", line)
        if not match:
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
            continue

        user_data[chat_id][message_id] = (now, label, amount)
        updated = True

    if updated:
        print(f"✅ Saved message {message_id} from chat {chat_id}")

# Tambahkan di atas
last_export_time = {}

# /excel - tampil dengan markdown dan koma, hanya data terbaru
async def export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    now = datetime.now()
    last_time = last_export_time.get(chat_id, datetime.min)

    entries = user_data.get(chat_id, [])
    filtered = [(t, label, amount) for t, label, amount in entries if t > last_time]

    if not filtered:
        await update.message.reply_text("📭 Tidak ada data baru sejak /exl terakhir.")
        return

    rows = []
    for t, label, amount in filtered:
        date_str = t.strftime("%d/%m")
        label_clean = label.replace(",", "")
        rows.append(f"{date_str},{label_clean},{amount}")

    output = "\n".join(rows)

    await update.message.reply_text(
        f"```csv\n{output}\n```",
        parse_mode="Markdown"
    )

    # Update waktu terakhir ekspor
    last_export_time[chat_id] = now

# /summary command
async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    now = datetime.now()
    last_time = last_summary_time.get(chat_id, datetime.min)

    entries = list(user_data.get(chat_id, {}).values())
    filtered = [(label, amount) for t, label, amount in entries if t > last_time]


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
    text_filter = (filters.UpdateType.EDITED_MESSAGE & filters.TEXT & ~filters.COMMAND) | (filters.PHOTO & filters.Caption())
    app.add_handler(MessageHandler(text_filter, handle_message))
    print("✅ Bot is running...")
    await app.run_polling()

# Run main
if __name__ == "__main__":
    import nest_asyncio
    import asyncio

    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
