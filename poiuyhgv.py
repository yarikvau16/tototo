import asyncio
import json
import os
import random
from datetime import datetime, timedelta
from collections import deque

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command


# =========================
# ⚙️ НАЛАШТУВАННЯ
# =========================

BOT_TOKEN = "8726114369:AAF_iloiVrG0n66JpTl-AL20U5W9mFlqVtc"
DATA_FILE = "users.json"

MIN_SECONDS_BETWEEN_COMMANDS = 8
MAX_LENGTH = 1000.0
MIN_LENGTH = -1000.0
ADMINS = [857466206]


# =========================
# ⏱ ЧАС
# =========================

def now():
    return datetime.utcnow()


def dt_to_str(dt):
    return dt.isoformat() if dt else None


def str_to_dt(s):
    try:
        return datetime.fromisoformat(s) if s else None
    except:
        return None


# =========================
# 💾 ЗБЕРЕЖЕННЯ
# =========================

def load_storage():
    if not os.path.exists(DATA_FILE):
        return {
            "users": {},
            "chats": [],
            "group_growth_log": {}
        }

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        return {
            "users": {},
            "chats": [],
            "group_growth_log": {}
        }

    for u in data["users"].values():
        u["last_growth_time"] = str_to_dt(u.get("last_growth_time"))
        u["last_use_time"] = str_to_dt(u.get("last_use_time"))
        u["last_command_time"] = str_to_dt(u.get("last_command_time"))
        u["mute_until"] = str_to_dt(u.get("mute_until"))

        msgs = []
        for x in u.get("messages_last_5h", []):
            dt = str_to_dt(x)
            if dt:
                msgs.append(dt)
        u["messages_last_5h"] = deque(msgs)

    return data


def save_storage(db):
    data = {
        "users": {},
        "chats": db["chats"],
        "group_growth_log": db["group_growth_log"]
    }

    for uid, u in db["users"].items():
        data["users"][uid] = {
            **u,
            "last_growth_time": dt_to_str(u["last_growth_time"]),
            "last_use_time": dt_to_str(u["last_use_time"]),
            "last_command_time": dt_to_str(u["last_command_time"]),
            "mute_until": dt_to_str(u["mute_until"]),
            "messages_last_5h": [dt_to_str(x) for x in u["messages_last_5h"]],
        }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# =========================
# 🎲 РАНДОМ
# =========================

def safe_random_delta():
    return round(sum(random.uniform(-12, 12) for _ in range(5)) / 5, 1)


# =========================
# 🤖 БОТ
# =========================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
db = load_storage()


# =========================
# 📌 ДОПОМІЖНЕ
# =========================

def get_user(user):
    uid = str(user.id)

    if uid not in db["users"]:
        db["users"][uid] = {
            "name": user.username or user.first_name,
            "length": 0.0,
            "requests": 0,
            "streak": 0,
            "last_growth_time": None,
            "last_use_time": None,
            "last_command_time": None,
            "last_growth_chat": None,
            "messages_last_5h": deque(),
            "spam_warnings_sent": 0,
            "mute_until": None,
        }

    return db["users"][uid]


def add_chat(chat_id):
    if chat_id not in db["chats"]:
        db["chats"].append(chat_id)


# =========================
# 🚀 КОМАНДИ
# =========================

@dp.message(Command("start"))
async def start(msg: types.Message):
    add_chat(msg.chat.id)

    await msg.answer(
        "Команди:\n"
        "/pipisabotik — перевірити довжину\n"
        "/addyogroup — як додати в групу\n"
        "/admainpussy333 chat_id текст — адмін розсилка\n"
        "/adminlist — список даних"
    )


@dp.message(Command("addyogroup"))
async def add_group(msg: types.Message):
    await msg.answer("Додай бота в групу і дай права адміністратора")


# =========================
# 🍆 ОСНОВНА ЛОГІКА
# =========================

@dp.message(Command("pipisabotik"))
async def pipisa(msg: types.Message):
    user = get_user(msg.from_user)
    add_chat(msg.chat.id)

    t = now()

    if user["mute_until"] and t < user["mute_until"]:
        await msg.answer("Ти в муті")
        return

    user["messages_last_5h"] = deque(
        x for x in user["messages_last_5h"]
        if x and x > t - timedelta(hours=5)
    )
    user["messages_last_5h"].append(t)

    if len(user["messages_last_5h"]) > 8:
        if user["spam_warnings_sent"] < 2:
            user["spam_warnings_sent"] += 1
            await msg.answer("Занадто швидко!")
            return
        else:
            user["mute_until"] = t + timedelta(hours=12)
            await msg.answer("Мут 12 год")
            return

    if user["last_command_time"]:
        if (t - user["last_command_time"]).total_seconds() < MIN_SECONDS_BETWEEN_COMMANDS:
            return

    user["last_command_time"] = t

    if user["last_growth_time"]:
        if t - user["last_growth_time"] < timedelta(hours=24):
            await msg.answer("Ще не пройшло 24 години")
            return

    delta = safe_random_delta()
    user["length"] = max(MIN_LENGTH, min(MAX_LENGTH, user["length"] + delta))
    user["requests"] += 1

    today = t.date()
    last = user["last_use_time"].date() if user["last_use_time"] else None

    if last == today:
        pass
    elif last and last + timedelta(days=1) == today:
        user["streak"] += 1
    else:
        user["streak"] = 1

    user["last_use_time"] = t
    user["last_growth_time"] = t
    user["last_growth_chat"] = msg.chat.id

    verb = "виріс" if delta >= 0 else "зменшився"
    mood = "растем 💪" if user["length"] >= 0 else "це из-за холода 🥶"

    reply = (
        f"{user['name']}, твій дружок сьогодні {verb} на {abs(delta):.1f} см.\n"
        f"Довжина зараз: {user['length']:.1f} см\n"
        f"Стрік: {user['streak']} днів\n"
        f"Це твій {user['requests']}-й запит\n"
        f"{mood}"
    )

    await msg.answer(reply)
    save_storage(db)


# =========================
# 👑 АДМІН
# =========================

@dp.message(Command("admainpussy333"))
async def admin_send(msg: types.Message):
    if msg.from_user.id not in ADMINS:
        await msg.answer("Тільки адмін")
        return

    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        await msg.answer("формат: /admainpussy333 chat_id текст")
        return

    chat_id = int(parts[1])
    text = parts[2]

    try:
        await bot.send_message(chat_id, text)
        await msg.answer("надіслано")
    except Exception as e:
        await msg.answer(str(e))


@dp.message(Command("adminlist"))
async def admin_list(msg: types.Message):
    if msg.from_user.id not in ADMINS:
        return

    text = "Чати:\n"
    for c in db["chats"]:
        text += f"{c}\n"

    text += "\nКористувачі:\n"
    for uid, u in db["users"].items():
        text += f"{uid} | {u['name']} | {u['length']:.1f} см\n"

    await msg.answer(text)


# =========================
# ▶️ ЗАПУСК
# =========================

async def main():
    print("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())