import json
import logging
import os
from typing import Dict

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

CLIENTS_FILE = "clients.json"

CATEGORY_LABELS = {
    "type": {"0": "неизвестно", "1": "физлицо", "2": "юрлицо", "3": "партнёр"},
    "source": {"0": "бот", "1": "вручную", "2": "сайт", "3": "реклама"},
    "status": {"0": "новый", "1": "в работе", "2": "оплата", "3": "закрыт"},
    "prio": {"0": "обычный", "1": "срочно", "2": "VIP", "3": "черный список"},
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_clients() -> Dict[str, Dict]:
    if os.path.exists(CLIENTS_FILE):
        with open(CLIENTS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_clients(clients: Dict[str, Dict]):
    with open(CLIENTS_FILE, "w") as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)


def get_code_description(code: str) -> str:
    parts = code.split(".")
    if len(parts) != 4:
        return "код некорректен"
    a, b, c, d = parts
    return (
        f"Тип: {CATEGORY_LABELS['type'].get(a, '?')} | "
        f"Источник: {CATEGORY_LABELS['source'].get(b, '?')} | "
        f"Статус: {CATEGORY_LABELS['status'].get(c, '?')} | "
        f"Приоритет: {CATEGORY_LABELS['prio'].get(d, '?')}"
    )


clients = load_clients()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Здравствуйте! Отправьте сообщение и наши сотрудники свяжутся с вами."
    )


async def handle_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text or ""
    client_id = str(user.id)

    if client_id not in clients:
        clients[client_id] = {
            "username": user.username or "",
            "name": user.full_name,
            "code": "0.0.0.0",
        }
        save_clients(clients)

    code = clients[client_id]["code"]
    crm_group_id = int(os.getenv("CRM_GROUP_ID", "0"))
    superchat_id = int(os.getenv("SUPERCHAT_ID", "0"))

    forward_text = (
        f"🔵 #{code} | @{user.username or 'nousername'} | {user.full_name}\n"
        f"✉️ {text}"
    )

    if crm_group_id:
        sent = await context.bot.send_message(crm_group_id, forward_text)
        context.bot_data.setdefault("crm_map", {})[sent.message_id] = client_id
    if superchat_id:
        await context.bot.send_message(superchat_id, forward_text)


async def relay_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return
    mapping = context.bot_data.get("crm_map", {})
    client_id = mapping.get(update.message.reply_to_message.message_id)
    if not client_id:
        return
    await context.bot.send_message(int(client_id), update.message.text)


async def set_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or not context.args:
        await update.message.reply_text(
            "Команда используется ответом на сообщение клиента и принимает код"
        )
        return
    mapping = context.bot_data.get("crm_map", {})
    client_id = mapping.get(update.message.reply_to_message.message_id)
    if not client_id:
        await update.message.reply_text("Не удалось определить клиента")
        return
    code = context.args[0]
    clients[client_id]["code"] = code
    save_clients(clients)
    desc = get_code_description(code)
    username = clients[client_id]["username"]
    await update.message.reply_text(
        f"Код установлен для @{username}: #{code}\n{desc}"
    )


async def update_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_code(update, context)


async def code_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "Команда используется ответом на сообщение клиента"
        )
        return
    mapping = context.bot_data.get("crm_map", {})
    client_id = mapping.get(update.message.reply_to_message.message_id)
    if not client_id:
        await update.message.reply_text("Не удалось определить клиента")
        return
    code = clients[client_id]["code"]
    desc = get_code_description(code)
    await update.message.reply_text(f"Текущий код: #{code}\n{desc}")


async def change_digit(update: Update, context: ContextTypes.DEFAULT_TYPE, index: int):
    if not update.message.reply_to_message or not context.args:
        await update.message.reply_text(
            "Команда используется ответом на сообщение клиента и принимает число"
        )
        return
    mapping = context.bot_data.get("crm_map", {})
    client_id = mapping.get(update.message.reply_to_message.message_id)
    if not client_id:
        await update.message.reply_text("Не удалось определить клиента")
        return
    value = context.args[0]
    code_parts = clients[client_id]["code"].split(".")
    if len(code_parts) != 4:
        code_parts = ["0", "0", "0", "0"]
    code_parts[index] = value
    new_code = ".".join(code_parts)
    clients[client_id]["code"] = new_code
    save_clients(clients)
    desc = get_code_description(new_code)
    await update.message.reply_text(f"Код обновлен: #{new_code}\n{desc}")


async def mark_prio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await change_digit(update, context, 3)


async def set_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await change_digit(update, context, 2)


async def set_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await change_digit(update, context, 0)


def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN env var is required")
    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT, handle_client))

    crm_chat_id = os.getenv("CRM_GROUP_ID", "")
    if crm_chat_id:
        crm_filters = filters.Chat(crm_chat_id) & filters.REPLY
        application.add_handler(MessageHandler(crm_filters & filters.TEXT & ~filters.COMMAND, relay_reply))
        application.add_handler(CommandHandler("setcode", set_code))
        application.add_handler(CommandHandler("updatecode", update_code))
        application.add_handler(CommandHandler("codeinfo", code_info))
        application.add_handler(CommandHandler("markprio", mark_prio))
        application.add_handler(CommandHandler("status", set_status))
        application.add_handler(CommandHandler("type", set_type))

    application.run_polling()


if __name__ == "__main__":
    main()
