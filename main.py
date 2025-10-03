import sqlite3
import pandas as pd
from datetime import datetime
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Подключаем настройки из config.py
from config import BOT_TOKEN, ADMIN_CHAT_ID

DB_PATH = "messages.db"


# --- Инициализация базы ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        chat_id INTEGER,
        username TEXT,
        full_name TEXT,
        message_text TEXT,
        timestamp TEXT
    )
    """)
    conn.commit()
    conn.close()


# --- Сохраняем сообщение в базу ---
def save_message(user_id, chat_id, username, full_name, message_text):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO messages (user_id, chat_id, username, full_name, message_text, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, chat_id, username, full_name, message_text, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


# --- Отправка инфо админу ---
async def send_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message is None:
        return

    chat = update.effective_chat
    user = update.effective_user
    message_text = update.effective_message.text_html or "—"

    save_message(
        user_id=user.id,
        chat_id=chat.id,
        username=user.username or "—",
        full_name=user.full_name,
        message_text=message_text,
    )

    if chat.type in ("group", "supergroup"):
        chat_title = chat.title or "Без названия"
        text = (
            f"📣 Новое сообщение в группе\n\n"
            f"Название группы: {chat_title}\n"
            f"Group ID: <code>{chat.id}</code>\n\n"
            f"Пользователь: {user.full_name}\n"
            f"Username: @{user.username if user.username else '—'}\n"
            f"User ID: <code>{user.id}</code>\n\n"
            f"Текст сообщения: {message_text}"
        )
    else:
        text = (
            f"💬 Личный чат/канал\n\n"
            f"Chat ID: <code>{chat.id}</code>\n"
            f"User: {user.full_name}\n"
            f"User ID: <code>{user.id}</code>\n"
            f"Текст: {message_text}"
        )

    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=text, parse_mode="HTML")
    except Exception as e:
        print("Ошибка при отправке админу:", e)


# --- Команда /start ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_ids(update, context)
    await update.effective_message.reply_text("Информация сохранена и отправлена администратору.")


# --- Команда /report ---
async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("⛔ У вас нет прав для этой команды.")
        return

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM messages", conn)
    conn.close()

    file_path = "report.xlsx"
    df.to_excel(file_path, index=False)

    await context.bot.send_document(
        chat_id=ADMIN_CHAT_ID,
        document=InputFile(file_path),
        filename="report.xlsx",
        caption="📊 Отчет по сообщениям"
    )


# --- Запуск бота ---
def main():
    if not BOT_TOKEN:
        raise ValueError("❌ Ошибка: BOT_TOKEN пустой. Добавь его в config.py!")

    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(MessageHandler(filters.ALL, send_ids))

    print("✅ Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
