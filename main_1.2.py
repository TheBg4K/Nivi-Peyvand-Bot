import zipfile
import tempfile
from datetime import datetime, timedelta
import logging
import calendar
import shutil
import os
from datetime import datetime
import telebot
import sqlite3
import jdatetime
from datetime import datetime, date, timedelta
from telebot.types import *
import re
import threading
import json
import time
import random
import psutil
import platform
import os
from dotenv import load_dotenv
import telebot
from telebot import types
import sqlite3
from telebot import TeleBot
from colorama import Fore, Back, Style, init
import sys
import logging
from io import StringIO


reply_map = {}


# ?LOGER!


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)


logger = logging.getLogger(__name__)


init(autoreset=True)
API_TOKEN = ""
bot = telebot.TeleBot(API_TOKEN)


bot = telebot.TeleBot(API_TOKEN)


@bot.message_handler(commands=['start', 'restart'])
def start_handler(message):
    try:
        print(f"🔔 DEBUG: Start received from {message.chat.id}")

        uid = message.chat.id

        
        try:
            result = safe_execute_db(
                "SELECT * FROM users WHERE user_id = ?", (uid,))
            print(f"🔔 DEBUG: Database check result: {result}")
        except Exception as e:
            print(f"❌ DEBUG: Database error: {e}")
            result = None

        if result:
            print(f"✅ DEBUG: Existing user")
            bot.send_message(uid, "👋 خوش اومدی دوباره!",
                             reply_markup=main_menu())
            return

        # کاربر جدید
        print(f"🆕 DEBUG: New user")
        user_state[uid] = "gender"
        temp_data[uid] = {}

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("مرد 😎", callback_data="gender_مرد"),
            InlineKeyboardButton("زن 😏", callback_data="gender_زن")
        )
        bot.send_message(
            uid, "به ربات خوش اومدی! جنسیتت چیه؟ 😊", reply_markup=markup)

        print(f"✅ DEBUG: Start completed successfully")

    except Exception as e:
        print(f"❌ DEBUG: Start handler crashed: {e}")
        import traceback
        traceback.print_exc()


# اتصال به دیتابیس کاربران
conn_users = sqlite3.connect(
    "relation_agent.db", check_same_thread=False, isolation_level=None)
cur_users = conn_users.cursor()
cur_users.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    gender TEXT,
    name TEXT,
    birthdate TEXT,
    region TEXT DEFAULT 'ایران',
    partner_name TEXT,
    partner_birthdate TEXT,
    partner_age INTEGER,
    partner_nick TEXT,
    relation_type TEXT,
    start_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn_users.commit()


conn_notifications = sqlite3.connect(
    "notifications.db", check_same_thread=False, isolation_level=None)
cur_notifications = conn_notifications.cursor()
cur_notifications.execute("""
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    event_date TEXT NOT NULL,
    repeat_type TEXT DEFAULT 'none',
    notify_times TEXT DEFAULT '[]',
    sent_flags TEXT DEFAULT '[]',
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
)
""")


conn_notifications.commit()

# متغیرهای global
user_state = {}
temp_data = {}
temp_event_data = {}
db_lock = threading.Lock()


# لیست‌های پیام‌های رندوم
random_messages = [
    "🎉 امروز یه روز فوق‌العاده است!",
    "💖 عشق در هواست، لذت ببر!",
    "😎 یه تجربه جدید منتظرت هست!",
    "🌈 لبخند بزن، دنیا منتظر توست!",
    "✨ امروز می‌تونه شگفتی داشته باشه!",
    "🔥 یه اتفاق جذاب در راهه!",
    "🍀 شانس با توست، مراقب باش!",
    "🎁 یه هدیه کوچک در راهته!",
    "💫 انرژی مثبت رو حس کن!"
]

flirt_messages = [
    "💖 دلم برات تنگ شده عزیزم...",
    "🔥 امروز چقدر داغونی! میسوزونیم...",
    "😘 میدونی چقدر دوستت دارم؟ به اندازه تمام ستاره‌های آسمون!",
    "🌟 نگاهت ستاره‌ها رو خجالت زده میکنه...",
    "💋 فقط بذار یه بوسه کوچولو روی گونه‌هات...",
    "🫂 دلم هوات رو کرده... بغلم کن!",
    "✨ وجودت رو با هیچ چیزی عوض نمیکنم",
    "🌹 مثل گل می‌درخشی عزیزم",
    "💞 قلبم فقط برای تو میتپه",
    "🔥 عشقم برات بی‌قراره...",
    "🌸 بودن با تو قشنگترین حس دنیاست",
    "💕 هر لحظه با تو رو لحظه‌ای خاص میدونم"
]

suggestion_messages = [
    "💡 پیشنهاد: یه شام رمانتیک برنامه‌ریزی کن!",
    "💡 پیشنهاد: یه نامه عاشقانه بنویس و براش بخون!",
    "💡 پیشنهاد: یه هدیه کوچیک غافلگیرکننده بده!",
    "💡 پیشنهاد: یه قرار خاص و متفاوت بذار!",
    "💡 پیشنهاد: قدردانیت رو با کلمات قشنگ ابراز کن!",
    "💡 پیشنهاد: یه فعالیت جدید با هم انجام بدید!",
    "💡 پیشنهاد: خاطرات قشنگتون رو مرور کنید!",
    "💡 پیشنهاد: برای آینده رویایی‌تون برنامه‌ریزی کنید!",
    "💡 پیشنهاد: یه آهنگ عاشقانه براش بفرست!",
    "💡 پیشنهاد: یه تماس تصویری غافلگیرکننده داشته باش!"
]





DB_PATH = "relation_agent.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def calculate_age(birthdate_str):
    if not birthdate_str or birthdate_str == "ندارم":
        return None
    try:
        birth_date = datetime.strptime(birthdate_str, "%Y-%m-%d")
        today = datetime.now()
        age = today.year - birth_date.year
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
        return age
    except:
        return None


def get_user_stats(user_id):
    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()

    if not user:
        return None

    chat_folders = []
    if os.path.exists("anonymous_chats"):
        for folder in os.listdir("anonymous_chats"):
            folder_path = os.path.join("anonymous_chats", folder)
            if os.path.isdir(folder_path):
                json_file = os.path.join(folder_path, "chat_data.json")
                if os.path.exists(json_file):
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if data.get("user1_id") == user_id or data.get("user2_id") == user_id:
                            chat_folders.append(folder)

    total_chats = len(chat_folders)

    total_messages = 0
    for folder in chat_folders:
        json_file = os.path.join("anonymous_chats", folder, "chat_data.json")
        if os.path.exists(json_file):
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                total_messages += len(data.get("messages", []))

    return {
        "user_id": user["user_id"],
        "name": user["name"] if user["name"] else "نامشخص",
        "gender": user["gender"] if user["gender"] else "مشخص نشده",
        "birthdate": user["birthdate"] if user["birthdate"] else "ندارم",
        "age": calculate_age(user["birthdate"]) if user["birthdate"] and user["birthdate"] != "ندارم" else None,
        "region": user["region"] if user["region"] else "ایران",
        "partner_name": user["partner_name"] if user["partner_name"] and user["partner_name"] != "ندارم" else "بدون پارتنر",
        "connection_status": user["connection_status"] if user["connection_status"] else "single",
        "total_chats": total_chats,
        "total_messages": total_messages,
        "user_score": 0
    }


def get_user_score(user_id):
    score_file = f"user_scores/{user_id}.json"
    if os.path.exists(score_file):
        with open(score_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("score", 0)
    return 0


@bot.callback_query_handler(func=lambda call: call.data == "sec_chat")
def handle_anonymous_chat_section(call: CallbackQuery):
    user_id = call.from_user.id

    main_menu = InlineKeyboardMarkup(row_width=1)
    info_button = InlineKeyboardButton(
        "📋 اطلاعات من", callback_data="show_my_info")
    chat_button = InlineKeyboardButton(
        "💬 چت ناشناس", callback_data="anonymous_chat_menu")
    main_menu.add(info_button, chat_button)

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🔒 *بخش چت ناشناس*\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=main_menu,
        parse_mode="Markdown"
    )


@bot.callback_query_handler(func=lambda call: call.data == "show_my_info")
def show_my_info(call: CallbackQuery):
    user_id = call.from_user.id
    user_stats = get_user_stats(user_id)

    if not user_stats:
        bot.answer_callback_query(call.id, "❌ اطلاعات شما یافت نشد!")
        return

    user_score = get_user_score(user_id)

    partner_status = "✅ داشتن پارتنر" if user_stats["partner_name"] != "بدون پارتنر" else "❌ بدون پارتنر"
    if user_stats["partner_name"] != "بدون پارتنر":
        partner_status += f" (نام: {user_stats['partner_name']})"

    age_text = f"{user_stats['age']} سال" if user_stats['age'] is not None else "نامشخص"

    info_text = f"""📋 *اطلاعات شما*

👤 *نام:* {user_stats['name']}
💑 *وضعیت پارتنر:* {partner_status}
🎂 *تاریخ تولد:* {user_stats['birthdate']} ({age_text})
🌍 *ریجن:* {user_stats['region']}
🆔 *آیدی عددی:* {user_stats['user_id']}
💬 *تعداد چت‌ها:* {user_stats['total_chats']}
📝 *تعداد پیام‌ها:* {user_stats['total_messages']}
⭐ *امتیاز:* {user_score}"""

    back_button = InlineKeyboardMarkup()
    back_button.add(InlineKeyboardButton("🔙 بازگشت", callback_data="sec_Chat"))

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=info_text,
        reply_markup=back_button,
        parse_mode="Markdown"
    )


@bot.callback_query_handler(func=lambda call: call.data == "anonymous_chat_menu")
def anonymous_chat_menu(call: CallbackQuery):
    chat_options = InlineKeyboardMarkup(row_width=2)

    btn_random = InlineKeyboardButton(
        "🎲 چت شانسی", callback_data="dummy_random_chat")
    btn_with_girl = InlineKeyboardButton(
        "👧 چت با دختر", callback_data="dummy_chat_with_girl")
    btn_with_boy = InlineKeyboardButton(
        "👦 چت با پسر", callback_data="dummy_chat_with_boy")
    btn_group = InlineKeyboardButton(
        "👥 چت گروهی", callback_data="dummy_group_chat")
    btn_couple = InlineKeyboardButton(
        "💑 چت کاپلی", callback_data="dummy_couple_chat")
    btn_same_age = InlineKeyboardButton(
        "🎂 چت با همسن", callback_data="dummy_same_age_chat")
    btn_back = InlineKeyboardButton("🔙 بازگشت", callback_data="sec_Chat")

    chat_options.add(btn_random, btn_with_girl, btn_with_boy,
                     btn_group, btn_couple, btn_same_age)
    chat_options.add(btn_back)

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🎯 *انتخاب نوع چت ناشناس*\n\nلطفاً نوع چت مورد نظر خود را انتخاب کنید:",
        reply_markup=chat_options,
        parse_mode="Markdown"
    )


def any():
    if not os.path.exists("anonymous_chats"):
        os.makedirs("anonymous_chats")
    if not os.path.exists("user_scores"):
        os.makedirs("user_scores")


DB_PATH = "relation_agent.db"
ACTIVE_CHATS = {}
WAITING_QUEUE = {
    "random": [],
    "with_girl": [],
    "with_boy": [],
    "same_age": []
}


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def calculate_age(birthdate_str):
    if not birthdate_str or birthdate_str == "ندارم":
        return None
    try:
        birth_date = datetime.strptime(birthdate_str, "%Y-%m-%d")
        today = datetime.now()
        age = today.year - birth_date.year
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
        return age
    except:
        return None


def get_user_score(user_id):
    score_file = f"user_scores/{user_id}.json"
    if os.path.exists(score_file):
        with open(score_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("score", 0)
    return 0


def update_user_score(user_id, new_score):
    if not os.path.exists("user_scores"):
        os.makedirs("user_scores")
    score_file = f"user_scores/{user_id}.json"
    with open(score_file, "w", encoding="utf-8") as f:
        json.dump({"score": new_score}, f, ensure_ascii=False)


def get_user_info(user_id):
    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if not user:
        return None
    return {
        "user_id": user["user_id"],
        "name": user["name"] if user["name"] else "نامشخص",
        "gender": user["gender"] if user["gender"] else "مشخص نشده",
        "birthdate": user["birthdate"],
        "age": calculate_age(user["birthdate"]),
        "region": user["region"] if user["region"] else "ایران",
        "partner_name": user["partner_name"] if user["partner_name"] and user["partner_name"] != "ندارم" else None,
        "connection_status": user["connection_status"] if user["connection_status"] else "single"
    }


def load_truth_dare_questions():
    if os.path.exists("truth_dare_questions.json"):
        with open("truth_dare_questions.json", "r", encoding="utf-8") as f:
            return json.load(f)
    default_questions = {
        "truth": [
            "آخرین باری که گریه کردی کی بود؟",
            "یک راز که به کسی نگفتی بگو؟",
            "تا حالا عاشق شدی؟"
        ],
        "dare": [
            "یک آهنگ بخوان",
            "یک حرکت خنده‌دار انجام بده",
            "به بهترین دوستت زنگ بزن و بگو دوستت دارم"
        ]
    }
    with open("truth_dare_questions.json", "w", encoding="utf-8") as f:
        json.dump(default_questions, f, ensure_ascii=False, indent=2)
    return default_questions


def save_message_to_session(chat_session_id, message_data):
    session_path = f"anonymous_chats/{chat_session_id}"
    json_file = os.path.join(session_path, "chat_data.json")

    if not os.path.exists(json_file):
        return

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["messages"].append(message_data)

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_file_to_session(chat_session_id, file_path, file_type):
    session_path = f"anonymous_chats/{chat_session_id}"
    files_folder = os.path.join(session_path, "files")

    if not os.path.exists(files_folder):
        os.makedirs(files_folder)

    file_name = os.path.basename(file_path)
    dest_path = os.path.join(files_folder, file_name)
    shutil.copy(file_path, dest_path)
    return dest_path


def find_match(user_id, chat_type):
    user_info = get_user_info(user_id)
    if not user_info:
        return None

    user_score = get_user_score(user_id)
    conn = get_db_connection()

    if chat_type == "random":
        query = """
            SELECT user_id FROM users 
            WHERE user_id != ? AND connection_status = 'single'
        """
        candidates = conn.execute(query, (user_id,)).fetchall()

        if not candidates:
            conn.close()
            return None

        scored_candidates = []
        for candidate in candidates:
            cand_id = candidate["user_id"]
            cand_info = get_user_info(cand_id)
            if not cand_info:
                continue
            cand_score = get_user_score(cand_id)
            has_partner = 1 if cand_info["partner_name"] else 0
            user_has_partner = 1 if user_info["partner_name"] else 0
            priority = (cand_score, 1 if has_partner ==
                        user_has_partner else 0)
            scored_candidates.append((priority, cand_id))

        scored_candidates.sort(key=lambda x: (x[0][0], x[0][1]), reverse=True)
        conn.close()
        return scored_candidates[0][1] if scored_candidates else None

    elif chat_type == "with_girl":
        query = """
            SELECT user_id FROM users 
            WHERE user_id != ? AND gender = 'زن' AND connection_status = 'single'
        """
        candidates = conn.execute(query, (user_id,)).fetchall()

        if not candidates:
            conn.close()
            return None

        scored_candidates = []
        for candidate in candidates:
            cand_id = candidate["user_id"]
            cand_info = get_user_info(cand_id)
            if not cand_info:
                continue
            cand_score = get_user_score(cand_id)
            has_partner = 1 if cand_info["partner_name"] else 0
            user_has_partner = 1 if user_info["partner_name"] else 0

            age_diff = None
            if user_info["age"] and cand_info["age"]:
                if cand_info["age"] < user_info["age"] and (user_info["age"] - cand_info["age"]) <= 2:
                    age_diff = user_info["age"] - cand_info["age"]
                elif cand_info["age"] == user_info["age"]:
                    age_diff = 0

            priority = (cand_score, 1 if has_partner ==
                        user_has_partner else 0, age_diff)
            scored_candidates.append((priority, cand_id))

        scored_candidates.sort(key=lambda x: (
            x[0][0], x[0][1], x[0][2] is not None, x[0][2] if x[0][2] is not None else 999), reverse=True)

        if scored_candidates and scored_candidates[0][0][2] is not None:
            conn.close()
            return scored_candidates[0][1]

        random_candidate = random.choice(candidates) if candidates else None
        conn.close()
        return random_candidate["user_id"] if random_candidate else None

    elif chat_type == "with_boy":
        query = """
            SELECT user_id FROM users 
            WHERE user_id != ? AND gender = 'مرد' AND connection_status = 'single'
        """
        candidates = conn.execute(query, (user_id,)).fetchall()

        if not candidates:
            conn.close()
            return None

        scored_candidates = []
        for candidate in candidates:
            cand_id = candidate["user_id"]
            cand_info = get_user_info(cand_id)
            if not cand_info:
                continue
            cand_score = get_user_score(cand_id)
            has_partner = 1 if cand_info["partner_name"] else 0
            user_has_partner = 1 if user_info["partner_name"] else 0

            age_diff = None
            if user_info["age"] and cand_info["age"]:
                if cand_info["age"] > user_info["age"] and (cand_info["age"] - user_info["age"]) <= 2:
                    age_diff = cand_info["age"] - user_info["age"]
                elif cand_info["age"] == user_info["age"]:
                    age_diff = 0

            priority = (cand_score, 1 if has_partner ==
                        user_has_partner else 0, age_diff)
            scored_candidates.append((priority, cand_id))

        scored_candidates.sort(key=lambda x: (
            x[0][0], x[0][1], x[0][2] is not None, x[0][2] if x[0][2] is not None else 999), reverse=True)

        if scored_candidates and scored_candidates[0][0][2] is not None:
            conn.close()
            return scored_candidates[0][1]

        random_candidate = random.choice(candidates) if candidates else None
        conn.close()
        return random_candidate["user_id"] if random_candidate else None

    elif chat_type == "same_age":
        user_age = user_info["age"]
        if not user_age:
            conn.close()
            return None

        query = """
            SELECT user_id FROM users 
            WHERE user_id != ? AND connection_status = 'single'
        """
        candidates = conn.execute(query, (user_id,)).fetchall()
        conn.close()

        if not candidates:
            return None

        same_age_candidates = []
        for candidate in candidates:
            cand_id = candidate["user_id"]
            cand_info = get_user_info(cand_id)
            if not cand_info or not cand_info["age"]:
                continue

            age_diff = abs(user_age - cand_info["age"])
            if age_diff <= 1:
                if user_info["gender"] == "مرد":
                    if cand_info["age"] == user_age - 1:
                        priority = 1
                    elif cand_info["age"] == user_age:
                        priority = 2
                    else:
                        continue
                else:
                    if cand_info["age"] == user_age + 1:
                        priority = 1
                    elif cand_info["age"] == user_age:
                        priority = 2
                    else:
                        continue

                cand_score = get_user_score(cand_id)
                same_age_candidates.append((priority, cand_score, cand_id))

        if same_age_candidates:
            same_age_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
            return same_age_candidates[0][2]

        return None


def create_chat_session(user1_id, user2_id, chat_type):
    session_id = f"{user1_id}_{user2_id}_{int(datetime.now().timestamp())}"
    session_path = f"anonymous_chats/{session_id}"

    if not os.path.exists(session_path):
        os.makedirs(session_path)

    files_folder = os.path.join(session_path, "files")
    if not os.path.exists(files_folder):
        os.makedirs(files_folder)

    chat_data = {
        "session_id": session_id,
        "chat_type": chat_type,
        "user1_id": user1_id,
        "user2_id": user2_id,
        "start_time": datetime.now().isoformat(),
        "messages": [],
        "used_questions": {
            "truth": [],
            "dare": []
        }
    }

    json_file = os.path.join(session_path, "chat_data.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(chat_data, f, ensure_ascii=False, indent=2)

    return session_id


def get_active_session(user_id):
    for session_id, users in ACTIVE_CHATS.items():
        if user_id in users:
            return session_id
    return None


def send_question_to_chat(session_id, question_type):
    if session_id not in ACTIVE_CHATS:
        return

    users = ACTIVE_CHATS[session_id]
    session_path = f"anonymous_chats/{session_id}"
    json_file = os.path.join(session_path, "chat_data.json")

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions_db = load_truth_dare_questions()
    available_questions = [q for q in questions_db[question_type]
                           if q not in data["used_questions"][question_type]]

    if not available_questions:
        for user_id in users:
            bot.send_message(user_id, "⚠️ سوالات این بخش به پایان رسیده است!")
        return

    selected_question = random.choice(available_questions)
    data["used_questions"][question_type].append(selected_question)

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    question_text = f"❓ *سوال {question_type}*\n\n{selected_question}"
    for user_id in users:
        bot.send_message(user_id, question_text, parse_mode="Markdown")


def show_profile_preview(user_id, viewer_id):
    user_info = get_user_info(user_id)
    if not user_info:
        return "اطلاعاتی یافت نشد"

    partner_status = "دارد" if user_info["partner_name"] else "ندارد"
    age_text = f"{user_info['age']} سال" if user_info['age'] else "نامشخص"

    profile_text = f"""👤 *پروفایل کاربر*

📛 *نام:* {user_info['name']}
🎂 *سن:* {age_text}
🌍 *ریجن:* {user_info['region']}
💑 *وضعیت پارتنر:* {partner_status}"""

    return profile_text


ACTIVE_CHATS = {}
WAITING_QUEUE = {
    "random": [],
    "with_girl": [],
    "with_boy": [],
    "same_age": []
}
CHAT_PARTNERS = {}


def get_active_session(user_id):
    if user_id in CHAT_PARTNERS:
        return CHAT_PARTNERS[user_id]
    return None


def find_match(user_id, chat_type):
    user_info = get_user_info(user_id)
    if not user_info:
        return None

    if user_id not in WAITING_QUEUE[chat_type]:
        return None

    conn = get_db_connection()
    candidates = []

    if chat_type == "random":
        query = "SELECT user_id FROM users WHERE user_id != ? AND connection_status = 'single'"
        all_candidates = conn.execute(query, (user_id,)).fetchall()
        for c in all_candidates:
            if c["user_id"] in WAITING_QUEUE["random"] and c["user_id"] != user_id:
                candidates.append(c["user_id"])
    elif chat_type == "with_girl":
        query = "SELECT user_id FROM users WHERE user_id != ? AND gender = 'زن' AND connection_status = 'single'"
        all_candidates = conn.execute(query, (user_id,)).fetchall()
        for c in all_candidates:
            if c["user_id"] in WAITING_QUEUE["with_girl"] and c["user_id"] != user_id:
                candidates.append(c["user_id"])
    elif chat_type == "with_boy":
        query = "SELECT user_id FROM users WHERE user_id != ? AND gender = 'مرد' AND connection_status = 'single'"
        all_candidates = conn.execute(query, (user_id,)).fetchall()
        for c in all_candidates:
            if c["user_id"] in WAITING_QUEUE["with_boy"] and c["user_id"] != user_id:
                candidates.append(c["user_id"])
    elif chat_type == "same_age":
        query = "SELECT user_id FROM users WHERE user_id != ? AND connection_status = 'single'"
        all_candidates = conn.execute(query, (user_id,)).fetchall()
        for c in all_candidates:
            if c["user_id"] in WAITING_QUEUE["same_age"] and c["user_id"] != user_id:
                candidates.append(c["user_id"])

    conn.close()

    if not candidates:
        return None

    scored_candidates = []
    for cand_id in candidates:
        cand_info = get_user_info(cand_id)
        if not cand_info:
            continue
        cand_score = get_user_score(cand_id)
        has_partner = 1 if cand_info["partner_name"] else 0
        user_has_partner = 1 if user_info["partner_name"] else 0

        if chat_type == "random":
            priority = (cand_score, 1 if has_partner ==
                        user_has_partner else 0)
            scored_candidates.append((priority, cand_id))
        elif chat_type == "with_girl":
            age_diff = None
            if user_info["age"] and cand_info["age"]:
                if cand_info["age"] < user_info["age"] and (user_info["age"] - cand_info["age"]) <= 2:
                    age_diff = user_info["age"] - cand_info["age"]
                elif cand_info["age"] == user_info["age"]:
                    age_diff = 0
            priority = (cand_score, 1 if has_partner ==
                        user_has_partner else 0, age_diff)
            scored_candidates.append((priority, cand_id))
        elif chat_type == "with_boy":
            age_diff = None
            if user_info["age"] and cand_info["age"]:
                if cand_info["age"] > user_info["age"] and (cand_info["age"] - user_info["age"]) <= 2:
                    age_diff = cand_info["age"] - user_info["age"]
                elif cand_info["age"] == user_info["age"]:
                    age_diff = 0
            priority = (cand_score, 1 if has_partner ==
                        user_has_partner else 0, age_diff)
            scored_candidates.append((priority, cand_id))
        elif chat_type == "same_age":
            if not user_info["age"] or not cand_info["age"]:
                continue
            age_diff = abs(user_info["age"] - cand_info["age"])
            if age_diff <= 1:
                if user_info["gender"] == "مرد":
                    if cand_info["age"] == user_info["age"] - 1:
                        priority = 1
                    elif cand_info["age"] == user_info["age"]:
                        priority = 2
                    else:
                        continue
                else:
                    if cand_info["age"] == user_info["age"] + 1:
                        priority = 1
                    elif cand_info["age"] == user_info["age"]:
                        priority = 2
                    else:
                        continue
                scored_candidates.append(((priority, cand_score), cand_id))

    if not scored_candidates:
        return None

    if chat_type in ["random", "with_girl", "with_boy"]:
        scored_candidates.sort(key=lambda x: (x[0][0], x[0][1]), reverse=True)
    else:
        scored_candidates.sort(key=lambda x: (x[0][0], x[0][1]), reverse=True)

    best_match = scored_candidates[0][1]
    if best_match in WAITING_QUEUE[chat_type]:
        WAITING_QUEUE[chat_type].remove(best_match)
    if user_id in WAITING_QUEUE[chat_type]:
        WAITING_QUEUE[chat_type].remove(user_id)

    return best_match


@bot.callback_query_handler(func=lambda call: call.data == "dummy_random_chat")
def start_random_chat(call: CallbackQuery):
    user_id = call.from_user.id
    active_session = get_active_session(user_id)
    if active_session:
        bot.answer_callback_query(
            call.id, "شما در حال حاضر در یک چت ناشناس هستید! ابتدا چت فعلی را پایان دهید.", show_alert=True)
        return
    user_info = get_user_info(user_id)
    if not user_info:
        bot.answer_callback_query(
            call.id, "خطا در دریافت اطلاعات کاربر!", show_alert=True)
        return
    if user_info["connection_status"] != "single":
        bot.answer_callback_query(
            call.id, "شما در حالت جفت هستید و نمی‌توانید چت ناشناس شروع کنید!", show_alert=True)
        return
    if user_id in WAITING_QUEUE["random"]:
        bot.answer_callback_query(
            call.id, "شما قبلاً در صف انتظار هستید!", show_alert=True)
        return

    WAITING_QUEUE["random"].append(user_id)
    match_id = find_match(user_id, "random")

    if match_id:
        session_id = create_chat_session(user_id, match_id, "random")
        ACTIVE_CHATS[session_id] = [user_id, match_id]
        CHAT_PARTNERS[user_id] = session_id
        CHAT_PARTNERS[match_id] = session_id
        for uid in [user_id, match_id]:
            chat_markup = InlineKeyboardMarkup(row_width=1)
            chat_markup.add(
                InlineKeyboardButton(
                    "👤 مشاهده پروفایل", callback_data=f"view_profile_{session_id}"),
                InlineKeyboardButton("🎲 بازی جرعت حقیقت",
                                     callback_data=f"game_menu_{session_id}"),
                InlineKeyboardButton(
                    "🚪 خروج از چت", callback_data=f"exit_chat_{session_id}")
            )
            bot.send_message(uid, "✅ *شما به یک کاربر متصل شدید!*\n\nبرای مشاهده گزینه‌های چت از دکمه‌های زیر استفاده کنید:",
                             reply_markup=chat_markup, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "پارتنر پیدا شد! چت شروع شد.")
    else:
        queue_markup = InlineKeyboardMarkup()
        queue_markup.add(InlineKeyboardButton(
            "🚪 خروج از صف انتظار", callback_data=f"exit_queue_random"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text="⏳ *در صف انتظار قرار گرفتید*\n\nبه محض پیدا شدن پارتنر مناسب به شما اطلاع داده می‌شود.\n\nبرای خروج از صف روی دکمه زیر کلیک کنید:", reply_markup=queue_markup, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "به صف انتظار اضافه شدید!")


@bot.callback_query_handler(func=lambda call: call.data == "dummy_chat_with_girl")
def start_chat_with_girl(call: CallbackQuery):
    user_id = call.from_user.id
    active_session = get_active_session(user_id)
    if active_session:
        bot.answer_callback_query(
            call.id, "شما در حال حاضر در یک چت ناشناس هستید! ابتدا چت فعلی را پایان دهید.", show_alert=True)
        return
    user_info = get_user_info(user_id)
    if not user_info:
        bot.answer_callback_query(
            call.id, "خطا در دریافت اطلاعات کاربر!", show_alert=True)
        return
    if user_info["connection_status"] != "single":
        bot.answer_callback_query(
            call.id, "شما در حالت جفت هستید و نمی‌توانید چت ناشناس شروع کنید!", show_alert=True)
        return
    if user_id in WAITING_QUEUE["with_girl"]:
        bot.answer_callback_query(
            call.id, "شما قبلاً در صف انتظار هستید!", show_alert=True)
        return

    WAITING_QUEUE["with_girl"].append(user_id)
    match_id = find_match(user_id, "with_girl")

    if match_id:
        session_id = create_chat_session(user_id, match_id, "with_girl")
        ACTIVE_CHATS[session_id] = [user_id, match_id]
        CHAT_PARTNERS[user_id] = session_id
        CHAT_PARTNERS[match_id] = session_id
        for uid in [user_id, match_id]:
            chat_markup = InlineKeyboardMarkup(row_width=1)
            chat_markup.add(
                InlineKeyboardButton(
                    "👤 مشاهده پروفایل", callback_data=f"view_profile_{session_id}"),
                InlineKeyboardButton("🎲 بازی جرعت حقیقت",
                                     callback_data=f"game_menu_{session_id}"),
                InlineKeyboardButton(
                    "🚪 خروج از چت", callback_data=f"exit_chat_{session_id}")
            )
            bot.send_message(uid, "✅ *شما به یک کاربر متصل شدید!*\n\nبرای مشاهده گزینه‌های چت از دکمه‌های زیر استفاده کنید:",
                             reply_markup=chat_markup, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "پارتنر پیدا شد! چت شروع شد.")
    else:
        queue_markup = InlineKeyboardMarkup()
        queue_markup.add(InlineKeyboardButton(
            "🚪 خروج از صف انتظار", callback_data=f"exit_queue_with_girl"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text="⏳ *در صف انتظار قرار گرفتید*\n\nبه محض پیدا شدن دختر مناسب به شما اطلاع داده می‌شود.\n\nبرای خروج از صف روی دکمه زیر کلیک کنید:", reply_markup=queue_markup, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "به صف انتظار اضافه شدید!")


@bot.callback_query_handler(func=lambda call: call.data == "dummy_chat_with_boy")
def start_chat_with_boy(call: CallbackQuery):
    user_id = call.from_user.id
    active_session = get_active_session(user_id)
    if active_session:
        bot.answer_callback_query(
            call.id, "شما در حال حاضر در یک چت ناشناس هستید! ابتدا چت فعلی را پایان دهید.", show_alert=True)
        return
    user_info = get_user_info(user_id)
    if not user_info:
        bot.answer_callback_query(
            call.id, "خطا در دریافت اطلاعات کاربر!", show_alert=True)
        return
    if user_info["connection_status"] != "single":
        bot.answer_callback_query(
            call.id, "شما در حالت جفت هستید و نمی‌توانید چت ناشناس شروع کنید!", show_alert=True)
        return
    if user_id in WAITING_QUEUE["with_boy"]:
        bot.answer_callback_query(
            call.id, "شما قبلاً در صف انتظار هستید!", show_alert=True)
        return

    WAITING_QUEUE["with_boy"].append(user_id)
    match_id = find_match(user_id, "with_boy")

    if match_id:
        session_id = create_chat_session(user_id, match_id, "with_boy")
        ACTIVE_CHATS[session_id] = [user_id, match_id]
        CHAT_PARTNERS[user_id] = session_id
        CHAT_PARTNERS[match_id] = session_id
        for uid in [user_id, match_id]:
            chat_markup = InlineKeyboardMarkup(row_width=1)
            chat_markup.add(
                InlineKeyboardButton(
                    "👤 مشاهده پروفایل", callback_data=f"view_profile_{session_id}"),
                InlineKeyboardButton("🎲 بازی جرعت حقیقت",
                                     callback_data=f"game_menu_{session_id}"),
                InlineKeyboardButton(
                    "🚪 خروج از چت", callback_data=f"exit_chat_{session_id}")
            )
            bot.send_message(uid, "✅ *شما به یک کاربر متصل شدید!*\n\nبرای مشاهده گزینه‌های چت از دکمه‌های زیر استفاده کنید:",
                             reply_markup=chat_markup, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "پارتنر پیدا شد! چت شروع شد.")
    else:
        queue_markup = InlineKeyboardMarkup()
        queue_markup.add(InlineKeyboardButton(
            "🚪 خروج از صف انتظار", callback_data=f"exit_queue_with_boy"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text="⏳ *در صف انتظار قرار گرفتید*\n\nبه محض پیدا شدن پسر مناسب به شما اطلاع داده می‌شود.\n\nبرای خروج از صف روی دکمه زیر کلیک کنید:", reply_markup=queue_markup, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "به صف انتظار اضافه شدید!")


@bot.callback_query_handler(func=lambda call: call.data == "dummy_same_age_chat")
def start_same_age_chat(call: CallbackQuery):
    user_id = call.from_user.id
    active_session = get_active_session(user_id)
    if active_session:
        bot.answer_callback_query(
            call.id, "شما در حال حاضر در یک چت ناشناس هستید! ابتدا چت فعلی را پایان دهید.", show_alert=True)
        return
    user_info = get_user_info(user_id)
    if not user_info:
        bot.answer_callback_query(
            call.id, "خطا در دریافت اطلاعات کاربر!", show_alert=True)
        return
    if user_info["connection_status"] != "single":
        bot.answer_callback_query(
            call.id, "شما در حالت جفت هستید و نمی‌توانید چت ناشناس شروع کنید!", show_alert=True)
        return
    if user_id in WAITING_QUEUE["same_age"]:
        bot.answer_callback_query(
            call.id, "شما قبلاً در صف انتظار هستید!", show_alert=True)
        return

    WAITING_QUEUE["same_age"].append(user_id)
    match_id = find_match(user_id, "same_age")

    if match_id:
        session_id = create_chat_session(user_id, match_id, "same_age")
        ACTIVE_CHATS[session_id] = [user_id, match_id]
        CHAT_PARTNERS[user_id] = session_id
        CHAT_PARTNERS[match_id] = session_id
        for uid in [user_id, match_id]:
            chat_markup = InlineKeyboardMarkup(row_width=1)
            chat_markup.add(
                InlineKeyboardButton(
                    "👤 مشاهده پروفایل", callback_data=f"view_profile_{session_id}"),
                InlineKeyboardButton("🎲 بازی جرعت حقیقت",
                                     callback_data=f"game_menu_{session_id}"),
                InlineKeyboardButton(
                    "🚪 خروج از چت", callback_data=f"exit_chat_{session_id}")
            )
            bot.send_message(uid, "✅ *شما به یک کاربر همسن متصل شدید!*\n\nبرای مشاهده گزینه‌های چت از دکمه‌های زیر استفاده کنید:",
                             reply_markup=chat_markup, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "پارتنر همسن پیدا شد! چت شروع شد.")
    else:
        queue_markup = InlineKeyboardMarkup()
        queue_markup.add(InlineKeyboardButton(
            "🚪 خروج از صف انتظار", callback_data=f"exit_queue_same_age"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text="⏳ *در صف انتظار قرار گرفتید*\n\nبه محض پیدا شدن کاربر همسن به شما اطلاع داده می‌شود.\n\nبرای خروج از صف روی دکمه زیر کلیک کنید:", reply_markup=queue_markup, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "به صف انتظار اضافه شدید!")


@bot.callback_query_handler(func=lambda call: call.data.startswith("exit_queue_"))
def exit_from_queue(call: CallbackQuery):
    user_id = call.from_user.id
    queue_type = call.data.split("_")[2]
    if queue_type == "random" and user_id in WAITING_QUEUE["random"]:
        WAITING_QUEUE["random"].remove(user_id)
    elif queue_type == "with_girl" and user_id in WAITING_QUEUE["with_girl"]:
        WAITING_QUEUE["with_girl"].remove(user_id)
    elif queue_type == "with_boy" and user_id in WAITING_QUEUE["with_boy"]:
        WAITING_QUEUE["with_boy"].remove(user_id)
    elif queue_type == "same_age" and user_id in WAITING_QUEUE["same_age"]:
        WAITING_QUEUE["same_age"].remove(user_id)
    else:
        bot.answer_callback_query(
            call.id, "شما در صف انتظار نیستید!", show_alert=True)
        return
    try:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text="✅ *شما از صف انتظار خارج شدید*", parse_mode="Markdown")
    except:
        pass
    bot.answer_callback_query(call.id, "با موفقیت از صف خارج شدید!")


@bot.callback_query_handler(func=lambda call: call.data.startswith("view_profile_"))
def handle_view_profile(call: CallbackQuery):
    user_id = call.from_user.id
    session_id = call.data.split("_")[2]
    if session_id not in ACTIVE_CHATS:
        bot.answer_callback_query(call.id, "این چت به پایان رسیده است!", show_alert=True)
        return
    if user_id not in ACTIVE_CHATS[session_id]:
        bot.answer_callback_query(call.id, "شما عضو این چت نیستید!", show_alert=True)
        return
    other_user_id = ACTIVE_CHATS[session_id][0] if ACTIVE_CHATS[session_id][1] == user_id else ACTIVE_CHATS[session_id][1]
    other_user_info = get_user_info(other_user_id)
    if not other_user_info:
        bot.answer_callback_query(call.id, "خطا در دریافت اطلاعات کاربر!", show_alert=True)
        return
    partner_status = "دارد" if other_user_info["partner_name"] else "ندارد"
    age_text = f"{other_user_info['age']} سال" if other_user_info['age'] else "نامشخص"
    profile_text = f"""👤 *پروفایل کاربر*
📛 *نام:* {other_user_info['name']}
🎂 *سن:* {age_text}
🌍 *ریجن:* {other_user_info['region']}
💑 *وضعیت پارتنر:* {partner_status}"""
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, profile_text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("exit_chat_"))
def exit_from_chat(call: CallbackQuery):
    user_id = call.from_user.id
    session_id = call.data.split("_")[2]
    if session_id not in ACTIVE_CHATS:
        bot.answer_callback_query(call.id, "این چت قبلاً پایان یافته است!")
        return
    if user_id not in ACTIVE_CHATS[session_id]:
        bot.answer_callback_query(call.id, "شما عضو این چت نیستید!")
        return
    other_user_id = ACTIVE_CHATS[session_id][0] if ACTIVE_CHATS[session_id][1] == user_id else ACTIVE_CHATS[session_id][1]
    if user_id in CHAT_PARTNERS:
        del CHAT_PARTNERS[user_id]
    if other_user_id in CHAT_PARTNERS:
        del CHAT_PARTNERS[other_user_id]
    del ACTIVE_CHATS[session_id]
    bot.send_message(other_user_id, "⚠️ *کاربر مقابل چت را ترک کرد*", parse_mode="Markdown")
    try:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="✅ *شما از چت خارج شدید*", parse_mode="Markdown")
    except:
        pass
    bot.answer_callback_query(call.id, "با موفقیت از چت خارج شدید!")

@bot.message_handler(commands=['cl'])
def handle_cancel_queue_or_chat(message: Message):
    user_id = message.from_user.id
    active_session = get_active_session(user_id)
    if active_session and active_session in ACTIVE_CHATS:
        other_user_id = ACTIVE_CHATS[active_session][0] if ACTIVE_CHATS[active_session][1] == user_id else ACTIVE_CHATS[active_session][1]
        if user_id in CHAT_PARTNERS:
            del CHAT_PARTNERS[user_id]
        if other_user_id in CHAT_PARTNERS:
            del CHAT_PARTNERS[other_user_id]
        del ACTIVE_CHATS[active_session]
        bot.send_message(other_user_id, "⚠️ *کاربر مقابل چت را ترک کرد*", parse_mode="Markdown")
        bot.reply_to(message, "✅ شما از چت ناشناس خارج شدید!")
        return
    removed = False
    for queue_type in ["random", "with_girl", "with_boy", "same_age"]:
        if user_id in WAITING_QUEUE[queue_type]:
            WAITING_QUEUE[queue_type].remove(user_id)
            removed = True
            break
    if removed:
        bot.reply_to(message, "✅ شما از صف انتظار خارج شدید!")
    else:
        bot.reply_to(message, "⚠️ شما در هیچ صف انتظار یا چتی نیستید!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("end_chat_confirm_"))
def handle_end_chat_confirm(call: CallbackQuery):
    session_id = call.data.split("_")[3]
    if session_id not in ACTIVE_CHATS:
        bot.answer_callback_query(call.id, "چت قبلاً پایان یافته است!")
        return
    users = ACTIVE_CHATS[session_id][:]
    for user_id in users:
        markup = InlineKeyboardMarkup(row_width=1)
        match_button = InlineKeyboardButton("🔍 مچ شدن", callback_data=f"match_request_{user_id}_{session_id}")
        markup.add(match_button)
        bot.send_message(user_id, "✅ *چت ناشناس پایان یافت*\n\nاگر می‌خواهید با این کاربر مچ شوید روی دکمه زیر کلیک کنید:", reply_markup=markup, parse_mode="Markdown")
    if session_id in ACTIVE_CHATS:
        del ACTIVE_CHATS[session_id]
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("end_chat_cancel_"))
def handle_end_chat_cancel(call: CallbackQuery):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "چت ادامه یافت!")

@bot.message_handler(func=lambda message: True)
def handle_chat_messages(message: Message):
    user_id = message.from_user.id
    if message.text and message.text.startswith("/"):
        return
    active_session = get_active_session(user_id)
    if not active_session or active_session not in ACTIVE_CHATS:
        return
    if message.text and message.text.lower() in ["!جرعت", "!جرئت", "!جریت", "!جرات"]:
        send_question_to_chat(active_session, "dare")
        return
    elif message.text and message.text.lower() in ["!حقیقت", "!هقیقت", "!هغیغت", "!حغیغت"]:
        send_question_to_chat(active_session, "truth")
        return
    elif message.text == "!پایان":
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(InlineKeyboardButton("✅ بله", callback_data=f"end_chat_confirm_{active_session}"), InlineKeyboardButton("❌ خیر", callback_data=f"end_chat_cancel_{active_session}"))
        bot.reply_to(message, "آیا مطمئن هستید که می‌خواهید چت را پایان دهید؟", reply_markup=markup)
        return
    session_users = ACTIVE_CHATS[active_session]
    other_user_id = session_users[0] if session_users[1] == user_id else session_users[1]
    if message.reply_to_message and message.reply_to_message.from_user.id == user_id and message.text in ["/del", "!حذف"]:
        original_msg_id = message.reply_to_message.message_id
        json_file = f"anonymous_chats/{active_session}/chat_data.json"
        if os.path.exists(json_file):
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["messages"] = [m for m in data["messages"] if m.get("message_id") != original_msg_id]
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            bot.reply_to(message, "✅ پیام مورد نظر با موفقیت حذف شد!")
            bot.send_message(other_user_id, "🗑️ *یک پیام توسط کاربر مقابل حذف شد*", parse_mode="Markdown")
        return
    message_data = {
        "message_id": message.message_id,
        "sender_id": user_id,
        "timestamp": datetime.now().isoformat(),
        "text": message.text if message.text else None,
        "reply_to": message.reply_to_message.message_id if message.reply_to_message else None,
        "caption": None,
        "file": None
    }
    if message.content_type == "text":
        save_message_to_session(active_session, message_data)
        if message.reply_to_message:
            json_file = f"anonymous_chats/{active_session}/chat_data.json"
            original_text = None
            if os.path.exists(json_file):
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for msg in data["messages"]:
                    if msg.get("message_id") == message.reply_to_message.message_id:
                        original_text = msg.get("text")
                        break
            if original_text:
                bot.send_message(other_user_id, f"📎 *ریپلای به:*\n{original_text}\n\n{message.text}", parse_mode="Markdown")
            else:
                bot.send_message(other_user_id, message.text)
        else:
            bot.send_message(other_user_id, message.text)
    elif message.content_type == "photo":
        caption = message.caption if message.caption else None
        message_data["caption"] = caption
        file_info = message.photo[-1]
        file_info = bot.get_file(file_info.file_id)
        file_path = f"temp_{user_id}_{message.message_id}.jpg"
        downloaded_file = bot.download_file(file_info.file_path)
        with open(file_path, "wb") as f:
            f.write(downloaded_file)
        saved_path = save_file_to_session(active_session, file_path, "photo")
        message_data["file"] = saved_path
        save_message_to_session(active_session, message_data)
        if message.reply_to_message:
            json_file = f"anonymous_chats/{active_session}/chat_data.json"
            original_text = None
            if os.path.exists(json_file):
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for msg in data["messages"]:
                    if msg.get("message_id") == message.reply_to_message.message_id:
                        original_text = msg.get("text")
                        break
            if original_text:
                bot.send_message(other_user_id, f"📎 *ریپلای به:*\n{original_text}", parse_mode="Markdown")
        if caption:
            bot.send_photo(other_user_id, open(file_path, "rb"), caption=caption)
        else:
            bot.send_photo(other_user_id, open(file_path, "rb"))
        os.remove(file_path)
    elif message.content_type == "video":
        caption = message.caption if message.caption else None
        message_data["caption"] = caption
        file_info = message.video
        file_info = bot.get_file(file_info.file_id)
        file_path = f"temp_{user_id}_{message.message_id}.mp4"
        downloaded_file = bot.download_file(file_info.file_path)
        with open(file_path, "wb") as f:
            f.write(downloaded_file)
        saved_path = save_file_to_session(active_session, file_path, "video")
        message_data["file"] = saved_path
        save_message_to_session(active_session, message_data)
        if message.reply_to_message:
            json_file = f"anonymous_chats/{active_session}/chat_data.json"
            original_text = None
            if os.path.exists(json_file):
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for msg in data["messages"]:
                    if msg.get("message_id") == message.reply_to_message.message_id:
                        original_text = msg.get("text")
                        break
            if original_text:
                bot.send_message(other_user_id, f"📎 *ریپلای به:*\n{original_text}", parse_mode="Markdown")
        if caption:
            bot.send_video(other_user_id, open(file_path, "rb"), caption=caption)
        else:
            bot.send_video(other_user_id, open(file_path, "rb"))
        os.remove(file_path)
    elif message.content_type == "document":
        caption = message.caption if message.caption else None
        message_data["caption"] = caption
        file_info = message.document
        file_info = bot.get_file(file_info.file_id)
        file_path = f"temp_{user_id}_{message.message_id}_{file_info.file_path.split('/')[-1]}"
        downloaded_file = bot.download_file(file_info.file_path)
        with open(file_path, "wb") as f:
            f.write(downloaded_file)
        saved_path = save_file_to_session(active_session, file_path, "document")
        message_data["file"] = saved_path
        save_message_to_session(active_session, message_data)
        if message.reply_to_message:
            json_file = f"anonymous_chats/{active_session}/chat_data.json"
            original_text = None
            if os.path.exists(json_file):
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for msg in data["messages"]:
                    if msg.get("message_id") == message.reply_to_message.message_id:
                        original_text = msg.get("text")
                        break
            if original_text:
                bot.send_message(other_user_id, f"📎 *ریپلای به:*\n{original_text}", parse_mode="Markdown")
        if caption:
            bot.send_document(other_user_id, open(file_path, "rb"), caption=caption)
        else:
            bot.send_document(other_user_id, open(file_path, "rb"))
        os.remove(file_path)
    elif message.content_type == "voice":
        message_data["caption"] = None
        file_info = message.voice
        file_info = bot.get_file(file_info.file_id)
        file_path = f"temp_{user_id}_{message.message_id}.ogg"
        downloaded_file = bot.download_file(file_info.file_path)
        with open(file_path, "wb") as f:
            f.write(downloaded_file)
        saved_path = save_file_to_session(active_session, file_path, "voice")
        message_data["file"] = saved_path
        save_message_to_session(active_session, message_data)
        if message.reply_to_message:
            json_file = f"anonymous_chats/{active_session}/chat_data.json"
            original_text = None
            if os.path.exists(json_file):
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for msg in data["messages"]:
                    if msg.get("message_id") == message.reply_to_message.message_id:
                        original_text = msg.get("text")
                        break
            if original_text:
                bot.send_message(other_user_id, f"📎 *ریپلای به:*\n{original_text}", parse_mode="Markdown")
        bot.send_voice(other_user_id, open(file_path, "rb"))
        os.remove(file_path)
    elif message.content_type == "contact":
        message_data["text"] = f"contact: {message.contact.first_name} {message.contact.last_name if message.contact.last_name else ''} - {message.contact.phone_number}"
        save_message_to_session(active_session, message_data)
        if message.reply_to_message:
            json_file = f"anonymous_chats/{active_session}/chat_data.json"
            original_text = None
            if os.path.exists(json_file):
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for msg in data["messages"]:
                    if msg.get("message_id") == message.reply_to_message.message_id:
                        original_text = msg.get("text")
                        break
            if original_text:
                bot.send_message(other_user_id, f"📎 *ریپلای به:*\n{original_text}", parse_mode="Markdown")
        bot.send_contact(other_user_id, message.contact.phone_number, message.contact.first_name, last_name=message.contact.last_name if message.contact.last_name else "")







def get_active_session(user_id):
    return CHAT_PARTNERS.get(user_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("end_chat_confirm_"))
def handle_end_chat_confirm(call: CallbackQuery):
    session_id = call.data.split("_")[3]

    if session_id not in ACTIVE_CHATS:
        bot.answer_callback_query(call.id, "چت قبلاً پایان یافته است!")
        return

    users = ACTIVE_CHATS[session_id][:]

    for user_id in users:
        markup = InlineKeyboardMarkup(row_width=1)
        match_button = InlineKeyboardButton(
            "🔍 مچ شدن", callback_data=f"match_request_{user_id}_{session_id}")
        markup.add(match_button)

        bot.send_message(
            user_id,
            "✅ *چت ناشناس پایان یافت*\n\nاگر می‌خواهید با این کاربر مچ شوید روی دکمه زیر کلیک کنید:",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    if session_id in ACTIVE_CHATS:
        del ACTIVE_CHATS[session_id]

    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("end_chat_cancel_"))
def handle_end_chat_cancel(call: CallbackQuery):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "چت ادامه یافت!")


@bot.callback_query_handler(func=lambda call: call.data.startswith("match_request_"))
def handle_match_request(call: CallbackQuery):
    parts = call.data.split("_")
    requester_id = int(parts[2])
    session_id = parts[3]

    json_file = f"anonymous_chats/{session_id}/chat_data.json"
    if not os.path.exists(json_file):
        bot.answer_callback_query(call.id, "چت یافت نشد!")
        return

    with open(json_file, "r", encoding="utf-8") as f:
        chat_data = json.load(f)

    other_user_id = chat_data["user1_id"] if chat_data["user2_id"] == requester_id else chat_data["user2_id"]

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(
            "✅ قبول", callback_data=f"match_accept_{requester_id}_{other_user_id}_{session_id}"),
        InlineKeyboardButton(
            "❌ رد", callback_data=f"match_reject_{requester_id}_{other_user_id}_{session_id}")
    )

    bot.send_message(
        other_user_id,
        f"👤 کاربری با آیدی {requester_id} درخواست مچ شدن با شما را دارد. آیا موافقید؟",
        reply_markup=markup
    )

    bot.answer_callback_query(call.id, "درخواست مچ شدن ارسال شد!")


@bot.callback_query_handler(func=lambda call: call.data.startswith("match_accept_"))
def handle_match_accept(call: CallbackQuery):
    parts = call.data.split("_")
    requester_id = int(parts[2])
    accepter_id = int(parts[3])
    session_id = parts[4]

    conn = get_db_connection()
    conn.execute("UPDATE users SET connection_status = 'coupled', partner_id = ? WHERE user_id = ?",
                 (requester_id, accepter_id))
    conn.execute("UPDATE users SET connection_status = 'coupled', partner_id = ? WHERE user_id = ?",
                 (accepter_id, requester_id))
    conn.commit()
    conn.close()

    bot.send_message(
        requester_id, f"✅ درخواست مچ شدن شما توسط کاربر {accepter_id} پذیرفته شد!")
    bot.send_message(accepter_id, "✅ شما با درخواست مچ شدن موافقت کردید!")

    bot.answer_callback_query(call.id, "مچ شدن با موفقیت انجام شد!")


@bot.callback_query_handler(func=lambda call: call.data.startswith("match_reject_"))
def handle_match_reject(call: CallbackQuery):
    parts = call.data.split("_")
    requester_id = int(parts[2])
    accepter_id = int(parts[3])

    bot.send_message(
        requester_id, f"❌ درخواست مچ شدن شما توسط کاربر {accepter_id} رد شد!")
    bot.answer_callback_query(call.id, "درخواست مچ شدن رد شد!")


############### -- SEC CHAT -- ###############
############### -- SEC CHAT -- ###############
############### -- SEC CHAT -- ###############
############### -- SEC CHAT -- ###############
############### -- SEC CHAT -- ###############
############### -- SEC CHAT -- ###############
############### -- SEC CHAT -- ###############
############### -- SEC CHAT -- ###############
############### -- SEC CHAT -- ###############
############### -- SEC CHAT -- ###############

def main_menu():
    """منوی اصلی بات - با اضافه شدن کتاب‌نویسی"""
    markup = InlineKeyboardMarkup()

    # ردیف 1: دو دکمه - قلب رابطه
    markup.row(
        InlineKeyboardButton("💑 اطلاعات رابطه", callback_data="show_info"),
        InlineKeyboardButton("📅 مناسبت‌های من", callback_data="my_events")
    )

    # ردیف 2: یک دکمه - ارتباط مخفی
    markup.row(InlineKeyboardButton(
        "💌 پیام‌های مخفی", callback_data="secret_msgs_menu"),
        InlineKeyboardButton("💬 چت ناشناس", callback_data="sec_chat"))

    # ردیف 3: دو دکمه - عشق و احساسات
    markup.row(
        InlineKeyboardButton("💖 لاس سنگین", callback_data="flirt"),
        InlineKeyboardButton("💡 پیشنهادات", callback_data="suggestions")
    )

    # ردیف 4: دو دکمه - خلاقیت و مدیریت
    markup.row(
        InlineKeyboardButton("📚 کتاب‌نویسی", callback_data="books_menu"),
        InlineKeyboardButton(
            "🎁 پیام‌های ویژه", callback_data="special_messages"),
        InlineKeyboardButton("🌙 حالت خلقی", callback_data="mood_tracker")
    )

    # ردیف 5: مدیریت
    markup.row(InlineKeyboardButton(
        "✏️ ویرایش اطلاعات", callback_data="edit_profile"))

    return markup


def save_reply_mapping(sender, receiver, chat_id, sender_msg_id, receiver_msg_id):
    chat_id = str(chat_id)

    if chat_id not in reply_map:
        reply_map[chat_id] = {}

    if receiver not in reply_map[chat_id]:
        reply_map[chat_id][receiver] = {}

    reply_map[chat_id][receiver][sender_msg_id] = receiver_msg_id


def get_partner_reply_message_id(receiver, chat_id, original_msg_id):
    chat_id = str(chat_id)

    if chat_id not in reply_map:
        return None

    if receiver not in reply_map[chat_id]:
        return None

    return reply_map[chat_id][receiver].get(original_msg_id)


def parse_date_input(text: str):
    """تبدیل متن تاریخ به میلادی و شمسی"""
    text = text.strip()
    try:
        if "/" in text:  # فرمت شمسی
            parts = re.split(r"[\/\s\-]+", text)
            if len(parts) != 3:
                raise ValueError("فرمت تاریخ نامعتبر")
            y, m, d = map(int, parts)
            jd = jdatetime.date(y, m, d)
            return jd.togregorian(), jd
        else:  # فرمت میلادی
            g = datetime.strptime(text, "%Y-%m-%d").date()
            return g, jdatetime.date.fromgregorian(date=g)
    except Exception as e:
        raise ValueError(f"خطا در پردازش تاریخ: {str(e)}")


def calc_age_and_days(birthdate: date):
    """محاسبه سن و روزهای گذشته از تولد"""
    today = date.today()
    age = today.year - birthdate.year - \
        ((today.month, today.day) < (birthdate.month, birthdate.day))
    days_passed = (today - birthdate).days
    return age, days_passed


def get_relation_days(start_date: date):
    """محاسبه روزهای گذشته از شروع رابطه"""
    today = date.today()
    days_passed = (today - start_date).days
    return days_passed


def safe_execute_db(query, params=(), db_type="users"):
    """اجرای ایمن کوئری‌های دیتابیس"""
    try:
        if db_type == "users":
            cur = conn_users.cursor()
            cur.execute(query, params)
            result = cur.fetchall()
            conn_users.commit()
            cur.close()
        else:
            cur = conn_notifications.cursor()
            cur.execute(query, params)
            result = cur.fetchall()
            conn_notifications.commit()
            cur.close()
        return result
    except Exception as e:
        print(f"خطای دیتابیس: {e}")
        return None


@bot.message_handler(commands=['start', 'restart'])
def start_handler(message):
    """Handler شروع بات"""
    uid = message.chat.id

    result = safe_execute_db("SELECT * FROM users WHERE user_id = ?", (uid,))

    if result:
        default_events = safe_execute_db("""
            SELECT COUNT(*) FROM notifications 
            WHERE user_id = ? AND (title LIKE '%تولد%' OR title LIKE '%گرد رابطه%')
        """, (uid,), "notifications")

        if not default_events or default_events[0][0] == 0:
            create_default_events(uid)

        bot.send_message(uid, "👋 خوش اومدی دوباره! آماده‌ای برای کمی عشق و شیطنت؟ 💕",
                         reply_markup=main_menu())
        return

    user_state[uid] = "gender"
    temp_data[uid] = {}

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("مرد 😎", callback_data="gender_مرد"),
               InlineKeyboardButton("زن 😏", callback_data="gender_زن"))
    bot.send_message(uid, "به ربات رابطه‌یاب خوش اومدی! 💖\n\nاول یه چیز مهم، جنسیتت چیه؟ 😊",
                     reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("gender_"))
def gender_handler(call):
    """Handler انتخاب جنسیت"""
    uid = call.message.chat.id
    if user_state.get(uid) != "gender":
        bot.answer_callback_query(call.id, "❌ وضعیت نامعتبر")
        return

    gender = call.data.split("_")[1]
    temp_data[uid]["gender"] = gender

    if gender == "مرد":
        response = "😎 آها، مرد اومد وسط! بوی خودشیفتگی و غرور قاطی عطر عشق پیچید 😏"
    elif gender == "زن":
        response = "😍 وای یه داف احساسی وارد شد! حتما قراره یکیو تا لب مرز دیوونگی ببره 😂"
    else:
        response = "💫 vibe خاص داری، انگار خودِ عشق قراره ازت گزارش کار بگیره 😌"

    user_state[uid] = "name"

    bot.edit_message_text(f"{response}\n\n💬 حالا اسمت رو برام بنویس:",
                          uid, call.message.message_id)


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "name")
def name_handler(message):
    """Handler دریافت نام"""
    uid = message.chat.id
    name = message.text.strip()

    if len(name) < 2:
        bot.send_message(uid, "❌ اسم باید حداقل ۲ حرف داشته باشه!")
        return

    temp_data[uid]["name"] = name

    name_length = len(name)
    if name_length <= 3:
        joke = "😏 اسم سه‌حرفی؟ همون‌قدری که کوتاهه، قشنگ می‌چسبه 😍"
    elif name_length <= 6:
        joke = "😎 اسمت اندازه‌ست؛ نه زیادی بچه‌مثبتی، نه زیادی مرموز 😏"
    else:
        joke = "😂 تا آخر گفتنش پارتنرت عاشق‌تر می‌شه، نفس بگیره وسطش 😅"

    if name.startswith('آ'):
        joke += "\n💫 از همون اول معلوم بود خاصی، آ اول اسمت فریاد داره 😌"
    elif name.endswith('ی'):
        joke += "\n😏 اون «ی» آخرش یه ناز خاص داره که بوی دلبری می‌ده 😍"

    user_state[uid] = "birthdate"

    bot.send_message(
        uid, f"✅ {joke}\n\n📅 حالا تاریخ تولدت رو به یکی از فرمت‌های زیر وارد کن:\n• ۱۳۸۰-۰۱-۰۱ (شمسی)\n• 2001-03-21 (میلادی)")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "birthdate")
def birthdate_handler(message):
    """Handler دریافت تاریخ تولد"""
    uid = message.chat.id

    try:
        gdate, jdate = parse_date_input(message.text)
        age, days_passed = calc_age_and_days(gdate)

        if age < 10 or age > 100:
            bot.send_message(
                uid, "❌ سن نامعتبر! لطفا تاریخ تولد واقعی وارد کن")
            return

        temp_data[uid]["birthdate"] = gdate.isoformat()
        temp_data[uid]["age"] = age

        if age < 13:
            age_joke = "😂 بچه عشقی؟ هنوز عشق واسه‌ت یعنی استیکر قلب 😭"
        elif age <= 16:
            age_joke = "😏 فازای 'قهر بعد ۱۰ دقیقه آشتی' داری نه؟ classic 😎"
        elif age <= 21:
            age_joke = "🔥 اووه این سن خطرناکه! هم می‌سوزونی هم می‌سوزی 😌"
        elif age <= 30:
            age_joke = "😌 بالغی ولی هنوز اون تهِ دلت یه بچه شیطون عشق‌باز هست 😏"
        else:
            age_joke = "😂 تجربه‌داری، یعنی دیگه با یه ناز ساده ذوب نمی‌شی … یا می‌شی؟ 😜"

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("💖 وارد کردن نام پارتنر",
                                 callback_data="has_partner"),
            InlineKeyboardButton("😅 پارتنر ندارم", callback_data="no_partner")
        )

        bot.send_message(uid,
                         f"✅ اطلاعات تولد ثبت شد! 🎂\n\n"
                         f"📅 میلادی: {gdate}\n"
                         f"📅 شمسی: {jdate.year}/{jdate.month:02d}/{jdate.day:02d}\n"
                         f"👤 سن: {age} سال\n"
                         f"{age_joke}\n\n"
                         f"💖 حالا اسم پارتنرت رو بنویس یا اگه نداریش بگو:",
                         reply_markup=markup)

        user_state[uid] = "partner_choice"

    except ValueError as e:
        bot.send_message(
            uid, f"❌ خطا در تاریخ: {str(e)}\n\nلطفا دوباره وارد کن:")


@bot.callback_query_handler(func=lambda call: call.data in ["has_partner", "no_partner"])
def partner_choice_handler(call):
    """Handler انتخاب وضعیت پارتنر"""
    uid = call.message.chat.id
    if user_state.get(uid) != "partner_choice":
        bot.answer_callback_query(call.id, "❌ وضعیت نامعتبر")
        return

    if call.data == "no_partner":
        temp_data[uid]["partner_name"] = "ندارم"
        temp_data[uid]["partner_birthdate"] = None
        temp_data[uid]["partner_age"] = None
        temp_data[uid]["partner_nick"] = "ندارم"
        temp_data[uid]["relation_type"] = "تکی"
        temp_data[uid]["start_date"] = datetime.now().date().isoformat()

        # ذخیره اطلاعات در دیتابیس
        data = temp_data[uid]
        query = """
        INSERT OR REPLACE INTO users 
        (user_id, gender, name, birthdate, partner_name, partner_birthdate, partner_age, partner_nick, relation_type, start_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        result = safe_execute_db(query, (
            uid, data["gender"], data["name"], data["birthdate"],
            data["partner_name"], data["partner_birthdate"], data["partner_age"],
            data["partner_nick"], data["relation_type"], data["start_date"]
        ))

        if result is None:
            bot.send_message(
                uid, "❌ خطا در ذخیره اطلاعات! لطفا دوباره تلاش کن /start")
            return

        # ایجاد مناسبت‌های پیش‌فرض فقط برای کاربر
        create_default_events_single(uid)

        # پاکسازی state
        user_state.pop(uid, None)
        temp_data.pop(uid, None)

        bot.edit_message_text(
            "😅 فدای سرت! خودمون یه پارتنر خفن برات پیدا می‌کنیم!\n\n"
            "😂 نگران نباش، تا اون موقع می‌تونی از همه قابلیت‌های ربات استفاده کنی!\n\n"
            "🎉 ثبت نامت تموم شد! بریم تو کار...",
            uid, call.message.message_id,
            reply_markup=main_menu()
        )
    else:
        bot.edit_message_text(
            "💖 اسم پارتنرت رو بنویس:",
            uid, call.message.message_id
        )
        user_state[uid] = "partner_name"


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "partner_name")
def partner_name_handler(message):
    """Handler دریافت نام پارتنر"""
    uid = message.chat.id
    partner_name = message.text.strip()

    if len(partner_name) < 2:
        bot.send_message(uid, "❌ اسم پارتنر باید حداقل ۲ حرف داشته باشه!")
        return

    temp_data[uid]["partner_name"] = partner_name

    name_length = len(partner_name)
    if name_length <= 3:
        name_joke = "😍 اسم ناز داره، معلومه هر بار می‌گی دل نرم می‌شه 😌"
    elif name_length <= 6:
        name_joke = "😎 اسمش اندازه‌ست، نه زیادی ساده نه زیادی پیچیده"
    else:
        name_joke = "😅 تا بگی تمومش، یا قهر کرده یا عاشق‌تر شده 😏"

    if partner_name == temp_data[uid]["name"]:
        name_joke = "😳 یعنی هر وقت صداش می‌زنی خودت برمی‌گردی؟ bug عشقی 😂"
    elif any(char in partner_name for char in "آابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی"):
        name_joke = "😎 اسم خاص = دل خاص = دردسر خاص 😜"

    user_state[uid] = "partner_birthdate"

    bot.send_message(
        uid, f"✅ {name_joke}\n\n📅 حالا تاریخ تولد {partner_name} رو وارد کن:")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "partner_birthdate")
def partner_birthdate_handler(message):
    """Handler دریافت تاریخ تولد پارتنر"""
    uid = message.chat.id

    try:
        gdate, jdate = parse_date_input(message.text)
        age, days_passed = calc_age_and_days(gdate)

        if age < 10 or age > 100:
            bot.send_message(
                uid, "❌ سن نامعتبر! لطفا تاریخ تولد واقعی وارد کن")
            return

        temp_data[uid]["partner_birthdate"] = gdate.isoformat()
        temp_data[uid]["partner_age"] = age

        user_age = temp_data[uid]["age"]
        age_diff = user_age - age

        if age_diff == 0:
            age_joke = "❤️ وای، دوقلوای عشقی! با یه نگاه همو می‌فهمین 😍"
        elif 1 <= age_diff <= 3:
            age_joke = "😏 خوش به حالت، پارتنرت تجربه داره، ولی مواظب باش زیاد قلدری نکنه 😂"
        elif -3 <= age_diff <= -1:
            age_joke = "😌 کوچولوشه؟ پس حتما هر روز قربون‌صدقه می‌ری 😍"
        elif 10 <= age_diff <= 15:
            age_joke = "😏 شوگری طور؟ فقط نگو دسرم خرجِ دله 😜"
        elif -15 <= age_diff <= -10:
            age_joke = "😳 شوگرته؟ وای داری با زندگی دیالوگ می‌زنی 😅"
        else:
            age_joke = "😌 سن فرق داره ولی دلا که یکیه، مگه نه؟ 😉"

        bot.send_message(uid,
                         f"✅ تولد پارتنرت ثبت شد! 💕\n\n"
                         f"📅 میلادی: {gdate}\n"
                         f"📅 شمسی: {jdate.year}/{jdate.month:02d}/{jdate.day:02d}\n"
                         f"👤 سن: {age} سال\n"
                         f"{age_joke}\n\n"
                         f"😏 حالا یه لقب شوخی و دوستانه برایش انتخاب کن:")

        user_state[uid] = "partner_nick"

    except ValueError as e:
        bot.send_message(
            uid, f"❌ خطا در تاریخ: {str(e)}\n\nلطفا دوباره وارد کن:")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "partner_nick")
def partner_nick_handler(message):
    """Handler دریافت لقب پارتنر"""
    uid = message.chat.id
    partner_nick = message.text.strip()

    if len(partner_nick) < 2:
        bot.send_message(uid, "❌ لقب باید حداقل ۲ حرف داشته باشه!")
        return

    temp_data[uid]["partner_nick"] = partner_nick

    nick_joke = ""
    if any(word in partner_nick for word in ["عشق", "دل", "جون"]):
        nick_joke = "😍 خزِ دوست‌داشتنی! همه می‌گن تکراریه ولی هنوز جواب می‌ده 😂"
    elif any(word in partner_nick for word in ["خر", "میمون"]):
        nick_joke = "😂 یعنی رابطه‌تون پر از خنده‌ست، همینه که شیرینه 😁"
    elif any(word in partner_nick for word in ["ملکه", "پادشاه", "شاه"]):
        nick_joke = "👑 سلطنتی ترین عشق جهان، فقط حواست باشه کودتا نشه 😏"
    elif "دیوونه" in partner_nick:
        nick_joke = "😅 دعواتونم بامزه‌ست نه؟ تهش یکی می‌گه 'ولی من هنوز دوستت دارم' 💕"
    else:
        nick_joke = "😍 ترکیب اسما؟ یعنی دیگه رسماً برند عشق شدین 😌"

    user_state[uid] = "relation_type"

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("لانگ دیستنس 🌍", callback_data="rtype_لانگ"),
               InlineKeyboardButton("حضوری 💑", callback_data="rtype_حضوری"))
    markup.row(InlineKeyboardButton("مجازی 💻", callback_data="rtype_مجازی"),
               bot.send_message(uid, f"✅ {nick_joke}\n\n💑 نوع رابطه‌تون چیه؟",
                                reply_markup=markup))


@bot.callback_query_handler(func=lambda call: call.data.startswith("rtype_"))
def relation_type_handler(call):
    """Handler انتخاب نوع رابطه"""
    uid = call.message.chat.id
    if user_state.get(uid) != "relation_type":
        bot.answer_callback_query(call.id, "❌ وضعیت نامعتبر")
        return

    relation_type = call.data.split("_")[1]
    temp_data[uid]["relation_type"] = relation_type

    if relation_type == "مجازی":
        type_joke = "💻 عشق مجازی؟ فقط حواست باشه اینترنت قطع شه، دل نره 😭"
    elif relation_type == "حضوری":
        type_joke = "😏 حضوری؟ یعنی آغوش واقعی و قهر واقعی 😅"
    elif relation_type == "لانگ":
        type_joke = "😌 دلتنگی سخته ولی شماها از دور هم دل می‌لرزونین ❤️"

    user_state[uid] = "start_date"

    bot.edit_message_text(f"✅ {type_joke}\n\n📅 حالا تاریخ شروع رابطه‌تون رو وارد کن:",
                          uid, call.message.message_id)


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "start_date")
def start_date_handler(message):
    """Handler دریافت تاریخ شروع رابطه"""
    uid = message.chat.id

    try:
        gdate, jdate = parse_date_input(message.text)
        days_passed = get_relation_days(gdate)

        if days_passed < 0:
            bot.send_message(uid, "❌ تاریخ شروع رابطه نمی‌تونه آینده باشه!")
            return

        temp_data[uid]["start_date"] = gdate.isoformat()

        if days_passed < 7:
            duration_joke = "😏 هنوز دلش می‌ره وقتی اسم تو میاد، enjoy it 😍"
        elif days_passed <= 90:
            duration_joke = "💕 هنوز قربون‌صدقه است و هر چت یه قلب آخرش داره 😌"
        elif days_passed <= 365:
            duration_joke = "😅 نصف زمان عشقو رفتی، حالا وقت اثباته 😏"
        elif days_passed <= 1095:
            duration_joke = "💪 سه سال؟ شماها عشق ناب این نسلین 😎"
        else:
            duration_joke = "😍 عشقِ ریشه‌دار؟ دمتون گرم که هنوز برق چشاتون خاموش نشده ❤️"

        data = temp_data[uid]

        final_joke = ""
        user_age = data["age"]
        partner_age = data.get("partner_age")
        relation_type = data["relation_type"]

        if partner_age and user_age < 18 and partner_age < 18:
            final_joke = "😂 عشقِ کم‌سن ولی پر احساس، فقط قول بدین کمتر قهر کنین 😅"
        elif partner_age and abs(user_age - partner_age) > 10:
            final_joke = "😏 سن فرق داره ولی دلا که یکیه، مگه نه؟ 😉"
        elif days_passed > 1095:
            final_joke = "💪 عشقِ واقعی یعنی همین... نه بلاک، نه غیبت، فقط ادامه 😎"
        elif relation_type == "مجازی" and days_passed > 180:
            final_joke = "😌 وای، عشقِ از پشت صفحه! پایداری‌تون قابل احترامه ❤️"
        elif days_passed < 30:
            final_joke = "🎉 تازه شروع شد؟ بذار منم براتون دعا کنم این یکی بمونه 😍"

        query = """
        INSERT OR REPLACE INTO users 
        (user_id, gender, name, birthdate, partner_name, partner_birthdate, partner_age, partner_nick, relation_type, start_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        result = safe_execute_db(query, (
            uid, data["gender"], data["name"], data["birthdate"],
            data["partner_name"], data["partner_birthdate"], data["partner_age"],
            data["partner_nick"], data["relation_type"], data["start_date"]
        ))

        if result is None:
            bot.send_message(
                uid, "❌ خطا در ذخیره اطلاعات! لطفا دوباره تلاش کن /start")
            return

        create_default_events(uid)

        user_state.pop(uid, None)
        temp_data.pop(uid, None)

        completion_message = f"🎉 ثبت نام تکمیل شد! 💖\n\n{duration_joke}"
        if final_joke:
            completion_message += f"\n\n{final_joke}"

        completion_message += f"\n\n📅 شروع رابطه: {gdate}\n⏳ روزهای گذشته: {days_passed} روز\n🗓 شمسی: {jdate.year}/{jdate.month:02d}/{jdate.day:02d}"

        if data["partner_name"] != "ندارم":
            completion_message += f"\n\n✅ مناسبت‌های پیش‌فرض برات ایجاد شدن:\n• تولد خودت 🎂\n• تولد {data['partner_name']} 💕\n• سالگرد رابطه 💑"
        else:
            completion_message += f"\n\n💫 وقتی پارتنر پیدا کردی، مناسبت‌ها رو برات ایجاد می‌کنم!"

        completion_message += f"\n\nحالا می‌تونی از منوی اصلی استفاده کنی:"

        bot.send_message(uid, completion_message, reply_markup=main_menu())

    except ValueError as e:
        bot.send_message(
            uid, f"❌ خطا در تاریخ: {str(e)}\n\nلطفا دوباره وارد کن:")


def create_default_events(uid):
    """ایجاد مناسبت‌های پیش‌فرض برای کاربران با پارتنر"""
    try:
        result = safe_execute_db("""
            SELECT name, birthdate, partner_name, partner_birthdate, partner_nick, start_date 
            FROM users WHERE user_id = ?
        """, (uid,))

        if not result:
            return False

        name, birthdate, partner_name, partner_birthdate, partner_nick, start_date = result[0]

        # فقط چک کن که مناسبت‌های پیش‌فرض وجود ندارن
        existing_events = safe_execute_db("""
            SELECT COUNT(*) FROM notifications 
            WHERE user_id = ? AND title IN (?, ?, ?)
        """, (uid, f"تولد {name}", f"تولد {partner_name}", "سالگرد رابطه"), "notifications")

        if existing_events and existing_events[0][0] > 0:
            return True

        # ایجاد مناسبت تولد کاربر
        safe_execute_db("""
            INSERT INTO notifications (user_id, title, description, event_date, repeat_type, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (
            uid,
            f"تولد {name}",
            "تولد خودت! 🎂",
            birthdate,
            'yearly'
        ), "notifications")

        # ایجاد مناسبت تولد پارتنر
        safe_execute_db("""
            INSERT INTO notifications (user_id, title, description, event_date, repeat_type, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (
            uid,
            f"تولد {partner_name}",
            f"تولد {partner_nick} عزیز! 💕",
            partner_birthdate,
            'yearly'
        ), "notifications")

        # ایجاد مناسبت سالگرد رابطه
        safe_execute_db("""
            INSERT INTO notifications (user_id, title, description, event_date, repeat_type, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (
            uid,
            "سالگرد رابطه",
            "سالگرد شروع رابطه عاشقانه‌تون! 💑",
            start_date,
            'yearly'
        ), "notifications")

        print(f"✅ مناسبت‌های پیش‌فرض برای کاربر {uid} ایجاد شدند")
        return True

    except Exception as e:
        print(f"❌ خطا در ایجاد مناسبت‌های پیش‌فرض: {e}")
        return False


def create_default_events_single(uid):
    """ایجاد مناسبت‌های پیش‌فرض برای کاربران بدون پارتنر"""
    try:
        result = safe_execute_db("""
            SELECT name, birthdate
            FROM users WHERE user_id = ?
        """, (uid,))

        if not result:
            return False

        name, birthdate = result[0]

        # فقط مناسبت تولد کاربر ایجاد شود
        safe_execute_db("""
            INSERT INTO notifications (user_id, title, description, event_date, repeat_type, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (
            uid,
            f"تولد {name}",
            "تولد خودت! 🎂",
            birthdate,
            'yearly'
        ), "notifications")

        print(f"✅ مناسبت‌های پیش‌فرض برای کاربر تکی {uid} ایجاد شد")
        return True

    except Exception as e:
        print(f"❌ خطا در ایجاد مناسبت‌های پیش‌فرض تکی: {e}")
        return False


@bot.callback_query_handler(func=lambda call: call.data == "show_info")
def show_info_handler(call):
    """Handler نمایش اطلاعات - با حالت خلقی"""
    uid = call.message.chat.id

    result = safe_execute_db("""
        SELECT gender, name, birthdate, partner_name, partner_birthdate, partner_age, 
               partner_nick, relation_type, start_date, partner_id
        FROM users WHERE user_id = ?
    """, (uid,))

    if not result:
        bot.answer_callback_query(call.id, "❌ اطلاعاتی پیدا نشد!")
        return

    (gender, name, birthdate_g, partner_name, partner_birthdate_g,
     partner_age, partner_nick, relation_type, start_date_g, partner_id) = result[0]

    # تبدیل تاریخ‌ها
    birthdate_j = jdatetime.date.fromgregorian(
        date=datetime.strptime(birthdate_g, "%Y-%m-%d").date())

    # ساخت متن اصلی
    text = f"""
📋 اطلاعات رابطه‌ی شما 💕

👤 اطلاعات شما:
• نام: {name}
• جنسیت: {gender}
• تولد: {birthdate_g} / {birthdate_j.year}/{birthdate_j.month:02d}/{birthdate_j.day:02d}
"""

    # بررسی وجود پارتنر
    has_partner = partner_name and partner_name != "ندارم"

    if has_partner:
        partner_birthdate_j = jdatetime.date.fromgregorian(
            date=datetime.strptime(partner_birthdate_g, "%Y-%m-%d").date())
        start_date_j = jdatetime.date.fromgregorian(
            date=datetime.strptime(start_date_g, "%Y-%m-%d").date())

        relation_days = get_relation_days(
            datetime.strptime(start_date_g, "%Y-%m-%d").date())

        text += f"""
❤️ اطلاعات پارتنر:
• نام: {partner_name}
• تولد: {partner_birthdate_g} / {partner_birthdate_j.year}/{partner_birthdate_j.month:02d}/{partner_birthdate_j.day:02d}
• سن: {partner_age} سال
• لقب: {partner_nick}
"""

        if partner_id:
            partner_mood = get_partner_mood_display(partner_id)
            text += f"\n🌙 حالت خلقی امروز:\n{partner_mood}\n"

        text += f"""
💑 اطلاعات رابطه:
• نوع: {relation_type}
• شروع: {start_date_g} / {start_date_j.year}/{start_date_j.month:02d}/{start_date_j.day:02d}
• روزهای گذشته: {relation_days} روز 🎉
"""
    else:
        text += f"""
💔 وضعیت رابطه:
• پارتنر: ندارم
• نوع: {relation_type}
"""

    markup = InlineKeyboardMarkup()

    if has_partner:

        result_partner = safe_execute_db(
            "SELECT partner_id, connection_status FROM users WHERE user_id = ?", (uid,))

        if result_partner and result_partner[0][0] is not None:
            partner_id, connection_status = result_partner[0]

            if connection_status == "connected":
                markup.row(InlineKeyboardButton(
                    "👤 اطلاعات پارتنر", callback_data="partner_info"))
                markup.row(InlineKeyboardButton(
                    "🥀 اتمام رابطه", callback_data="end_relation"))
            elif connection_status == "pending":
                markup.row(InlineKeyboardButton(
                    "⏳ درخواست در انتظار تایید", callback_data="pending_request"))
                markup.row(InlineKeyboardButton(
                    "❌ لغو درخواست", callback_data="cancel_request"))
        else:
            markup.row(InlineKeyboardButton(
                "💞 اتصال به پارتنر", callback_data="connect_partner"))
    else:

        markup.row(InlineKeyboardButton(
            "💖 افزودن پارتنر", callback_data="add_partner"))

    markup.row(InlineKeyboardButton(
        "✏️ ویرایش اطلاعات", callback_data="edit_profile"))
    markup.row(InlineKeyboardButton(
        "🔙 منوی اصلی", callback_data="back_to_main"))

    try:
        bot.edit_message_text(text, uid, call.message.message_id,
                              reply_markup=markup, parse_mode="Markdown")
    except:
        bot.send_message(uid, text, reply_markup=markup, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: call.data == "add_partner")
def add_partner_handler(call):
    """Handler شروع فرآیند افزودن پارتنر"""
    uid = call.message.chat.id

    user_state[uid] = "add_partner_name"
    temp_data[uid] = {}

    try:
        bot.edit_message_text(
            "💖 افزودن پارتنر جدید\n\n"
            "اسم پارتنرت رو بنویس:",
            uid, call.message.message_id
        )
    except:
        bot.send_message(uid, "💖 افزودن پارتنر جدید\n\nاسم پارتنرت رو بنویس:")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "add_partner_name")
def add_partner_name_handler(message):
    """Handler دریافت نام پارتنر جدید"""
    uid = message.chat.id
    partner_name = message.text.strip()

    if len(partner_name) < 2:
        bot.send_message(uid, "❌ اسم پارتنر باید حداقل ۲ حرف داشته باشه!")
        return

    temp_data[uid]["partner_name"] = partner_name
    user_state[uid] = "add_partner_birthdate"

    bot.send_message(
        uid, f"✅ اسم '{partner_name}' ثبت شد!\n\n📅 حالا تاریخ تولدش رو وارد کن:")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "add_partner_birthdate")
def add_partner_birthdate_handler(message):
    """Handler دریافت تاریخ تولد پارتنر جدید"""
    uid = message.chat.id

    try:
        gdate, jdate = parse_date_input(message.text)
        age, days_passed = calc_age_and_days(gdate)

        if age < 10 or age > 100:
            bot.send_message(
                uid, "❌ سن نامعتبر! لطفا تاریخ تولد واقعی وارد کن")
            return

        temp_data[uid]["partner_birthdate"] = gdate.isoformat()
        temp_data[uid]["partner_age"] = age

        bot.send_message(uid,
                         f"✅ تولد پارتنرت ثبت شد! 💕\n\n"
                         f"📅 میلادی: {gdate}\n"
                         f"📅 شمسی: {jdate.year}/{jdate.month:02d}/{jdate.day:02d}\n"
                         f"👤 سن: {age} سال\n\n"
                         f"😏 حالا یه لقب شوخی و دوستانه برایش انتخاب کن:")

        user_state[uid] = "add_partner_nick"

    except ValueError as e:
        bot.send_message(
            uid, f"❌ خطا در تاریخ: {str(e)}\n\nلطفا دوباره وارد کن:")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "add_partner_nick")
def add_partner_nick_handler(message):
    """Handler دریافت لقب پارتنر جدید"""
    uid = message.chat.id
    partner_nick = message.text.strip()

    if len(partner_nick) < 2:
        bot.send_message(uid, "❌ لقب باید حداقل ۲ حرف داشته باشه!")
        return

    temp_data[uid]["partner_nick"] = partner_nick
    user_state[uid] = "add_relation_type"

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("لانگ دیستنس 🌍", callback_data="add_rtype_لانگ"),
               InlineKeyboardButton("حضوری 💑", callback_data="add_rtype_حضوری"))
    markup.row(InlineKeyboardButton("مجازی 💻", callback_data="add_rtype_مجازی"),
               InlineKeyboardButton("تازه 💫", callback_data="add_rtype_تازه"))
    markup.row(InlineKeyboardButton(
        "قدیمی 💪", callback_data="add_rtype_قدیمی"))

    bot.send_message(uid, f"✅ لقب '{partner_nick}' ثبت شد! 😊\n\n💑 نوع رابطه‌تون چیه؟",
                     reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("add_rtype_"))
def add_relation_type_handler(call):
    """Handler انتخاب نوع رابطه برای پارتنر جدید"""
    uid = call.message.chat.id
    if user_state.get(uid) != "add_relation_type":
        bot.answer_callback_query(call.id, "❌ وضعیت نامعتبر")
        return

    relation_type = call.data.split("_")[2]
    temp_data[uid]["relation_type"] = relation_type

    bot.edit_message_text(f"✅ نوع رابطه '{relation_type}' ثبت شد!\n\n📅 حالا تاریخ شروع رابطه‌تون رو وارد کن:",
                          uid, call.message.message_id)
    user_state[uid] = "add_start_date"


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "add_start_date")
def add_start_date_handler(message):
    """Handler دریافت تاریخ شروع رابطه برای پارتنر جدید"""
    uid = message.chat.id

    try:
        gdate, jdate = parse_date_input(message.text)
        days_passed = get_relation_days(gdate)

        if days_passed < 0:
            bot.send_message(uid, "❌ تاریخ شروع رابطه نمی‌تونه آینده باشه!")
            return

        temp_data[uid]["start_date"] = gdate.isoformat()

        # آپدیت اطلاعات کاربر در دیتابیس
        data = temp_data[uid]
        query = """
        UPDATE users 
        SET partner_name = ?, partner_birthdate = ?, partner_age = ?, 
            partner_nick = ?, relation_type = ?, start_date = ?
        WHERE user_id = ?
        """

        result = safe_execute_db(query, (
            data["partner_name"], data["partner_birthdate"], data["partner_age"],
            data["partner_nick"], data["relation_type"], data["start_date"], uid
        ))

        if result is None:
            bot.send_message(uid, "❌ خطا در ذخیره اطلاعات پارتنر!")
            return

        # ایجاد مناسبت‌های پیش‌فرض جدید
        create_default_events(uid)

        # پاکسازی state
        user_state.pop(uid, None)
        temp_data.pop(uid, None)

        bot.send_message(uid,
                         f"🎉 اطلاعات پارتنر با موفقیت اضافه شد! 💖\n\n"
                         f"📅 شروع رابطه: {gdate}\n"
                         f"⏳ روزهای گذشته: {days_passed} روز\n"
                         f"🗓 شمسی: {jdate.year}/{jdate.month:02d}/{jdate.day:02d}\n\n"
                         f"✅ مناسبت‌های جدید برات ایجاد شدن:\n"
                         f"• تولد {data['partner_name']} 💕\n"
                         f"• سالگرد رابطه 💑\n\n"
                         f"حالا می‌تونی از منوی اصلی استفاده کنی:",
                         reply_markup=main_menu())

    except ValueError as e:
        bot.send_message(
            uid, f"❌ خطا در تاریخ: {str(e)}\n\nلطفا دوباره وارد کن:")


@bot.callback_query_handler(func=lambda call: call.data == "flirt")
def flirt_handler(call):
    """Handler لاس سنگین"""
    uid = call.message.chat.id
    message = random.choice(flirt_messages)
    bot.answer_callback_query(call.id, "💖 یه لاس سنگین برات فرستادم!")
    bot.send_message(uid, f"{message}\n\nبرای لاس بعدی دوباره کلیک کن! 😘")


@bot.callback_query_handler(func=lambda call: call.data == "suggestions")
def suggestions_handler(call):
    """Handler پیشنهادات رابطه"""
    uid = call.message.chat.id
    message = random.choice(suggestion_messages)
    bot.answer_callback_query(call.id, "💡 یه پیشنهاد جدید برات آماده کردم!")
    bot.send_message(uid, f"{message}\n\nبرای پیشنهاد بعدی دوباره کلیک کن! ✨")

# سیستم مناسبت‌ها


@bot.callback_query_handler(func=lambda call: call.data == "add_event")
def add_event_handler(call):
    """Handler شروع افزودن مناسبت"""
    uid = call.message.chat.id

    # بررسی وجود کاربر
    result = safe_execute_db("SELECT 1 FROM users WHERE user_id = ?", (uid,))
    if not result:
        bot.answer_callback_query(call.id, "❌ اول باید ثبت نام کنی!")
        return

    user_state[uid] = "event_title"
    temp_event_data[uid] = {}

    bot.edit_message_text("📌 موضوع مناسبت رو بنویس:\n(مثلا: سالگرد آشنایی، تولد پارتنر، اولین بوسه و...)",
                          uid, call.message.message_id)


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "event_title")
def event_title_handler(message):
    """Handler دریافت موضوع مناسبت"""
    uid = message.chat.id
    title = message.text.strip()

    if len(title) < 2:
        bot.send_message(uid, "❌ موضوع باید حداقل ۲ حرف داشته باشه!")
        return

    temp_event_data[uid]["title"] = title
    user_state[uid] = "event_description"

    bot.send_message(
        uid, "💬 حالا یه توضیح مختصر درباره این مناسبت بنویس:\n(اختیاری - اگه نمی‌خوای بنویس 'skip')")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "event_description")
def event_description_handler(message):
    """Handler دریافت توضیحات مناسبت"""
    uid = message.chat.id

    description = message.text.strip()
    if description.lower() == "skip":
        description = ""

    temp_event_data[uid]["description"] = description
    user_state[uid] = "event_date"

    bot.send_message(
        uid, "📅 تاریخ مناسبت رو وارد کن:\n(مثلا: 1403-10-15 یا 2025-01-05)")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "event_date")
def event_date_handler(message):
    """Handler دریافت تاریخ مناسبت"""
    uid = message.chat.id

    try:
        gdate, jdate = parse_date_input(message.text)
        temp_event_data[uid]["event_date"] = gdate.isoformat()
        temp_event_data[uid]["jdate"] = jdate

        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("📅 سالانه", callback_data="repeat_سالانه"),
                   InlineKeyboardButton("📅 ماهانه", callback_data="repeat_ماهانه"))
        markup.row(InlineKeyboardButton("📅 هفتگی", callback_data="repeat_هفتگی"),
                   InlineKeyboardButton("📅 روزانه", callback_data="repeat_روزانه"))
        markup.row(InlineKeyboardButton(
            "❌ بدون تکرار", callback_data="repeat_هیچ"))

        bot.send_message(uid,
                         f"✅ تاریخ مناسبت ثبت شد!\n"
                         f"📅 میلادی: {gdate}\n"
                         f"📅 شمسی: {jdate.year}/{jdate.month:02d}/{jdate.day:02d}\n\n"
                         f"🔁 آیا این مناسبت تکرار میشه؟",
                         reply_markup=markup)

        user_state[uid] = "event_repeat"

    except ValueError as e:
        bot.send_message(
            uid, f"❌ خطا در تاریخ: {str(e)}\n\nلطفا دوباره وارد کن:")


@bot.callback_query_handler(func=lambda call: call.data.startswith("repeat_"))
def event_repeat_handler(call):
    """Handler انتخاب نوع تکرار"""
    uid = call.message.chat.id
    if user_state.get(uid) != "event_repeat":
        bot.answer_callback_query(call.id, "❌ وضعیت نامعتبر")
        return

    repeat_type = call.data.split("_")[1]

    # نگاشت به مقادیر انگلیسی برای دیتابیس
    repeat_map = {
        "هیچ": "none",
        "روزانه": "daily",
        "هفتگی": "weekly",
        "ماهانه": "monthly",
        "سالانه": "yearly"
    }

    repeat_type_en = repeat_map.get(repeat_type, "none")
    temp_event_data[uid]["repeat_type"] = repeat_type_en
    temp_event_data[uid]["repeat_type_fa"] = repeat_type

    # ذخیره در دیتابیس
    data = temp_event_data[uid]
    query = """
    INSERT INTO notifications (user_id, title, description, event_date, repeat_type)
    VALUES (?, ?, ?, ?, ?)
    """

    result = safe_execute_db(query, (
        uid, data["title"], data["description"],
        data["event_date"], repeat_type_en
    ), "notifications")

    if result is None:
        bot.answer_callback_query(call.id, "❌ خطا در ذخیره مناسبت!")
        return

    # پاکسازی state
    user_state.pop(uid, None)
    temp_data.pop(uid, None)

    jdate = data["jdate"]
    random_msg = random.choice(random_messages)

    bot.edit_message_text(
        f"🎉 مناسبت با موفقیت ثبت شد! ✅\n\n"
        f"📌 موضوع: {data['title']}\n"
        f"📅 تاریخ: {jdate.year}/{jdate.month:02d}/{jdate.day:02d}\n"
        f"🔁 تکرار: {repeat_type}\n\n"
        f"{random_msg}\n\n"
        f"💌 از این به بعد به موقع بهت یادآوری میشه!",
        uid, call.message.message_id
    )

    # پاکسازی داده‌های موقت
    temp_event_data.pop(uid, None)


@bot.callback_query_handler(func=lambda call: call.data == "my_events")
def my_events_handler(call):
    """Handler نمایش لیست مناسبت‌ها به صورت اینلاین"""
    uid = call.message.chat.id

    result = safe_execute_db("""
        SELECT id, title, event_date 
        FROM notifications 
        WHERE user_id = ? AND is_active = 1
        ORDER BY event_date ASC
    """, (uid,), "notifications")

    if not result:
        bot.send_message(uid, "📭 هنوز هیچ مناسبتی ثبت نکردی!",
                         reply_markup=main_menu())
        return

    markup = InlineKeyboardMarkup()
    for event_id, title, event_date in result:
        gdate = datetime.strptime(event_date, "%Y-%m-%d").date()
        days_until = (gdate - date.today()).days

        if days_until > 0:
            time_text = f"⏳ {days_until} روز دیگر"
        elif days_until == 0:
            time_text = "🎉 امروز"
        else:
            time_text = f"📅 {abs(days_until)} روز گذشته"

        button_text = f"{title} - {time_text}"
        markup.add(InlineKeyboardButton(
            button_text, callback_data=f"event_{event_id}"))

    markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main"))
    bot.edit_message_text("📅 مناسبت‌های تو (مرتب شده بر اساس نزدیک‌ترین):",
                          uid, call.message.message_id, reply_markup=markup)


# سیستم نوتیفیکیشن
def get_notification_times(event_date: date, repeat_type: str):
    """محاسبه زمان‌های ارسال نوتیفیکیشن"""
    event_datetime = datetime.combine(event_date, datetime.min.time())
    notify_points = []

    if repeat_type == "none":
        notify_points = [
            event_datetime - timedelta(days=7),
            event_datetime - timedelta(days=3),
            event_datetime - timedelta(days=1),
            event_datetime
        ]
    elif repeat_type == "daily":
        notify_points = [event_datetime]
    elif repeat_type == "weekly":
        notify_points = [
            event_datetime - timedelta(days=3),
            event_datetime - timedelta(days=1),
            event_datetime
        ]
    elif repeat_type == "monthly":
        notify_points = [
            event_datetime - timedelta(days=7),
            event_datetime - timedelta(days=3),
            event_datetime - timedelta(days=1),
            event_datetime
        ]
    elif repeat_type == "yearly":
        notify_points = [
            event_datetime - timedelta(days=30),
            event_datetime - timedelta(days=14),
            event_datetime - timedelta(days=7),
            event_datetime - timedelta(days=3),
            event_datetime - timedelta(days=1),
            event_datetime
        ]

    return notify_points


def send_notifications():
    """ارسال نوتیفیکیشن‌های زمان‌رسیده"""
    try:
        conn = sqlite3.connect("notifications.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("""
            SELECT id, user_id, title, description, event_date, repeat_type, notify_times, sent_flags 
            FROM notifications 
            WHERE is_active = 1
        """)
        rows = cur.fetchall()

        now = datetime.now()

        for row in rows:
            notif_id, user_id, title, description, event_date, repeat_type, notify_times, sent_flags = row

            try:
                gdate = datetime.strptime(event_date, "%Y-%m-%d").date()
                jdate = jdatetime.date.fromgregorian(date=gdate)

                if not notify_times or notify_times == "[]":
                    notify_times_list = [
                        dt.isoformat() for dt in get_notification_times(gdate, repeat_type)]
                    cur.execute("UPDATE notifications SET notify_times = ? WHERE id = ?",
                                (json.dumps(notify_times_list), notif_id))
                    conn.commit()
                    notify_times = json.dumps(notify_times_list)

                notify_times_list = json.loads(notify_times)
                sent_flags_list = json.loads(sent_flags) if sent_flags else []

                # بررسی زمان‌های نوتیفیکیشن
                for i, ntime in enumerate(notify_times_list):
                    ntime_dt = datetime.fromisoformat(ntime)

                    if ntime_dt <= now and i not in sent_flags_list:
                        # ارسال نوتیفیکیشن
                        days_until = (gdate - date.today()).days

                        if days_until > 0:
                            message = f"🔔 یادآوری مناسبت:\n\n📌 {title}\n📅 تاریخ: {jdate.year}/{jdate.month:02d}/{jdate.day:02d}\n⏳ {days_until} روز دیگر\n💬 {description or 'بدون توضیح'}"
                        elif days_until == 0:
                            message = f"🎉 امروز مناسبتت هست!\n\n📌 {title}\n📅 امروز: {jdate.year}/{jdate.month:02d}/{jdate.day:02d}\n💬 {description or 'بدون توضیح'}\n\nبرات بهترین‌ها رو آرزو می‌کنم! 💖"

                        try:
                            bot.send_message(user_id, message)
                            sent_flags_list.append(i)
                            cur.execute("UPDATE notifications SET sent_flags = ? WHERE id = ?",
                                        (json.dumps(sent_flags_list), notif_id))
                            conn.commit()
                        except Exception as e:
                            print(f"خطا در ارسال به کاربر {user_id}: {e}")

            except Exception as e:
                print(f"خطا در پردازش نوتیفیکیشن {notif_id}: {e}")
                continue

        cur.close()
        conn.close()

    except Exception as e:
        print(f"خطا در اجرای نوتیفیکیشن: {e}")


def notification_loop():
    """حلقه اصلی نوتیفیکیشن"""
    while True:
        try:
            send_notifications()
            check_and_send_mood_reminders()
        except Exception as e:
            print(f"خطا در حلقه نوتیفیکیشن: {e}")
        time.sleep(300)


@bot.callback_query_handler(func=lambda call: call.data.startswith("event_"))
def event_detail_handler(call):
    """Handler نمایش جزئیات مناسبت"""
    uid = call.message.chat.id
    event_id = parse_event_id(call.data)

    if not event_id:
        bot.answer_callback_query(call.id, "❌ خطا در شناسایی مناسبت!")
        return

    result = safe_execute_db("""
        SELECT title, description, event_date, repeat_type 
        FROM notifications WHERE id = ? AND user_id = ?
    """, (event_id, uid), "notifications")

    if not result:
        bot.answer_callback_query(call.id, "❌ مناسبت پیدا نشد!")
        return

    title, description, event_date, repeat_type = result[0]
    gdate = datetime.strptime(event_date, "%Y-%m-%d").date()
    jdate = jdatetime.date.fromgregorian(date=gdate)

    # محاسبه زمان باقی‌مانده در پایتون
    days_until, year_info = calculate_days_until_event(event_date)
    time_text = format_time_remaining(days_until, year_info)

    # تاریخ بعدی مناسبت
    today = date.today()
    event_this_year = gdate.replace(year=today.year)
    if event_this_year < today:
        next_occurrence = gdate.replace(year=today.year + 1)
        next_jdate = jdatetime.date.fromgregorian(date=next_occurrence)
        occurrence_text = f"📅 بعدی: {next_jdate.year}/{next_jdate.month:02d}/{next_jdate.day:02d}"
    else:
        occurrence_text = f"📅 امسال: {jdate.year}/{jdate.month:02d}/{jdate.day:02d}"

    repeat_map = {
        "none": "بدون تکرار",
        "daily": "روزانه",
        "weekly": "هفتگی",
        "monthly": "ماهانه",
        "yearly": "سالانه"
    }
    repeat_fa = repeat_map.get(repeat_type, "نامشخص")

    text = f"""
📋 **جزئیات مناسبت**

📌 **عنوان:** {title}
{occurrence_text}
🔁 **تکرار:** {repeat_fa}

**⏰ {time_text}**
"""
    if description and description.strip():
        text += f"\n💬 **توضیحات:** {description}"

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✏️ ویرایش", callback_data=f"edit_{event_id}"),
        InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_{event_id}")
    )
    markup.row(InlineKeyboardButton(
        "📋 بازگشت به لیست", callback_data="my_events"))

    try:
        bot.edit_message_text(
            text,
            uid,
            call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except:
        bot.send_message(uid, text, reply_markup=markup, parse_mode="Markdown")


# Handler بازگشت به منوی اصلی
@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
def back_to_main_handler(call):
    """Handler بازگشت به منوی اصلی"""
    uid = call.message.chat.id
    try:
        bot.edit_message_text(
            "🏠 به منوی اصلی خوش اومدی! چه کاری می‌خوای انجام بدی؟",
            uid,
            call.message.message_id,
            reply_markup=main_menu()
        )
    except:
        bot.send_message(
            uid,
            "🏠 به منوی اصلی خوش اومدی! چه کاری می‌خوای انجام بدی؟",
            reply_markup=main_menu()
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_event_"))
def delete_event_handler(call):
    """Handler حذف مناسبت (جدید - بدون تداخل)"""
    uid = call.message.chat.id

    try:
        event_id = int(call.data.split("_")[2])

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton(
                "✅ بله، حذف کن", callback_data=f"confirm_delete_event_{event_id}"),
            InlineKeyboardButton(
                "❌ خیر، بازگشت", callback_data=f"event_{event_id}")
        )

        bot.edit_message_text(
            "⚠️ آیا مطمئنی می‌خوای این مناسبت رو حذف کنی؟",
            uid, call.message.message_id,
            reply_markup=markup
        )

    except (ValueError, IndexError):
        return


@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_delete_"))
def confirm_delete_handler(call):
    """Handler حذف نهایی مناسبت"""
    uid = call.message.chat.id
    event_id = int(call.data.split("_")[2])

    safe_execute_db("DELETE FROM notifications WHERE id = ? AND user_id = ?",
                    (event_id, uid), "notifications")

    bot.answer_callback_query(call.id, "✅ مناسبت حذف شد!")
    my_events_handler(call)  # بازگشت به لیست مناسبت‌ها


# Handlerهای ویرایش مناسبت - نسخه دیباگ شده
def parse_event_id(callback_data):
    """تابع کمکی برای استخراج event_id از callback_data"""
    try:
        parts = callback_data.split('_')
        # پیدا کردن آخرین عدد در لیست
        for part in reversed(parts):
            if part.isdigit():
                return int(part)
        return None
    except:
        return None


@bot.callback_query_handler(func=lambda call: call.data == "my_events")
def my_events_handler(call):
    """Handler نمایش لیست مناسبت‌ها"""
    uid = call.message.chat.id

    # دریافت مناسبت‌ها با نوع تکرار
    result = safe_execute_db("""
        SELECT id, title, event_date, repeat_type 
        FROM notifications 
        WHERE user_id = ? AND is_active = 1
    """, (uid,), "notifications")

    if not result:
        try:
            bot.edit_message_text(
                "📭 هنوز هیچ مناسبتی ثبت نکردی!",
                uid, call.message.message_id,
                reply_markup=main_menu()
            )
        except:
            bot.send_message(uid, "📭 هنوز هیچ مناسبتی ثبت نکردی!",
                             reply_markup=main_menu())
        return

    # مرتب‌سازی مناسبت‌ها
    sorted_events = sort_events_by_upcoming(result)

    markup = InlineKeyboardMarkup()

    for event_id, title, event_date, repeat_type in sorted_events:
        days_until, time_info, next_date = calculate_days_until_event(
            event_date, repeat_type)
        time_text = format_time_remaining(days_until, time_info)

        # کوتاه کردن عنوان
        display_title = title[:18] + "..." if len(title) > 18 else title
        button_text = f"{display_title}\n{time_text}"

        markup.add(InlineKeyboardButton(
            button_text, callback_data=f"event_{event_id}"))

    markup.add(InlineKeyboardButton(
        "🔙 بازگشت به منوی اصلی", callback_data="back_to_main"))

    try:
        bot.edit_message_text(
            "📅 مناسبت‌های تو (مرتب شده بر اساس نزدیک‌ترین تاریخ):",
            uid, call.message.message_id,
            reply_markup=markup
        )
    except:
        bot.send_message(
            uid,
            "📅 مناسبت‌های تو (مرتب شده بر اساس نزدیک‌ترین تاریخ):",
            reply_markup=markup
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("event_"))
def event_detail_handler(call):
    """Handler نمایش جزئیات مناسبت"""
    uid = call.message.chat.id
    event_id = parse_event_id(call.data)

    if not event_id:
        bot.answer_callback_query(call.id, "❌ خطا در شناسایی مناسبت!")
        return

    result = safe_execute_db("""
        SELECT title, description, event_date, repeat_type 
        FROM notifications WHERE id = ? AND user_id = ?
    """, (event_id, uid), "notifications")

    if not result:
        bot.answer_callback_query(call.id, "❌ مناسبت پیدا نشد!")
        return

    title, description, event_date, repeat_type = result[0]
    event_gdate = datetime.strptime(event_date, "%Y-%m-%d").date()
    jdate = jdatetime.date.fromgregorian(date=event_gdate)

    # محاسبه زمان با الگوریتم جدید
    days_until, time_info, next_date = calculate_days_until_event(
        event_date, repeat_type)
    next_jdate = jdatetime.date.fromgregorian(date=next_date)

    # اطلاعات تکرار
    repeat_map = {
        "none": "بدون تکرار",
        "daily": "روزانه",
        "weekly": "هفتگی",
        "monthly": "ماهانه",
        "yearly": "سالانه"
    }
    repeat_fa = repeat_map.get(repeat_type, "نامشخص")

    # متن پیام
    text = f"""
📋 **جزئیات مناسبت**

📌 **عنوان:** {title}
📅 **تاریخ اصلی:** {jdate.year}/{jdate.month:02d}/{jdate.day:02d}
📅 **{time_info}:** {next_jdate.year}/{next_jdate.month:02d}/{next_jdate.day:02d}
🔁 **تکرار:** {repeat_fa}

"""

    # اطلاعات زمان باقی‌مانده
    if days_until == 0:
        text += "**🎉 امروز مناسبت شماست!**"
    else:
        text += f"**⏳ {days_until} روز تا {time_info}**"

    if description and description.strip():
        text += f"\n\n💬 **توضیحات:** {description}"

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✏️ ویرایش", callback_data=f"edit_{event_id}"),
        InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_{event_id}")
    )
    markup.row(InlineKeyboardButton(
        "📋 بازگشت به لیست", callback_data="my_events"))

    try:
        bot.edit_message_text(
            text,
            uid,
            call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except:
        bot.send_message(uid, text, reply_markup=markup, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_"))
def edit_event_handler(call):
    """Handler منوی ویرایش مناسبت با بررسی نوع مناسبت"""
    uid = call.message.chat.id
    event_id = parse_event_id(call.data)

    if not event_id:
        bot.answer_callback_query(call.id, "❌ خطا در شناسایی مناسبت!")
        return

    # بررسی اینکه آیا مناسبت پیش‌فرض است
    result = safe_execute_db("""
        SELECT title FROM notifications WHERE id = ? AND user_id = ?
    """, (event_id, uid), "notifications")

    if not result:
        bot.answer_callback_query(call.id, "❌ مناسبت پیدا نشد!")
        return

    title = result[0][0]
    is_default_event = any(keyword in title for keyword in [
                           "تولد", "سالگرد", "ماهگرد"])

    markup = InlineKeyboardMarkup()

    if is_default_event:
        # برای مناسبت‌های پیش‌فرض فقط تاریخ و توضیحات قابل ویرایش است
        markup.row(InlineKeyboardButton("📅 ویرایش تاریخ",
                   callback_data=f"editdate_{event_id}"))
        markup.row(InlineKeyboardButton("📝 ویرایش توضیحات",
                   callback_data=f"editdesc_{event_id}"))
        markup.row(InlineKeyboardButton(
            "🔙 بازگشت", callback_data=f"event_{event_id}"))

        message_text = "✏️ این مناسبت پیش‌فرض است. فقط می‌تونی تاریخ و توضیحات رو ویرایش کنی:"
    else:
        # برای مناسبت‌های عادی همه چیز قابل ویرایش است
        markup.row(InlineKeyboardButton("✏️ ویرایش عنوان",
                   callback_data=f"edittitle_{event_id}"))
        markup.row(InlineKeyboardButton("📝 ویرایش توضیحات",
                   callback_data=f"editdesc_{event_id}"))
        markup.row(InlineKeyboardButton("📅 ویرایش تاریخ",
                   callback_data=f"editdate_{event_id}"))
        markup.row(InlineKeyboardButton("🔁 ویرایش تکرار",
                   callback_data=f"editrepeat_{event_id}"))
        markup.row(InlineKeyboardButton(
            "🔙 بازگشت", callback_data=f"event_{event_id}"))

        message_text = "✏️ چه قسمتی از مناسبت رو می‌خوای ویرایش کنی؟"

    try:
        bot.edit_message_text(
            message_text,
            uid, call.message.message_id,
            reply_markup=markup
        )
    except:
        bot.send_message(uid, message_text, reply_markup=markup)


# ویرایش عنوان
@bot.callback_query_handler(func=lambda call: call.data.startswith("edittitle_"))
def edit_title_start_handler(call):
    """Handler شروع ویرایش عنوان"""
    uid = call.message.chat.id
    event_id = parse_event_id(call.data)

    if not event_id:
        bot.answer_callback_query(call.id, "❌ خطا در شناسایی مناسبت!")
        return

    user_state[uid] = f"waiting_title_{event_id}"

    try:
        bot.edit_message_text(
            "✏️ عنوان جدید مناسبت رو وارد کن:",
            uid, call.message.message_id
        )
    except:
        bot.send_message(uid, "✏️ عنوان جدید مناسبت رو وارد کن:")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id, "").startswith("waiting_title_"))
def edit_title_finish_handler(message):
    """Handler دریافت عنوان جدید"""
    uid = message.chat.id
    state = user_state.get(uid, "")

    if not state.startswith("waiting_title_"):
        return

    try:
        event_id = int(state.split("_")[2])
    except:
        bot.send_message(uid, "❌ خطا در پردازش!")
        user_state.pop(uid, None)
        return

    new_title = message.text.strip()

    if len(new_title) < 2:
        bot.send_message(uid, "❌ عنوان باید حداقل ۲ حرف داشته باشه!")
        return

    result = safe_execute_db(
        "UPDATE notifications SET title = ? WHERE id = ? AND user_id = ?",
        (new_title, event_id, uid), "notifications"
    )

    if result is not None:
        bot.send_message(uid, "✅ عنوان مناسبت با موفقیت ویرایش شد!")
        # نمایش مجدد جزئیات مناسبت
        show_event_details(uid, event_id)
    else:
        bot.send_message(uid, "❌ خطا در ویرایش عنوان!")

    user_state.pop(uid, None)

# ویرایش توضیحات


@bot.callback_query_handler(func=lambda call: call.data.startswith("editdesc_"))
def edit_desc_start_handler(call):
    """Handler شروع ویرایش توضیحات"""
    uid = call.message.chat.id
    event_id = parse_event_id(call.data)

    if not event_id:
        bot.answer_callback_query(call.id, "❌ خطا در شناسایی مناسبت!")
        return

    user_state[uid] = f"waiting_desc_{event_id}"

    try:
        bot.edit_message_text(
            "📝 توضیحات جدید مناسبت رو وارد کن (یا 'حذف' برای پاک کردن):",
            uid, call.message.message_id
        )
    except:
        bot.send_message(
            uid, "📝 توضیحات جدید مناسبت رو وارد کن (یا 'حذف' برای پاک کردن):")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id, "").startswith("waiting_desc_"))
def edit_desc_finish_handler(message):
    """Handler دریافت توضیحات جدید"""
    uid = message.chat.id
    state = user_state.get(uid, "")

    if not state.startswith("waiting_desc_"):
        return

    try:
        event_id = int(state.split("_")[2])
    except:
        bot.send_message(uid, "❌ خطا در پردازش!")
        user_state.pop(uid, None)
        return

    new_desc = message.text.strip()

    if new_desc.lower() == "حذف":
        new_desc = ""

    result = safe_execute_db(
        "UPDATE notifications SET description = ? WHERE id = ? AND user_id = ?",
        (new_desc, event_id, uid), "notifications"
    )

    if result is not None:
        bot.send_message(uid, "✅ توضیحات مناسبت با موفقیت ویرایش شد!")
        show_event_details(uid, event_id)
    else:
        bot.send_message(uid, "❌ خطا در ویرایش توضیحات!")

    user_state.pop(uid, None)

# ویرایش تاریخ


@bot.callback_query_handler(func=lambda call: call.data.startswith("editdate_"))
def edit_date_start_handler(call):
    """Handler شروع ویرایش تاریخ"""
    uid = call.message.chat.id
    event_id = parse_event_id(call.data)

    if not event_id:
        bot.answer_callback_query(call.id, "❌ خطا در شناسایی مناسبت!")
        return

    user_state[uid] = f"waiting_date_{event_id}"

    try:
        bot.edit_message_text(
            "📅 تاریخ جدید مناسبت رو وارد کن (مثلا: 1403-10-15 یا 2025-01-05):",
            uid, call.message.message_id
        )
    except:
        bot.send_message(
            uid, "📅 تاریخ جدید مناسبت رو وارد کن (مثلا: 1403-10-15 یا 2025-01-05):")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id, "").startswith("waiting_date_"))
def edit_date_finish_handler(message):
    """Handler دریافت تاریخ جدید"""
    uid = message.chat.id
    state = user_state.get(uid, "")

    if not state.startswith("waiting_date_"):
        return

    try:
        event_id = int(state.split("_")[2])
    except:
        bot.send_message(uid, "❌ خطا در پردازش!")
        user_state.pop(uid, None)
        return

    try:
        gdate, jdate = parse_date_input(message.text)
        new_date = gdate.isoformat()

        result = safe_execute_db(
            "UPDATE notifications SET event_date = ?, notify_times = '[]', sent_flags = '[]' WHERE id = ? AND user_id = ?",
            (new_date, event_id, uid), "notifications"
        )

        if result is not None:
            bot.send_message(
                uid, f"✅ تاریخ مناسبت به {jdate.year}/{jdate.month:02d}/{jdate.day:02d} ویرایش شد!")
            show_event_details(uid, event_id)
        else:
            bot.send_message(uid, "❌ خطا در ویرایش تاریخ!")

    except ValueError as e:
        bot.send_message(uid, f"❌ خطا در تاریخ: {str(e)}")

    user_state.pop(uid, None)

# ویرایش تکرار


@bot.callback_query_handler(func=lambda call: call.data.startswith("editrepeat_"))
def edit_repeat_handler(call):
    """Handler ویرایش نوع تکرار"""
    uid = call.message.chat.id
    event_id = parse_event_id(call.data)

    if not event_id:
        bot.answer_callback_query(call.id, "❌ خطا در شناسایی مناسبت!")
        return

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(
            "📅 سالانه", callback_data=f"setrepeat_yearly_{event_id}"),
        InlineKeyboardButton(
            "📅 ماهانه", callback_data=f"setrepeat_monthly_{event_id}")
    )
    markup.row(
        InlineKeyboardButton(
            "📅 هفتگی", callback_data=f"setrepeat_weekly_{event_id}"),
        InlineKeyboardButton(
            "📅 روزانه", callback_data=f"setrepeat_daily_{event_id}")
    )
    markup.row(InlineKeyboardButton("❌ بدون تکرار",
               callback_data=f"setrepeat_none_{event_id}"))
    markup.row(InlineKeyboardButton(
        "🔙 بازگشت", callback_data=f"edit_{event_id}"))

    try:
        bot.edit_message_text(
            "🔁 نوع تکرار جدید رو انتخاب کن:",
            uid, call.message.message_id,
            reply_markup=markup
        )
    except:
        bot.send_message(uid, "🔁 نوع تکرار جدید رو انتخاب کن:",
                         reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("setrepeat_"))
def set_repeat_handler(call):
    """Handler تنظیم نوع تکرار جدید"""
    uid = call.message.chat.id
    event_id = parse_event_id(call.data)

    if not event_id:
        bot.answer_callback_query(call.id, "❌ خطا در شناسایی مناسبت!")
        return

    # استخراج نوع تکرار از callback_data
    parts = call.data.split('_')
    if len(parts) < 2:
        bot.answer_callback_query(call.id, "❌ خطا در پردازش!")
        return

    repeat_type = parts[1]  # yearly, monthly, weekly, daily, none

    repeat_map = {
        "none": "بدون تکرار",
        "daily": "روزانه",
        "weekly": "هفتگی",
        "monthly": "ماهانه",
        "yearly": "سالانه"
    }

    repeat_fa = repeat_map.get(repeat_type, "نامشخص")

    result = safe_execute_db(
        "UPDATE notifications SET repeat_type = ?, notify_times = '[]', sent_flags = '[]' WHERE id = ? AND user_id = ?",
        (repeat_type, event_id, uid), "notifications"
    )

    if result is not None:
        bot.answer_callback_query(
            call.id, f"✅ نوع تکرار به {repeat_fa} تغییر کرد!")
        show_event_details(uid, event_id)
    else:
        bot.answer_callback_query(call.id, "❌ خطا در ویرایش نوع تکرار!")


def show_event_details(uid, event_id):
    """نمایش جزئیات مناسبت بعد از ویرایش"""
    result = safe_execute_db("""
        SELECT title, description, event_date, repeat_type 
        FROM notifications WHERE id = ? AND user_id = ?
    """, (event_id, uid), "notifications")

    if not result:
        bot.send_message(uid, "❌ مناسبت پیدا نشد!")
        return

    title, description, event_date, repeat_type = result[0]
    event_gdate = datetime.strptime(event_date, "%Y-%m-%d").date()
    jdate = jdatetime.date.fromgregorian(date=event_gdate)

    # محاسبه زمان با الگوریتم جدید
    days_until, time_info, next_date = calculate_days_until_event(
        event_date, repeat_type)

    repeat_map = {
        "none": "بدون تکرار",
        "daily": "روزانه",
        "weekly": "هفتگی",
        "monthly": "ماهانه",
        "yearly": "سالانه"
    }
    repeat_fa = repeat_map.get(repeat_type, "نامشخص")

    text = f"""
📋 **مناسبت ویرایش شد**

📌 **عنوان:** {title}
📅 **تاریخ اصلی:** {jdate.year}/{jdate.month:02d}/{jdate.day:02d}
🔁 **تکرار:** {repeat_fa}

"""

    if days_until == 0:
        text += "**🎉 امروز مناسبت شماست!**"
    else:
        text += f"**⏳ {days_until} روز تا {time_info}**"

    if description and description.strip():
        text += f"\n\n💬 **توضیحات:** {description}"

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(
            "✏️ ویرایش مجدد", callback_data=f"edit_{event_id}"),
        InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_{event_id}")
    )
    markup.row(InlineKeyboardButton(
        "📋 بازگشت به لیست", callback_data="my_events"))
    markup.row(InlineKeyboardButton(
        "🏠 منوی اصلی", callback_data="back_to_main"))

    bot.send_message(uid, text, reply_markup=markup, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: call.data == "edit_profile")
def edit_profile_handler(call):
    uid = call.message.chat.id

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(
        "✏️ ویرایش نام", callback_data="edit_name"))
    markup.row(InlineKeyboardButton(
        "🎂 ویرایش تاریخ تولد", callback_data="edit_birthdate"))
    markup.row(InlineKeyboardButton("💖 ویرایش نام پارتنر",
               callback_data="edit_partner_name"))
    markup.row(InlineKeyboardButton("📅 ویرایش تولد پارتنر",
               callback_data="edit_partner_birthdate"))
    markup.row(InlineKeyboardButton("😂 ویرایش لقب پارتنر",
               callback_data="edit_partner_nick"))
    markup.row(InlineKeyboardButton("💑 ویرایش نوع رابطه",
               callback_data="edit_relation_type"))
    markup.row(InlineKeyboardButton(
        "📆 ویرایش تاریخ شروع رابطه", callback_data="edit_start_date"))
    markup.row(InlineKeyboardButton("🔙 بازگشت", callback_data="show_info"))

    try:
        bot.edit_message_text(
            "✏️ کدوم اطلاعات رو می‌خوای ویرایش کنی؟",
            uid, call.message.message_id,
            reply_markup=markup
        )
    except:
        bot.send_message(
            uid, "✏️ کدوم اطلاعات رو می‌خوای ویرایش کنی؟", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "edit_name")
def edit_name_handler(call):
    uid = call.message.chat.id
    user_state[uid] = "waiting_edit_name"

    try:
        bot.edit_message_text("✏️ نام جدیدت رو وارد کن:",
                              uid, call.message.message_id)
    except:
        bot.send_message(uid, "✏️ نام جدیدت رو وارد کن:")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_edit_name")
def save_edit_name_handler(message):
    uid = message.chat.id
    new_name = message.text.strip()

    if len(new_name) < 2:
        bot.send_message(uid, "❌ نام باید حداقل ۲ حرف داشته باشه!")
        return

    safe_execute_db(
        "UPDATE users SET name = ? WHERE user_id = ?", (new_name, uid))
    bot.send_message(uid, f"✅ نامت به '{new_name}' تغییر کرد!")
    user_state.pop(uid, None)
    show_info_handler_simple(uid)


@bot.callback_query_handler(func=lambda call: call.data == "edit_birthdate")
def edit_birthdate_handler(call):
    uid = call.message.chat.id
    user_state[uid] = "waiting_edit_birthdate"

    try:
        bot.edit_message_text(
            "📅 تاریخ تولد جدیدت رو وارد کن (مثلا: 1375-03-15):", uid, call.message.message_id)
    except:
        bot.send_message(
            uid, "📅 تاریخ تولد جدیدت رو وارد کن (مثلا: 1375-03-15):")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_edit_birthdate")
def save_edit_birthdate_handler(message):
    uid = message.chat.id

    try:
        gdate, jdate = parse_date_input(message.text)
        new_birthdate = gdate.isoformat()

        safe_execute_db(
            "UPDATE users SET birthdate = ? WHERE user_id = ?", (new_birthdate, uid))
        bot.send_message(
            uid, f"✅ تاریخ تولدت به {jdate.year}/{jdate.month:02d}/{jdate.day:02d} تغییر کرد!")
        user_state.pop(uid, None)
        show_info_handler_simple(uid)

    except ValueError as e:
        bot.send_message(uid, f"❌ خطا در تاریخ: {str(e)}")


@bot.callback_query_handler(func=lambda call: call.data == "edit_partner_name")
def edit_partner_name_handler(call):
    uid = call.message.chat.id
    user_state[uid] = "waiting_edit_partner_name"

    try:
        bot.edit_message_text(
            "💖 نام جدید پارتنرت رو وارد کن:", uid, call.message.message_id)
    except:
        bot.send_message(uid, "💖 نام جدید پارتنرت رو وارد کن:")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_edit_partner_name")
def save_edit_partner_name_handler(message):
    uid = message.chat.id
    new_partner_name = message.text.strip()

    if len(new_partner_name) < 2:
        bot.send_message(uid, "❌ نام پارتنر باید حداقل ۲ حرف داشته باشه!")
        return

    safe_execute_db(
        "UPDATE users SET partner_name = ? WHERE user_id = ?", (new_partner_name, uid))
    bot.send_message(uid, f"✅ نام پارتنرت به '{new_partner_name}' تغییر کرد!")
    user_state.pop(uid, None)
    show_info_handler_simple(uid)


@bot.callback_query_handler(func=lambda call: call.data == "edit_partner_birthdate")
def edit_partner_birthdate_handler(call):
    uid = call.message.chat.id
    user_state[uid] = "waiting_edit_partner_birthdate"

    try:
        bot.edit_message_text(
            "📅 تاریخ تولد جدید پارتنرت رو وارد کن (مثلا: 1378-08-20):", uid, call.message.message_id)
    except:
        bot.send_message(
            uid, "📅 تاریخ تولد جدید پارتنرت رو وارد کن (مثلا: 1378-08-20):")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_edit_partner_birthdate")
def save_edit_partner_birthdate_handler(message):
    uid = message.chat.id

    try:
        gdate, jdate = parse_date_input(message.text)
        new_birthdate = gdate.isoformat()
        age, _ = calc_age_and_days(gdate)

        safe_execute_db("UPDATE users SET partner_birthdate = ?, partner_age = ? WHERE user_id = ?",
                        (new_birthdate, age, uid))
        bot.send_message(
            uid, f"✅ تاریخ تولد پارتنرت به {jdate.year}/{jdate.month:02d}/{jdate.day:02d} تغییر کرد!")
        user_state.pop(uid, None)
        show_info_handler_simple(uid)

    except ValueError as e:
        bot.send_message(uid, f"❌ خطا در تاریخ: {str(e)}")


@bot.callback_query_handler(func=lambda call: call.data == "edit_partner_nick")
def edit_partner_nick_handler(call):
    uid = call.message.chat.id
    user_state[uid] = "waiting_edit_partner_nick"

    try:
        bot.edit_message_text(
            "😂 لقب جدید پارتنرت رو وارد کن:", uid, call.message.message_id)
    except:
        bot.send_message(uid, "😂 لقب جدید پارتنرت رو وارد کن:")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_edit_partner_nick")
def save_edit_partner_nick_handler(message):
    uid = message.chat.id
    new_partner_nick = message.text.strip()

    if len(new_partner_nick) < 2:
        bot.send_message(uid, "❌ لقب باید حداقل ۲ حرف داشته باشه!")
        return

    safe_execute_db(
        "UPDATE users SET partner_nick = ? WHERE user_id = ?", (new_partner_nick, uid))
    bot.send_message(uid, f"✅ لقب پارتنرت به '{new_partner_nick}' تغییر کرد!")
    user_state.pop(uid, None)
    show_info_handler_simple(uid)


@bot.callback_query_handler(func=lambda call: call.data == "edit_relation_type")
def edit_relation_type_handler(call):
    uid = call.message.chat.id

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(
        "لانگ دیستنس 🌍", callback_data="edit_rtype_لانگ"))
    markup.row(InlineKeyboardButton(
        "حضوری 💑", callback_data="edit_rtype_حضوری"))
    markup.row(InlineKeyboardButton(
        "مجازی 💻", callback_data="edit_rtype_مجازی"))
    markup.row(InlineKeyboardButton("🔙 بازگشت", callback_data="edit_profile"))

    try:
        bot.edit_message_text("💑 نوع رابطه جدید رو انتخاب کن:",
                              uid, call.message.message_id, reply_markup=markup)
    except:
        bot.send_message(uid, "💑 نوع رابطه جدید رو انتخاب کن:",
                         reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_rtype_"))
def save_edit_relation_type_handler(call):
    uid = call.message.chat.id
    new_relation_type = call.data.split("_")[2]

    safe_execute_db(
        "UPDATE users SET relation_type = ? WHERE user_id = ?", (new_relation_type, uid))
    bot.answer_callback_query(
        call.id, f"✅ نوع رابطه به '{new_relation_type}' تغییر کرد!")
    show_info_handler_simple(uid)


@bot.callback_query_handler(func=lambda call: call.data == "edit_start_date")
def edit_start_date_handler(call):
    uid = call.message.chat.id
    user_state[uid] = "waiting_edit_start_date"

    try:
        bot.edit_message_text(
            "📆 تاریخ شروع رابطه جدید رو وارد کن (مثلا: 1402-05-10):", uid, call.message.message_id)
    except:
        bot.send_message(
            uid, "📆 تاریخ شروع رابطه جدید رو وارد کن (مثلا: 1402-05-10):")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_edit_start_date")
def save_edit_start_date_handler(message):
    uid = message.chat.id

    try:
        gdate, jdate = parse_date_input(message.text)
        new_start_date = gdate.isoformat()

        safe_execute_db(
            "UPDATE users SET start_date = ? WHERE user_id = ?", (new_start_date, uid))
        bot.send_message(
            uid, f"✅ تاریخ شروع رابطه به {jdate.year}/{jdate.month:02d}/{jdate.day:02d} تغییر کرد!")
        user_state.pop(uid, None)
        show_info_handler_simple(uid)

    except ValueError as e:
        bot.send_message(uid, f"❌ خطا در تاریخ: {str(e)}")


@bot.callback_query_handler(func=lambda call: call.data == "show_info")
def show_info_handler(call):
    """Handler نمایش اطلاعات - نسخه اصلاح شده"""
    uid = call.message.chat.id

    result = safe_execute_db("""
        SELECT gender, name, birthdate, partner_name, partner_birthdate, partner_age, 
               partner_nick, relation_type, start_date, partner_id, connection_status
        FROM users WHERE user_id = ?
    """, (uid,))

    if not result:
        bot.answer_callback_query(call.id, "❌ اطلاعاتی پیدا نشد!")
        return

    (gender, name, birthdate_g, partner_name, partner_birthdate_g,
     partner_age, partner_nick, relation_type, start_date_g, partner_id, connection_status) = result[0]

    # تبدیل تاریخ‌ها
    birthdate_j = jdatetime.date.fromgregorian(
        date=datetime.strptime(birthdate_g, "%Y-%m-%d").date())

    # ساخت متن اصلی
    text = f"""
📋 اطلاعات رابطه‌ی شما 💕

👤 اطلاعات شما:
• نام: {name}
• جنسیت: {gender}
• تولد: {birthdate_g} / {birthdate_j.year}/{birthdate_j.month:02d}/{birthdate_j.day:02d}
"""

    # بررسی وجود پارتنر
    has_partner = partner_name and partner_name != "ندارم" and partner_name != "NULL"

    if has_partner:
        try:
            partner_birthdate_j = jdatetime.date.fromgregorian(
                date=datetime.strptime(partner_birthdate_g, "%Y-%m-%d").date())
            start_date_j = jdatetime.date.fromgregorian(
                date=datetime.strptime(start_date_g, "%Y-%m-%d").date())

            relation_days = get_relation_days(
                datetime.strptime(start_date_g, "%Y-%m-%d").date())

            text += f"""
❤️ اطلاعات پارتنر:
• نام: {partner_name}
• تولد: {partner_birthdate_g} / {partner_birthdate_j.year}/{partner_birthdate_j.month:02d}/{partner_birthdate_j.day:02d}
• سن: {partner_age} سال
• لقب: {partner_nick}
"""

            # اضافه کردن حالت خلقی اگر پارتنر متصل باشد
            if partner_id and connection_status == "connected":
                partner_mood = get_partner_mood_display(partner_id)
                text += f"\n🌙 حالت خلقی امروز:\n{partner_mood}\n"

            # ادامه متن برای رابطه
            text += f"""
💑 اطلاعات رابطه:
• نوع: {relation_type}
• شروع: {start_date_g} / {start_date_j.year}/{start_date_j.month:02d}/{start_date_j.day:02d}
• روزهای گذشته: {relation_days} روز 🎉
"""
        except Exception as e:
            print(f"خطا در نمایش اطلاعات پارتنر: {e}")
            text += f"""
💔 وضعیت رابطه:
• پارتنر: {partner_name}
• نوع: {relation_type}
"""
    else:
        text += f"""
💔 وضعیت رابطه:
• پارتنر: ندارم
• نوع: {relation_type}
"""

    markup = InlineKeyboardMarkup()

    if has_partner:
        # بررسی وضعیت اتصال فقط اگر پارتنر وجود دارد
        if partner_id and connection_status:
            if connection_status == "connected":
                markup.row(InlineKeyboardButton(
                    "👤 اطلاعات پارتنر", callback_data="partner_info"))
                markup.row(InlineKeyboardButton(
                    "🥀 اتمام رابطه", callback_data="end_relation"))
            elif connection_status == "pending":
                markup.row(InlineKeyboardButton(
                    "⏳ درخواست در انتظار تایید", callback_data="pending_request"))
                markup.row(InlineKeyboardButton(
                    "❌ لغو درخواست", callback_data="cancel_request"))
            else:
                markup.row(InlineKeyboardButton(
                    "💞 اتصال به پارتنر", callback_data="connect_partner"))
        else:
            markup.row(InlineKeyboardButton(
                "💞 اتصال به پارتنر", callback_data="connect_partner"))
    else:
        # اگر پارتنر ندارد، گزینه افزودن پارتنر نمایش داده شود
        markup.row(InlineKeyboardButton(
            "💖 افزودن پارتنر", callback_data="add_partner"))

    markup.row(InlineKeyboardButton(
        "✏️ ویرایش اطلاعات", callback_data="edit_profile"))
    markup.row(InlineKeyboardButton(
        "🔙 منوی اصلی", callback_data="back_to_main"))

    try:
        bot.edit_message_text(text, uid, call.message.message_id,
                              reply_markup=markup, parse_mode="Markdown")
    except:
        bot.send_message(uid, text, reply_markup=markup, parse_mode="Markdown")


def calculate_days_until_event(event_date_str, repeat_type="yearly"):
    """محاسبه روزهای باقی‌مانده با استفاده از کد شما"""
    today = datetime.today().date()
    event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()

    if repeat_type == "yearly":
        # پیدا کردن تاریخ بعدی (سالگرد)
        next_occurrence = event_date.replace(year=today.year)
        if next_occurrence < today:
            next_occurrence = event_date.replace(year=today.year + 1)
        days_to_next = (next_occurrence - today).days
        time_info = "سالگرد بعدی"

    elif repeat_type == "monthly":
        # پیدا کردن تاریخ بعدی (ماهگرد)
        year, month = today.year, today.month
        if today.day >= event_date.day:
            # میریم ماه بعد
            if month == 12:
                year += 1
                month = 1
            else:
                month += 1
        # هندل کردن تعداد روزهای هر ماه
        last_day = calendar.monthrange(year, month)[1]
        day = min(event_date.day, last_day)
        next_occurrence = datetime(year, month, day).date()
        days_to_next = (next_occurrence - today).days
        time_info = "ماهگرد بعدی"

    elif repeat_type in ["daily", "weekly", "none"]:
        # برای تکرارهای دیگر از روش ساده استفاده می‌کنیم
        if event_date >= today:
            next_occurrence = event_date
            days_to_next = (next_occurrence - today).days
        else:
            # اگر تاریخ گذشته، تکرار بعدی رو محاسبه کن
            if repeat_type == "daily":
                days_to_next = 1  # فردا
            elif repeat_type == "weekly":
                days_to_next = 7  # هفته بعد
            else:  # none
                days_to_next = 365  # سال بعد
            next_occurrence = today + timedelta(days=days_to_next)
        time_info = "تکرار بعدی"

    else:
        # حالت پیش‌فرض
        next_occurrence = event_date.replace(year=today.year)
        if next_occurrence < today:
            next_occurrence = event_date.replace(year=today.year + 1)
        days_to_next = (next_occurrence - today).days
        time_info = "بار بعدی"

    return days_to_next, time_info, next_occurrence


def format_time_remaining(days_until, time_info):
    """فرمت‌بندی زیبا برای نمایش زمان باقی‌مانده"""
    if days_until == 0:
        return "🎉 امروز!"
    elif days_until == 1:
        return f"⏳ فردا ({time_info})"
    elif days_until <= 7:
        return f"⏳ {days_until} روز دیگر ({time_info})"
    elif days_until <= 30:
        weeks = days_until // 7
        days_in_week = days_until % 7
        if days_in_week > 0:
            return f"⏳ {days_until} روز دیگر ({time_info} - {weeks} هفته و {days_in_week} روز)"
        else:
            return f"⏳ {days_until} روز دیگر ({time_info} - {weeks} هفته)"
    else:
        months = days_until // 30
        days_in_month = days_until % 30
        if days_in_month > 0:
            return f"⏳ {days_until} روز دیگر ({time_info} - {months} ماه و {days_in_month} روز)"
        else:
            return f"⏳ {days_until} روز دیگر ({time_info} - {months} ماه)"


def sort_events_by_upcoming(events):
    """مرتب‌سازی مناسبت‌ها بر اساس نزدیک‌ترین تاریخ با استفاده از کد شما"""
    today = datetime.today().date()

    def get_sort_key(event):
        _, _, event_date_str, repeat_type = event

        # محاسبه تاریخ بعدی با استفاده از کد شما
        days_until, _, next_date = calculate_days_until_event(
            event_date_str, repeat_type)
        return next_date

    return sorted(events, key=get_sort_key)


def get_detailed_user_stats(uid):
    """دریافت آمار دقیق کاربر با مدیریت خطا"""
    try:
        conn = sqlite3.connect(
            "heart_stats.db", check_same_thread=False, timeout=10)
        cur = conn.cursor()

        cur.execute("""
            SELECT today_count, week_count, total_count, last_click_time 
            FROM heart_clicks 
            WHERE user_id = ?
        """, (uid,))

        result = cur.fetchone()
        conn.close()

        if not result:
            return {
                'today': 0,
                'week': 0,
                'total': 0,
                'last_click': 'هرگز',
                'days_since_last': 999
            }

        today, week, total, last_click_time = result

        # محاسبه روزهای گذشته از آخرین کلیک
        if last_click_time:
            last_click = datetime.fromisoformat(last_click_time)
            days_since = (datetime.now() - last_click).days
            last_click_str = last_click.strftime("%Y/%m/%d %H:%M")
        else:
            days_since = 999
            last_click_str = 'هرگز'

        return {
            'today': today,
            'week': week,
            'total': total,
            'last_click': last_click_str,
            'days_since_last': days_since
        }

    except Exception as e:
        print(f"خطا در دریافت آمار دقیق کاربر: {e}")
        return {
            'today': 0,
            'week': 0,
            'total': 0,
            'last_click': 'هرگز',
            'days_since_last': 999
        }


# Connect To Partner


@bot.callback_query_handler(func=lambda call: call.data == "connect_partner")
def connect_partner_handler(call):
    uid = call.message.chat.id
    user_state[uid] = "waiting_partner_id"

    try:
        bot.edit_message_text(
            "💞 برای اتصال به پارتنر، لطفا آیدی عددی پارتنرت رو وارد کن:",
            uid, call.message.message_id
        )
    except:
        bot.send_message(
            uid, "💞 برای اتصال به پارتنر، لطفا آیدی عددی پارتنرت رو وارد کن:")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_partner_id")
def receive_partner_id_handler(message):
    uid = message.chat.id

    try:
        partner_id = int(message.text.strip())

        if partner_id == uid:
            bot.send_message(uid, "❌ نمی‌تونی به خودت درخواست اتصال بدی!")
            user_state.pop(uid, None)
            return

        partner_exists = safe_execute_db(
            "SELECT 1 FROM users WHERE user_id = ?", (partner_id,))

        if not partner_exists:
            bot.send_message(
                uid, f"❌ کاربر با آیدی {partner_id} در ربات عضو نیست!")
            user_state.pop(uid, None)
            return

        safe_execute_db(
            "UPDATE users SET partner_id = ?, connection_status = 'pending' WHERE user_id = ?", (partner_id, uid))

        send_connection_request(uid, partner_id)

        bot.send_message(
            uid, f"✅ درخواست اتصال به کاربر با آیدی {partner_id} ارسال شد!")

        user_state.pop(uid, None)

    except ValueError:
        bot.send_message(uid, "❌ آیدی باید یک عدد باشد! لطفا دوباره وارد کن:")


def send_connection_request(sender_id, receiver_id):
    try:
        sender_info = safe_execute_db(
            "SELECT name, partner_nick FROM users WHERE user_id = ?", (sender_id,))
        if not sender_info:
            return

        sender_name, partner_nick = sender_info[0]

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton(
                "✅ قبول درخواست", callback_data=f"accept_request_{sender_id}"),
            InlineKeyboardButton(
                "❌ رد درخواست", callback_data=f"reject_request_{sender_id}")
        )

        bot.send_message(
            receiver_id,
            f"💌 درخواست اتصال جدید!\n\n👤 {sender_name} ({partner_nick}) می‌خواد با تو وصل بشه!",
            reply_markup=markup
        )
    except Exception as e:
        print(f"خطا در ارسال درخواست: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("accept_request_"))
def accept_request_handler(call):
    uid = call.message.chat.id
    sender_id = int(call.data.split("_")[2])

    request_exists = safe_execute_db(
        "SELECT 1 FROM users WHERE user_id = ? AND partner_id = ? AND connection_status = 'pending'", (sender_id, uid))

    if not request_exists:
        bot.answer_callback_query(call.id, "❌ درخواست پیدا نشد!")
        return

    safe_execute_db(
        "UPDATE users SET connection_status = 'connected', partner_id = ? WHERE user_id = ?", (uid, sender_id))
    safe_execute_db(
        "UPDATE users SET connection_status = 'connected', partner_id = ? WHERE user_id = ?", (sender_id, uid))

    bot.send_message(sender_id, "🎉 درخواست اتصالت قبول شد!")
    bot.answer_callback_query(call.id, "✅ درخواست قبول شد!")

    try:
        bot.edit_message_text("✅ درخواست اتصال قبول شد!",
                              uid, call.message.message_id)
    except:
        bot.send_message(uid, "✅ درخواست اتصال قبول شد!")


@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_request_"))
def reject_request_handler(call):
    uid = call.message.chat.id
    sender_id = int(call.data.split("_")[2])

    safe_execute_db(
        "UPDATE users SET connection_status = 'single', partner_id = NULL WHERE user_id = ?", (sender_id,))

    bot.send_message(sender_id, "❌ درخواست اتصالت رد شد.")
    bot.answer_callback_query(call.id, "❌ درخواست رد شد!")
    bot.edit_message_text("❌ درخواست اتصال رد شد.",
                          uid, call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data == "cancel_request")
def cancel_request_handler(call):
    """Handler لغو درخواست اتصال"""
    uid = call.message.chat.id

    # ریست کردن وضعیت
    safe_execute_db("UPDATE users SET connection_status = 'single', partner_id = NULL WHERE user_id = ?",
                    (uid,))

    bot.answer_callback_query(call.id, "✅ درخواست لغو شد!")
    bot.edit_message_text(
        "✅ درخواست اتصال لغو شد.",
        uid, call.message.message_id
    )


@bot.callback_query_handler(func=lambda call: call.data == "partner_info")
def partner_info_handler(call):
    """Handler نمایش اطلاعات پارتنر (موقت)"""
    uid = call.message.chat.id

    # دریافت اطلاعات پارتنر
    result = safe_execute_db("""
        SELECT u.name, u.gender, u.birthdate, u.partner_nick 
        FROM users u 
        WHERE u.user_id = (
            SELECT partner_id FROM users WHERE user_id = ? AND connection_status = 'connected'
        )
    """, (uid,))

    if not result:
        bot.answer_callback_query(call.id, "❌ اطلاعات پارتنر پیدا نشد!")
        return

    name, gender, birthdate, partner_nick = result[0]
    birthdate_j = jdatetime.date.fromgregorian(
        date=datetime.strptime(birthdate, "%Y-%m-%d").date())

    text = f"""
👤 اطلاعات پارتنر

💖 نام: {name}
⚧ جنسیت: {gender}
🎂 تولد: {birthdate} / {birthdate_j.year}/{birthdate_j.month:02d}/{birthdate_j.day:02d}
😂 لقب: {partner_nick}

💕 این رابطه‌ی زیبات رو حفظ کن!
"""

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🔙 بازگشت", callback_data="show_info"))

    try:
        bot.edit_message_text(
            text, uid, call.message.message_id, reply_markup=markup)
    except:
        bot.send_message(uid, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "end_relation")
def end_relation_handler(call):
    """Handler اتمام رابطه"""
    uid = call.message.chat.id

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ بله، رابطه تموم شد",
                             callback_data="confirm_end_relation"),
        InlineKeyboardButton("❌ خیر، بازگشت", callback_data="show_info")
    )

    try:
        bot.edit_message_text(
            "⚠️ آیا مطمئنی می‌خوای این رابطه رو به پایان برسونی؟\n\n"
            "این عمل قابل بازگشت نیست!",
            uid, call.message.message_id,
            reply_markup=markup
        )
    except:
        bot.send_message(
            uid,
            "⚠️ آیا مطمئنی می‌خوای این رابطه رو به پایان برسونی؟\n\n"
            "این عمل قابل بازگشت نیست!",
            reply_markup=markup
        )


@bot.callback_query_handler(func=lambda call: call.data == "confirm_end_relation")
def confirm_end_relation_handler(call):
    """Handler تأیید اتمام رابطه"""
    uid = call.message.chat.id

    # دریافت آیدی پارتنر
    partner_result = safe_execute_db(
        "SELECT partner_id FROM users WHERE user_id = ?", (uid,))
    if partner_result:
        partner_id = partner_result[0][0]

        # ریست کردن وضعیت هر دو کاربر
        safe_execute_db("UPDATE users SET connection_status = 'single', partner_id = NULL WHERE user_id = ?",
                        (uid,))
        safe_execute_db("UPDATE users SET connection_status = 'single', partner_id = NULL WHERE user_id = ?",
                        (partner_id,))

        # اطلاع‌رسانی به پارتنر
        bot.send_message(partner_id, "💔 متأسفانه رابطه‌تون به پایان رسید.")

    bot.answer_callback_query(call.id, "💔 رابطه به پایان رسید!")
    bot.edit_message_text(
        "💔 رابطه‌تون به پایان رسید. امیدوارم دوباره عشق رو پیدا کنی!",
        uid, call.message.message_id,
        reply_markup=main_menu()
    )
##############
#############


def secret_messages_menu():
    """منوی پیام‌های مخفی"""
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(
        "✉️ ارسال پیام مخفی", callback_data="send_secret_msg"))
    markup.row(InlineKeyboardButton("📨 پیام‌های دریافتی",
               callback_data="received_secret_msgs"))
    markup.row(InlineKeyboardButton(
        "📤 پیام‌های ارسالی", callback_data="sent_secret_msgs"))
    markup.row(InlineKeyboardButton("🚫 کاربران بلاک شده",
               callback_data="blocked_users_list"))
    markup.row(InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main"))
    return markup


@bot.callback_query_handler(func=lambda call: call.data == "secret_msgs_menu")
def secret_msgs_menu_handler(call):
    """Handler منوی پیام‌های مخفی"""
    uid = call.message.chat.id
    try:
        bot.edit_message_text(
            "💌 سیستم پیام‌های مخفی\n\n"
            "می‌تونی پیام ناشناس بفرستی یا پیام‌های دریافتی رو مدیریت کنی!",
            uid,
            call.message.message_id,
            reply_markup=secret_messages_menu()
        )
    except:
        bot.send_message(
            uid,
            "💌 سیستم پیام‌های مخفی\n\n"
            "می‌تونی پیام ناشناس بفرستی یا پیام‌های دریافتی رو مدیریت کنی!",
            reply_markup=secret_messages_menu()
        )


@bot.callback_query_handler(func=lambda call: call.data == "send_secret_msg")
def send_secret_msg_handler(call):
    """شروع فرآیند ارسال پیام مخفی"""
    uid = call.message.chat.id
    user_state[uid] = "waiting_receiver_id"

    try:
        bot.edit_message_text(
            "✉️ ارسال پیام مخفی\n\n"
            "لطفا آیدی عددی کاربری که می‌خوای براش پیام بفرستی رو وارد کن:",
            uid,
            call.message.message_id
        )
    except:
        bot.send_message(
            uid,
            "✉️ ارسال پیام مخفی\n\n"
            "لطفا آیدی عددی کاربری که می‌خوای براش پیام بفرستی رو وارد کن:"
        )


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_receiver_id")
def receive_receiver_id_handler(message):
    """دریافت آیدی گیرنده"""
    uid = message.chat.id

    try:
        receiver_id = int(message.text.strip())

        # بررسی ارسال به خود
        if receiver_id == uid:
            bot.send_message(uid, "❌ نمی‌تونی به خودت پیام بفرستی!")
            user_state.pop(uid, None)
            return

        # بررسی وجود کاربر
        receiver_exists = safe_execute_db(
            "SELECT 1 FROM users WHERE user_id = ?", (receiver_id,))
        if not receiver_exists:
            bot.send_message(uid, "❌ کاربری با این آیدی وجود نداره!")
            user_state.pop(uid, None)
            return

        # بررسی بلاک بودن
        is_blocked = check_if_blocked(uid, receiver_id)
        if is_blocked:
            bot.send_message(uid, "❌ این کاربر شما رو بلاک کرده!")
            user_state.pop(uid, None)
            return

        # بررسی آنتی اسپم
        if not can_send_message(uid):
            bot.send_message(uid, "⏳ زیاد پیام فرستادی! لطفا 1 دقیقه صبر کن.")
            user_state.pop(uid, None)
            return

        user_state[uid] = f"waiting_message_text_{receiver_id}"
        bot.send_message(
            uid, "✅ کاربر پیدا شد!\n\n💬 حالا متن پیامت رو وارد کن (حداکثر 980 کاراکتر):")

    except ValueError:
        bot.send_message(uid, "❌ آیدی باید عدد باشه! دوباره وارد کن:")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id, "").startswith("waiting_message_text_"))
def receive_message_text_handler(message):
    """دریافت متن پیام"""
    uid = message.chat.id
    state = user_state.get(uid, "")

    if not state.startswith("waiting_message_text_"):
        return

    try:
        receiver_id = int(state.split("_")[3])
        message_text = message.text.strip()

        # بررسی طول پیام
        if len(message_text) > 980:
            bot.send_message(
                uid, "❌ پیام خیلی طولانیه! حداکثر 980 کاراکتر مجاز است.")
            return

        if len(message_text) < 2:
            bot.send_message(
                uid, "❌ پیام خیلی کوتاهه! حداقل 2 کاراکتر لازم است.")
            return

        # ارسال پیام
        success = send_secret_message(uid, receiver_id, message_text)

        if success:
            bot.send_message(uid, "✅ پیامت با موفقیت ارسال شد!")
            # ارسال نوتیفیکیشن به گیرنده
            notify_receiver(receiver_id, uid)
        else:
            bot.send_message(uid, "❌ خطا در ارسال پیام!")

        user_state.pop(uid, None)

    except Exception as e:
        bot.send_message(uid, "❌ خطا در پردازش پیام!")
        user_state.pop(uid, None)


def check_if_blocked(sender_id, receiver_id):
    """بررسی اینکه آیا کاربر بلاک شده"""
    try:
        conn = sqlite3.connect("secret_messages.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM blocked_users WHERE user_id = ? AND blocked_user_id = ?",
                    (receiver_id, sender_id))
        result = cur.fetchone()
        conn.close()

        return result is not None
    except:
        return False


def can_send_message(user_id):
    """بررسی امکان ارسال پیام (آنتی اسپم)"""
    try:
        conn = sqlite3.connect("secret_messages.db", check_same_thread=False)
        cur = conn.cursor()

        now = datetime.now().isoformat()

        cur.execute("SELECT last_message_time, message_count, reset_time FROM message_stats WHERE user_id = ?",
                    (user_id,))
        result = cur.fetchone()

        if not result:
            # اولین پیام کاربر
            cur.execute("INSERT INTO message_stats (user_id, last_message_time, message_count) VALUES (?, ?, 1)",
                        (user_id, now))
            conn.commit()
            conn.close()
            return True

        last_time, count, reset_time = result
        last_time_dt = datetime.fromisoformat(last_time)
        reset_time_dt = datetime.fromisoformat(reset_time)

        # ریست شمارشگر هر دقیقه
        if (datetime.now() - reset_time_dt).total_seconds() >= 60:
            cur.execute("UPDATE message_stats SET message_count = 1, reset_time = ? WHERE user_id = ?",
                        (now, user_id))
            conn.commit()
            conn.close()
            return True

        # بررسی تعداد پیام‌ها
        if count >= 10:
            conn.close()
            return False

        # افزایش شمارشگر
        cur.execute("UPDATE message_stats SET message_count = message_count + 1, last_message_time = ? WHERE user_id = ?",
                    (now, user_id))
        conn.commit()
        conn.close()
        return True

    except:
        return True  # در صورت خطا اجازه ارسال بده


def send_secret_message(sender_id, receiver_id, message_text):
    """ارسال پیام مخفی - نسخه دیباگ شده"""
    try:
        print(f"🔧 دیباگ: تلاش برای ارسال پیام از {sender_id} به {receiver_id}")

        conn = sqlite3.connect("secret_messages.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO secret_messages (sender_id, receiver_id, message_text)
            VALUES (?, ?, ?)
        """, (sender_id, receiver_id, message_text))

        conn.commit()

        # بررسی اینکه پیام واقعاً ذخیره شده
        cur.execute("SELECT id FROM secret_messages WHERE sender_id = ? AND receiver_id = ? ORDER BY id DESC LIMIT 1",
                    (sender_id, receiver_id))
        result = cur.fetchone()

        conn.close()

        if result:
            print(Fore.LIGHTBLUE_EX +
                  f"✅ DEBUG: Messaged saved ID: {result[0]}")
            return True
        else:
            print(Fore.RED + "❌ DEBUG: MESSAGE DID NOT SAVED")
            return False

    except Exception as e:
        print(Fore.RED + f"❌DEBUG: ERROR IN SENDIG MESSAGE :  {e}")
        return False


def notify_receiver(receiver_id, sender_id):

    try:
        print(Fore.LIGHTBLUE_EX +
              f"🔧 DEBUG: Try to sending notif: {receiver_id}")

        conn = sqlite3.connect("secret_messages.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("""
            SELECT id FROM secret_messages 
            WHERE receiver_id = ? AND sender_id = ? 
            ORDER BY created_at DESC LIMIT 1
        """, (receiver_id, sender_id))

        result = cur.fetchone()
        conn.close()

        if not result:
            print(Fore.RED + "❌ DEBUG: NO MESSAGE FIND TO SENDING")
            return

        msg_id = result[0]
        print(Fore.LIGHTBLUE_EX + f"✅ DEBUG: MESSAGE FOUND ID: {msg_id}")

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton(
                "📨 مشاهده پیام", callback_data=f"view_secret_msg_{msg_id}"),
            InlineKeyboardButton(
                "🚫 بلاک کاربر", callback_data=f"block_user_{sender_id}")
        )

        bot.send_message(
            receiver_id,
            "🔐 یک پیام مخفی جدید دریافت کردی!",
            reply_markup=markup
        )
        print(f"✅ دیباگ: نوتیفیکیشن ارسال شد به {receiver_id}")

    except Exception as e:
        print(f"❌ دیباگ: خطا در نوتیفیکیشن: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("view_secret_msg_"))
def view_secret_msg_handler(call):
    """نمایش پیام مخفی برای گیرنده - با دکمه بلاک در منوی اصلی"""
    uid = call.message.chat.id

    try:
        msg_id = int(call.data.split("_")[3])

        conn = sqlite3.connect("secret_messages.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("""
            SELECT id, sender_id, message_text, created_at 
            FROM secret_messages 
            WHERE id = ? AND receiver_id = ?
        """, (msg_id, uid))

        result = cur.fetchone()

        if not result:
            bot.answer_callback_query(call.id, "❌ پیام پیدا نشد!")
            return

        msg_id, sender_id, message_text, created_at = result

        # مارک کردن پیام به عنوان خوانده شده
        cur.execute(
            "UPDATE secret_messages SET is_read = TRUE WHERE id = ?", (msg_id,))
        conn.commit()
        conn.close()

        created_dt = datetime.fromisoformat(created_at)
        created_str = created_dt.strftime("%Y/%m/%d %H:%M")

        text = f"""
🔐 پیام مخفی دریافت کردید!

💬 متن پیام:
{message_text}

⏰ زمان ارسال: {created_str}

👤 فرستنده: ناشناس
"""

        # ✅ اضافه کردن دکمه بلاک به منوی اصلی
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton(
                "🔁 پاسخ دادن", callback_data=f"secret_reply_{msg_id}"),
            InlineKeyboardButton("💞 ارسال به پارتنر",
                                 callback_data=f"secret_forward_{msg_id}")
        )
        markup.row(
            InlineKeyboardButton(
                "🚫 بلاک کاربر", callback_data=f"block_user_{sender_id}"),
            InlineKeyboardButton(
                "❌ حذف پیام", callback_data=f"secret_delete_{msg_id}")
        )
        markup.row(
            InlineKeyboardButton(
                "🔙 بازگشت", callback_data="received_secret_msgs")
        )

        try:
            bot.edit_message_text(
                text,
                uid,
                call.message.message_id,
                reply_markup=markup
            )
        except:
            bot.send_message(uid, text, reply_markup=markup)

    except Exception as e:
        print(f"خطا در مشاهده پیام: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در نمایش پیام!")


def check_if_partner(user_id, potential_partner_id):
    """بررسی اینکه آیا کاربر پارتنر هست - نسخه بهبود یافته"""
    try:
        result = safe_execute_db(
            "SELECT partner_id FROM users WHERE user_id = ?", (user_id,))
        if result and result[0][0] == potential_partner_id:
            return True
        return False
    except Exception as e:
        print(f"خطا در بررسی پارتنر: {e}")
        return False


def notify_receiver(receiver_id, sender_id, message_type="پیام جدید"):
    """ارسال نوتیفیکیشن به گیرنده - بدون دکمه بلاک"""
    try:
        print(f"🔔 نوتیفیکیشن: {receiver_id} <- {sender_id} ({message_type})")

        conn = sqlite3.connect("secret_messages.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("""
            SELECT id FROM secret_messages 
            WHERE receiver_id = ? AND sender_id = ? 
            ORDER BY created_at DESC LIMIT 1
        """, (receiver_id, sender_id))

        result = cur.fetchone()
        conn.close()

        if not result:
            print("❌ پیامی برای نوتیفیکیشن پیدا نشد!")
            return

        msg_id = result[0]

        # پیام‌های مختلف برای انواع مختلف
        messages = {
            "پیام جدید": "🔐 یک پیام مخفی جدید دریافت کردی!",
            "پاسخ": "💌 به پاسخت پاسخ دادن!",
            "فوروارد": "📩 یه پیام برات فوروارد شده!"
        }

        message_text = messages.get(message_type, "🔔 پیام جدید داری!")

        # ✅ فقط دکمه مشاهده پیام - حذف دکمه بلاک
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton(
                "📨 مشاهده پیام", callback_data=f"view_secret_msg_{msg_id}")
        )

        bot.send_message(receiver_id, message_text, reply_markup=markup)
        print(f"✅ نوتیفیکیشن ارسال شد: {message_type}")

    except Exception as e:
        print(f"❌ خطا در نوتیفیکیشن: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("block_secret_"))
def block_secret_handler(call):
    """بلاک کردن کاربر عادی (غیر پارتنر)"""
    uid = call.message.chat.id

    try:
        blocked_user_id = int(call.data.split("_")[2])

        # بررسی مجدد که پارتنر نباشه
        if check_if_partner(uid, blocked_user_id):
            block_partner_joke_handler(call)
            return

        conn = sqlite3.connect("secret_messages.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("""
            INSERT OR IGNORE INTO blocked_users (user_id, blocked_user_id) 
            VALUES (?, ?)
        """, (uid, blocked_user_id))

        conn.commit()
        conn.close()

        bot.answer_callback_query(call.id, "✅ کاربر بلاک شد!")

        try:
            bot.edit_message_text(
                "✅ کاربر با موفقیت بلاک شد!\n\n"
                "این کاربر دیگه نمی‌تونه برات پیام بفرسته.",
                uid,
                call.message.message_id
            )
        except:
            bot.send_message(uid, "✅ کاربر با موفقیت بلاک شد!")

    except Exception as e:
        print(f"خطا در بلاک کردن: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در بلاک کردن!")


@bot.callback_query_handler(func=lambda call: call.data.startswith("block_partner_joke_"))
def block_partner_joke_handler(call):
    """پیام طنز وقتی کاربر می‌خواد پارتنرش رو بلاک کنه"""
    uid = call.message.chat.id

    try:
        partner_id = int(call.data.split("_")[3])

        # دریافت جنسیت کاربر برای شخصی‌سازی پیام
        result = safe_execute_db(
            "SELECT gender FROM users WHERE user_id = ?", (uid,))
        gender = result[0][0] if result else "مرد"

        if gender == "زن":
            title = "خانم"
        else:
            title = "آقا"

        text = f"""
😂😂 **اع! فک کردی اینجام اینستا و تلگرامه؟**

{title} گل {get_random_emoji()} بزاریم عشقتو بلاک کنی؟ 😂

نه قربونت بشم، اینجا نمیتونیم پارتنر رو بلاک کنیم!

💕 **پیشنهاد ما:** 
بهش یه پیام محبت‌آمیز بفرست و بگو دوسش داری! {get_random_heart()}
"""

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("💖 بفرست بگو دوستش دارم",
                                 callback_data=f"send_love_{partner_id}"),
            InlineKeyboardButton(
                "🔙 برگشت", callback_data="received_secret_msgs")
        )

        bot.answer_callback_query(call.id, "😂 نه بابا نمیشه!")

        try:
            bot.edit_message_text(
                text,
                uid,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except:
            bot.send_message(uid, text, reply_markup=markup,
                             parse_mode="Markdown")

    except Exception as e:
        print(f"خطا در handler بلاک طنز: {e}")
        bot.answer_callback_query(call.id, "😂 پارتنرت رو که نمیشه بلاک کرد!")


def get_random_emoji():
    """ایموجی رندوم برای پیام طنز"""
    emojis = ["✨", "🌟", "🎭", "👀", "🎪", "🤡", "💫"]
    return random.choice(emojis)


def get_random_heart():
    """قلب رندوم"""
    hearts = ["💕", "💖", "💗", "💓", "💞", "💘", "💝"]
    return random.choice(hearts)


@bot.callback_query_handler(func=lambda call: call.data.startswith("send_love_"))
def send_love_handler(call):
    """ارسال پیام عشق به پارتنر"""
    uid = call.message.chat.id

    try:
        partner_id = int(call.data.split("_")[2])

        love_messages = [
            "عزیزم دوست دارم 💖",
            "نکنه ناراحتت کردم؟ ببخشیدم 😔",
            "تو بهترین چیزی هستی که برام اتفاق افتاده 🌟",
            "همیشه دنبالت میام، ولت نمیکنم! 💕",
            "بیا آشتی کنیم 🤗",
            "بدون تو دنیام رنگ نداره 🌈",
            "عشقم همیشه مال تو میمونه 💘"
        ]

        love_message = random.choice(love_messages)

        # ارسال پیام به پارتنر
        send_secret_message(uid, partner_id, love_message)
        notify_receiver(receiver_id, sender_id, "پیام جدید")

        bot.answer_callback_query(call.id, "💖 پیام عشق فرستاده شد!")

        try:
            bot.edit_message_text(
                f"✅ پیامت براش فرستاده شد:\n\n"
                f"💌 *{love_message}*\n\n"
                f"حالا برو یه کار دیگه بکن! 😉",
                uid,
                call.message.message_id,
                parse_mode="Markdown"
            )
        except:
            bot.send_message(
                uid,
                f"✅ پیامت براش فرستاده شد:\n\n💌 {love_message}",
                parse_mode="Markdown"
            )

    except Exception as e:
        print(f"خطا در ارسال عشق: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در ارسال پیام!")


@bot.callback_query_handler(func=lambda call: call.data == "received_secret_msgs")
def received_secret_msgs_handler(call):
    """نمایش پیام‌های دریافتی با قابلیت حذف"""
    uid = call.message.chat.id

    try:
        conn = sqlite3.connect("secret_messages.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("""
            SELECT id, sender_id, message_text, created_at, is_read 
            FROM secret_messages 
            WHERE receiver_id = ? 
            ORDER BY created_at DESC LIMIT 10
        """, (uid,))

        messages = cur.fetchall()
        conn.close()

        if not messages:
            text = "📭 هنوز هیچ پیام دریافتی نداشتی!"
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton(
                "🔙 بازگشت", callback_data="secret_msgs_menu"))
        else:
            text = "📨 **پیام‌های دریافتی تو:**\n\n"
            markup = InlineKeyboardMarkup()

            for msg_id, sender_id, message_text, created_at, is_read in messages:
                status = "✅" if is_read else "🔴"
                preview = message_text[:30] + \
                    "..." if len(message_text) > 30 else message_text
                created_dt = datetime.fromisoformat(created_at)
                created_str = created_dt.strftime("%m/%d %H:%M")

                text += f"{status} `{preview}` - {created_str}\n"

                # اضافه کردن دکمه‌های اقدام برای هر پیام
                markup.row(
                    InlineKeyboardButton(
                        f"👀 مشاهده {msg_id}", callback_data=f"view_secret_msg_{msg_id}"),
                    InlineKeyboardButton(
                        f"🗑️ حذف {msg_id}", callback_data=f"secret_delete_{msg_id}")
                )

            markup.row(InlineKeyboardButton(
                "🔙 بازگشت", callback_data="secret_msgs_menu"))

        try:
            bot.edit_message_text(
                text,
                uid,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except:
            bot.send_message(uid, text, reply_markup=markup,
                             parse_mode="Markdown")

    except Exception as e:
        print(f"خطا در نمایش پیام‌های دریافتی: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در نمایش پیام‌ها!")


@bot.callback_query_handler(func=lambda call: call.data == "sent_secret_msgs")
def sent_secret_msgs_handler(call):
    """نمایش پیام‌های ارسالی با قابلیت حذف"""
    uid = call.message.chat.id

    try:
        conn = sqlite3.connect("secret_messages.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("""
            SELECT id, receiver_id, message_text, created_at 
            FROM secret_messages 
            WHERE sender_id = ? 
            ORDER BY created_at DESC LIMIT 10
        """, (uid,))

        messages = cur.fetchall()
        conn.close()

        if not messages:
            text = "📤 هنوز هیچ پیامی نفرستادی!"
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton(
                "🔙 بازگشت", callback_data="secret_msgs_menu"))
        else:
            text = "📤 **پیام‌های ارسالی تو:**\n\n"
            markup = InlineKeyboardMarkup()

            for msg_id, receiver_id, message_text, created_at in messages:
                preview = message_text[:30] + \
                    "..." if len(message_text) > 30 else message_text
                created_dt = datetime.fromisoformat(created_at)
                created_str = created_dt.strftime("%m/%d %H:%M")

                text += f"➡️ `{preview}` - {created_str}\n"

                # اضافه کردن دکمه حذف برای هر پیام
                markup.row(
                    InlineKeyboardButton(
                        f"🗑️ حذف {msg_id}", callback_data=f"delete_sent_msg_{msg_id}"),
                    InlineKeyboardButton(
                        f"👀 مشاهده {msg_id}", callback_data=f"view_sent_msg_{msg_id}")
                )

            markup.row(InlineKeyboardButton(
                "🔙 بازگشت", callback_data="secret_msgs_menu"))

        try:
            bot.edit_message_text(
                text,
                uid,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except:
            bot.send_message(uid, text, reply_markup=markup,
                             parse_mode="Markdown")

    except Exception as e:
        print(f"خطا در نمایش پیام‌های ارسالی: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در نمایش پیام‌ها!")


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_sent_msg_"))
def delete_sent_msg_handler(call):
    """حذف پیام ارسالی"""
    uid = call.message.chat.id

    try:
        msg_id = int(call.data.split("_")[3])

        conn = sqlite3.connect("secret_messages.db", check_same_thread=False)
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM secret_messages WHERE id = ? AND sender_id = ?", (msg_id, uid))
        deleted_count = cur.rowcount
        conn.commit()
        conn.close()

        if deleted_count > 0:
            bot.answer_callback_query(call.id, "✅ پیام حذف شد!")
            # بازگشت به لیست پیام‌های ارسالی
            sent_secret_msgs_handler(call)
        else:
            bot.answer_callback_query(call.id, "❌ پیام پیدا نشد!")

    except Exception as e:
        print(f"خطا در حذف پیام ارسالی: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در حذف!")


@bot.callback_query_handler(func=lambda call: call.data == "blocked_users_list")
def blocked_users_list_handler(call):
    """نمایش کاربران بلاک شده با فرمت جدید"""
    uid = call.message.chat.id

    try:
        conn = sqlite3.connect("secret_messages.db", check_same_thread=False)
        cur = conn.cursor()

        # دریافت لیست کاربران بلاک شده با اطلاعات پیام
        cur.execute("""
            SELECT bu.id, bu.blocked_user_id, bu.created_at,
                   sm.message_text
            FROM blocked_users bu
            LEFT JOIN secret_messages sm ON bu.blocked_user_id = sm.sender_id 
                AND sm.receiver_id = bu.user_id
            WHERE bu.user_id = ?
            GROUP BY bu.id
        """, (uid,))

        blocked_users = cur.fetchall()
        conn.close()

        if not blocked_users:
            text = "🚫 هیچ کاربری را بلاک نکرده‌اید!"
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton(
                "🔙 بازگشت", callback_data="secret_msgs_menu"))
        else:
            text = "🚫 **کاربران بلاک شده:**\n\n"
            markup = InlineKeyboardMarkup()

            for block_id, blocked_user_id, created_at, message_text in blocked_users:
                # فرمت تاریخ
                created_dt = datetime.fromisoformat(created_at)
                created_str = created_dt.strftime("%Y/%m/%d")

                # ایجاد شناسه مخفی (14 کاراکتر اول آخرین پیام)
                if message_text:
                    hidden_id = message_text[:14] + \
                        "..." if len(message_text) > 14 else message_text
                else:
                    hidden_id = "کاربر ناشناس"

                text += f"• `{hidden_id}` - {created_str}\n"

                # اضافه کردن دکمه آنبلاک
                markup.row(
                    InlineKeyboardButton(
                        f"🔓 آنبلاک {hidden_id[:8]}...", callback_data=f"unblock_user_{block_id}")
                )

            markup.row(InlineKeyboardButton(
                "🔙 بازگشت", callback_data="secret_msgs_menu"))

        try:
            bot.edit_message_text(
                text,
                uid,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except:
            bot.send_message(uid, text, reply_markup=markup,
                             parse_mode="Markdown")

    except Exception as e:
        print(f"خطا در نمایش کاربران بلاک شده: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در نمایش لیست!")


def show_partner_block_joke(uid, partner_id):
    """نمایش پیام طنز هنگام تلاش برای بلاک پارتنر"""
    try:
        # دریافت اطلاعات کاربر برای شخصی‌سازی پیام
        result = safe_execute_db(
            "SELECT gender, partner_nick FROM users WHERE user_id = ?", (uid,))
        if result:
            gender, partner_nick = result[0]
            title = "خانم" if gender == "زن" else "آقا"
        else:
            title = "عزیز"
            partner_nick = "پارتنرت"

        emojis = ["😂", "🤣", "😅", "🎭", "👀", "💫"]
        hearts = ["💖", "💕", "💗", "💓", "💞"]

        text = f"""
{random.choice(emojis)} **اوه! فکر کردی کجایی؟!**

{title} گل {random.choice(emojis)} می‌خوای {partner_nick} رو بلاک کنی؟! {random.choice(emojis)}

اینجا جای عشق هاست، نه بلاک کردن عشاق! {random.choice(hearts)}

**به جاش برو یه پیام محبت‌آمیز براش بفرست:** {random.choice(hearts)}
"""

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton(
                f"{random.choice(hearts)} بفرست بگو دوستش دارم", callback_data=f"send_love_{partner_id}"),
            InlineKeyboardButton(
                "🔙 برگشت", callback_data="received_secret_msgs")
        )

        bot.send_message(uid, text, reply_markup=markup, parse_mode="Markdown")

    except Exception as e:
        print(f"خطا در نمایش پیام طنز: {e}")
        bot.send_message(uid, "😂 نه بابا، پارتنرت رو که نمیشه بلاک کرد!")


@bot.callback_query_handler(func=lambda call: call.data.startswith("block_user_"))
def block_user_handler(call):
    """Handler بلاک کردن کاربر - نسخه نهایی"""
    uid = call.message.chat.id

    try:
        blocked_user_id = int(call.data.split("_")[2])

        # بررسی اینکه پارتنر نباشد
        if check_if_partner(uid, blocked_user_id):
            # نمایش پیام طنز برای پارتنر
            show_partner_block_joke(uid, blocked_user_id)
            return

        # بررسی اینکه قبلاً بلاک نشده
        conn = sqlite3.connect("secret_messages.db", check_same_thread=False)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM blocked_users WHERE user_id = ? AND blocked_user_id = ?",
                    (uid, blocked_user_id))

        if cur.fetchone():
            bot.answer_callback_query(call.id, "✅ کاربر قبلاً بلاک شده!")
            conn.close()
            return

        # بلاک کردن کاربر
        cur.execute("INSERT INTO blocked_users (user_id, blocked_user_id) VALUES (?, ?)",
                    (uid, blocked_user_id))
        conn.commit()
        conn.close()

        bot.answer_callback_query(call.id, "✅ کاربر بلاک شد!")

        # بازگشت به لیست پیام‌ها
        received_secret_msgs_handler(call)

    except Exception as e:
        print(f"خطا در بلاک کردن: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در بلاک کردن!")


def show_partner_block_joke(uid, partner_id):
    """نمایش پیام طنز هنگام تلاش برای بلاک پارتنر"""
    try:
        # دریافت اطلاعات کاربر برای شخصی‌سازی پیام
        result = safe_execute_db(
            "SELECT gender, partner_nick FROM users WHERE user_id = ?", (uid,))
        if result:
            gender, partner_nick = result[0]
            title = "خانم" if gender == "زن" else "آقا"
        else:
            title = "عزیز"
            partner_nick = "پارتنرت"

        emojis = ["😂", "🤣", "😅", "🎭", "👀", "💫"]
        hearts = ["💖", "💕", "💗", "💓", "💞"]

        text = f"""
{random.choice(emojis)} **اوه! فکر کردی کجایی؟!**

{title} گل {random.choice(emojis)} می‌خوای {partner_nick} رو بلاک کنی؟! {random.choice(emojis)}

اینجا جای عشق هاست، نه بلاک کردن عشاق! {random.choice(hearts)}

**به جاش برو یه پیام محبت‌آمیز براش بفرست:** {random.choice(hearts)}
"""

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton(
                f"{random.choice(hearts)} بفرست بگو دوستش دارم", callback_data=f"send_love_{partner_id}"),
            InlineKeyboardButton("🔙 برگشت به پیام‌ها",
                                 callback_data="received_secret_msgs")
        )

        bot.send_message(uid, text, reply_markup=markup, parse_mode="Markdown")

    except Exception as e:
        print(f"خطا در نمایش پیام طنز: {e}")
        bot.send_message(uid, "😂 نه بابا، پارتنرت رو که نمیشه بلاک کرد!")


# اصلاح تمام callback_data های پیام مخفی با پیشوند مشخص
@bot.callback_query_handler(func=lambda call: call.data.startswith("secret_reply_"))
def secret_reply_handler(call):
    """پاسخ دادن به پیام مخفی"""
    uid = call.message.chat.id

    try:
        msg_id = int(call.data.split("_")[2])
        user_state[uid] = f"secret_reply_{msg_id}"

        bot.answer_callback_query(call.id, "💬 متن پاسخ رو وارد کن...")
        bot.send_message(uid, "💬 متن پاسخ رو وارد کن:")

    except Exception as e:
        print(f"خطا در پاسخ دادن: {e}")
        bot.answer_callback_query(call.id, "❌ خطا!")


@bot.callback_query_handler(func=lambda call: call.data.startswith("secret_forward_"))
def secret_forward_handler(call):
    """ارسال پیام به پارتنر"""
    uid = call.message.chat.id

    try:
        msg_id = int(call.data.split("_")[2])

        result = safe_execute_db(
            "SELECT partner_id FROM users WHERE user_id = ?", (uid,))
        if not result or not result[0][0]:
            bot.answer_callback_query(call.id, "❌ پارتنری نداری که!")
            return

        partner_id = result[0][0]

        conn = sqlite3.connect("secret_messages.db", check_same_thread=False)
        cur = conn.cursor()
        cur.execute(
            "SELECT message_text FROM secret_messages WHERE id = ?", (msg_id,))
        result = cur.fetchone()
        conn.close()

        if not result:
            bot.answer_callback_query(call.id, "❌ پیام پیدا نشد!")
            return

        message_text = result[0]

        success = send_secret_message(
            uid, partner_id, f"🔁 فوروارد شده:\n\n{message_text}")

        if success:
            bot.answer_callback_query(call.id, "✅ برا پارتنرت فرستادم!")
            notify_receiver(partner_id, uid, "فوروارد")
        else:
            bot.answer_callback_query(call.id, "❌ خطا در ارسال!")

    except Exception as e:
        print(f"خطا در فوروارد: {e}")
        bot.answer_callback_query(call.id, "❌ خطا!")


@bot.callback_query_handler(func=lambda call: call.data.startswith("secret_delete_"))
def secret_delete_handler(call):
    """حذف پیام مخفی"""
    uid = call.message.chat.id

    try:
        msg_id = int(call.data.split("_")[2])

        conn = sqlite3.connect("secret_messages.db", check_same_thread=False)
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM secret_messages WHERE id = ? AND receiver_id = ?", (msg_id, uid))
        conn.commit()
        conn.close()

        bot.answer_callback_query(call.id, "✅ پیام حذف شد!")

        received_secret_msgs_handler(call)

    except Exception as e:
        print(f"خطا در حذف پیام: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در حذف!")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id, "").startswith("secret_reply_"))
def secret_reply_text_handler(message):
    """دریافت متن پاسخ"""
    uid = message.chat.id
    state = user_state.get(uid, "")

    if not state.startswith("secret_reply_"):
        return

    try:
        msg_id = int(state.split("_")[2])
        reply_text = message.text.strip()

        if len(reply_text) < 2:
            bot.send_message(uid, "❌ پیام خیلی کوتاهه!")
            return

        conn = sqlite3.connect("secret_messages.db", check_same_thread=False)
        cur = conn.cursor()
        cur.execute(
            "SELECT sender_id FROM secret_messages WHERE id = ?", (msg_id,))
        result = cur.fetchone()

        if not result:
            bot.send_message(uid, "❌ پیام اصلی پیدا نشد!")
            user_state.pop(uid, None)
            return

        original_sender = result[0]

        success = send_secret_message(
            uid, original_sender, f"🔁 پاسخ:\n\n{reply_text}")

        if success:
            bot.send_message(uid, "✅ پاسخت ارسال شد!")
            notify_receiver(original_sender, uid, "پاسخ")
        else:
            bot.send_message(uid, "❌ خطا در ارسال پاسخ!")

        user_state.pop(uid, None)

    except Exception as e:
        print(f"خطا در ارسال پاسخ: {e}")
        bot.send_message(uid, "❌ خطا در ارسال پاسخ!")
        user_state.pop(uid, None)


def notify_receiver(receiver_id, sender_id, message_type="پیام جدید"):
    """ارسال نوتیفیکیشن به گیرنده - نسخه اصلاح شده"""
    try:
        print(f"🔔 نوتیفیکیشن: {receiver_id} <- {sender_id} ({message_type})")

        conn = sqlite3.connect("secret_messages.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("""
            SELECT id FROM secret_messages 
            WHERE receiver_id = ? AND sender_id = ? 
            ORDER BY created_at DESC LIMIT 1
        """, (receiver_id, sender_id))

        result = cur.fetchone()
        conn.close()

        if not result:
            print("❌ پیامی برای نوتیفیکیشن پیدا نشد!")
            return

        msg_id = result[0]

        messages = {
            "پیام جدید": "🔐 یک پیام مخفی جدید دریافت کردی!",
            "پاسخ": "💌 به پاسخت پاسخ دادن!",
            "فوروارد": "📩 یه پیام برات فوروارد شده!"
        }

        message_text = messages.get(message_type, "🔔 پیام جدید داری!")

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton(
                "📨 مشاهده پیام", callback_data=f"view_secret_msg_{msg_id}"),
            InlineKeyboardButton(
                "🚫 بلاک کاربر", callback_data=f"block_user_{sender_id}")
        )

        bot.send_message(receiver_id, message_text, reply_markup=markup)
        print(f"✅ نوتیفیکیشن ارسال شد: {message_type}")

    except Exception as e:
        print(f"❌ خطا در نوتیفیکیشن: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("view_sent_msg_"))
def view_sent_msg_handler(call):

    uid = call.message.chat.id

    try:
        msg_id = int(call.data.split("_")[3])

        conn = sqlite3.connect("secret_messages.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("""
            SELECT receiver_id, message_text, created_at 
            FROM secret_messages 
            WHERE id = ? AND sender_id = ?
        """, (msg_id, uid))

        result = cur.fetchone()
        conn.close()

        if not result:
            bot.answer_callback_query(call.id, "❌ پیام پیدا نشد!")
            return

        receiver_id, message_text, created_at = result
        created_dt = datetime.fromisoformat(created_at)
        created_str = created_dt.strftime("%Y/%m/%d %H:%M")

        text = f"""
📤 **پیام ارسالی تو:**

👤 **به آیدی:** `{receiver_id}`
⏰ **زمان ارسال:** {created_str}

💬 **متن پیام:**
{message_text}
"""

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton(
                "🗑️ حذف این پیام", callback_data=f"delete_sent_msg_{msg_id}"),
            InlineKeyboardButton("🔙 بازگشت به لیست",
                                 callback_data="sent_secret_msgs")
        )

        try:
            bot.edit_message_text(
                text,
                uid,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except:
            bot.send_message(uid, text, reply_markup=markup,
                             parse_mode="Markdown")

    except Exception as e:
        print(f"خطا در مشاهده پیام ارسالی: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در نمایش پیام!")


@bot.callback_query_handler(func=lambda call: call.data.startswith("send_love_"))
def send_love_handler(call):
    uid = call.message.chat.id

    try:
        partner_id = int(call.data.split("_")[2])

        love_messages = [
            "عزیزم دوست دارم 💖",
            "نکنه ناراحتت کردم؟ ببخشیدم 😔",
            "تو بهترین چیزی هستی که برام اتفاق افتاده 🌟",
            "همیشه دنبالت میام، ولت نمیکنم! 💕",
            "بیا آشتی کنیم 🤗",
            "بدون تو دنیام رنگ نداره 🌈",
            "عشقم همیشه مال تو میمونه 💘"
        ]

        love_message = random.choice(love_messages)

        success = send_secret_message(uid, partner_id, love_message)

        if success:

            notify_receiver(partner_id, uid, "پیام جدید")
            bot.answer_callback_query(call.id, "💖 پیام عشق فرستاده شد!")

            try:
                bot.edit_message_text(
                    f"✅ پیامت براش فرستاده شد:\n\n"
                    f"💌 *{love_message}*\n\n"
                    f"حالا برو یه کار دیگه بکن! 😉",
                    uid,
                    call.message.message_id,
                    parse_mode="Markdown"
                )
            except:
                bot.send_message(
                    uid,
                    f"✅ پیامت براش فرستاده شد:\n\n💌 {love_message}",
                    parse_mode="Markdown"
                )
        else:
            bot.answer_callback_query(call.id, "❌ خطا در ارسال پیام!")

    except Exception as e:
        print(f"خطا در ارسال عشق: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در ارسال پیام!")

###########
###########
##########


MOOD_CATEGORIES = {
    "happy": {
        "name": "شاد و سرحال",
        "emoji": "😊",
        "messages": [
            "امروز حالش فوق‌العاده‌ست، بهترین موقع برای خوشگذرونی! 🎉",
            "انرژی مثبتش رو غنیمت بشمار، روز پرانرژی‌ای داره! ✨",
            "حالش خوبه، فرصت مناسبی برای برنامه‌های شاد! 🌟"
        ]
    },
    "romantic": {
        "name": "عاشقانه و محبت‌طلب",
        "emoji": "💖",
        "messages": [
            "دلش پر از عشقه و منتظر توجه توست 🌹",
            "امروز حال عاشقانه‌ای داره، فرصت رو غنیمت بشمار 💕",
            "قلبش برای تو میتپه، با محبت پاسخش بده 💘"
        ]
    },
    "calm": {
        "name": "آرام و ریلکس",
        "emoji": "😌",
        "messages": [
            "امروز در آرامش کامله، فضای مناسبی برای گفتگوهای عمیق ☁️",
            "حالش آرومه، موقعیت خوبی برای صحبت‌های heart-to-heart 🌿",
            "در آرامشه، می‌تونی در مورد آرزوها صحبت کنی 🌼"
        ]
    },
    "sad": {
        "name": "غمگین و دلگیر",
        "emoji": "😔",
        "messages": [
            "پارتنرت امروز ناراحته، کنارش باش و درکش کن 🤗",
            "حالش گرفته، نیاز به حمایت و همدلی داره 💙",
            "امروز دلش شکسته، با محبت بهش آرامش بده 🌧️"
        ]
    },
    "stressed": {
        "name": "استرس و فشار",
        "emoji": "😫",
        "messages": [
            "پارتنرت امروز استرس داره، فضای شخصی بهش بده 🌪️",
            "حالش شلوغه، فشار اضافی وارد نکن ⚡",
            "تحت فشاره، بهش استراحت و آرامش پیشنهاد بده 🌀"
        ]
    },
    "energetic": {
        "name": "پرانرژی و ماجراجو",
        "emoji": "🔥",
        "messages": [
            "پارتنرت امروز پر از انرژی‌ست، از این فرصت برای ماجراجویی استفاده کن! ⚡",
            "حالش برای چالش‌های جدید آماده‌ست، با هم فعالیت جدید شروع کنید! 🚀",
            "پر از انگیزه‌ست، بهترین موقع برای ورزش و تحرک! 💪"
        ]
    },
    "focused": {
        "name": "متمرکز و جدی",
        "emoji": "🎯",
        "messages": [
            "پارتنرت امروز روی کارش متمرکزه، حواسش پرت نکن 🎯",
            "در حال کار مهمیه، حمایتش کن و فضای کار بهش بده 📚",
            "روی هدفش تمرکز داره، پشتیبانش باش! 🔥"
        ]
    },
    "thoughtful": {
        "name": "فکور و درون‌گرا",
        "emoji": "🤔",
        "messages": [
            "پارتنرت امروز در حال تأمل و تفکره، فضای فکری بهش بده 💭",
            "در حال فکرهای عمیقه،尊重 فضای شخصیش 🌌",
            "داره به مسائل مهم فکر می‌کنه، مزاحمش نشو 🧠"
        ]
    },
    "playful": {
        "name": "شوخ و بامزه",
        "emoji": "🎪",
        "messages": [
            "پارتنرت امروز حال مسخره‌بازی داره، با هم بخندید! 😂",
            "حالش برای شوخی و خنده آماده‌ست، همراهیش کن! 🎭",
            "امروز حال شوخیه، بهترین موقع برای تفریحات بامزه! 🤡"
        ]
    },
    "sensitive": {
        "name": "عاطفی و حساس",
        "emoji": "🌸",
        "messages": [
            "پارتنرت امروز حساست، با ملایمت رفتار کن 🌸",
            "احساساتش سطحیه، مراقب کلماتت باش 💐",
            "امروز دل نازکیه، با محبت برخورد کن 🌹"
        ]
    },
    "determined": {
        "name": "مصمم و قوی",
        "emoji": "💪",
        "messages": [
            "پارتنرت امروز مصمم و قدرتمنده، پشتیبانش باش! 💪",
            "اراده قوی داره، تشویقش کن و حمایتش کن! 🔥",
            "برای هدفش مصممه، همراهیش کن! 🚀"
        ]
    },
    "tired": {
        "name": "خسته و کم‌انرژی",
        "emoji": "🛌",
        "messages": [
            "پارتنرت امروز خسته‌ست، بهش استراحت بده 🌙",
            "انرژی کمی داره، فشار نیار و بهش آرامش بده 😴",
            "خسته‌ست، پیشنهاد استراحت یا ماساژ آرام بده 💤"
        ]
    }
}


@bot.callback_query_handler(func=lambda call: call.data == "mood_tracker")
def mood_tracker_handler(call):
    """منوی اصلی حالت خلقی با چیدمان 3×4"""
    uid = call.message.chat.id

    markup = InlineKeyboardMarkup()

    # لیست تمام حالت‌ها
    moods = list(MOOD_CATEGORIES.items())

    # چیدمان 3 تایی در 4 ردیف
    for i in range(0, len(moods), 3):
        row = []
        # اضافه کردن 3 حالت در هر ردیف
        for j in range(3):
            if i + j < len(moods):
                mood_key, mood_data = moods[i + j]
                row.append(InlineKeyboardButton(
                    f"{mood_data['emoji']} {mood_data['name']}",
                    callback_data=f"mood_{mood_key}"
                ))

        markup.row(*row)

    markup.row(InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main"))

    try:
        bot.edit_message_text(
            "🌙 امروز حالت چطوریه، عزیزم؟\n\n"
            "یکی از حالت‌های زیر رو انتخاب کن:",
            uid, call.message.message_id,
            reply_markup=markup
        )
    except:
        bot.send_message(
            uid,
            "🌙 امروز حالت چطوریه، عزیزم？\n\n"
            "یکی از حالت‌های زیر رو انتخاب کن:",
            reply_markup=markup
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("mood_"))
def mood_selection_handler(call):
    """مدیریت انتخاب حالت خلقی"""
    uid = call.message.chat.id
    mood_key = call.data.split("_")[1]

    if mood_key not in MOOD_CATEGORIES:
        bot.answer_callback_query(call.id, "❌ حالت نامعتبر!")
        return

    mood_data = MOOD_CATEGORIES[mood_key]

    # ذخیره حالت موقت
    if uid not in temp_data:
        temp_data[uid] = {}
    temp_data[uid]["current_mood"] = mood_key
    user_state[uid] = "waiting_mood_message"

    # زمان‌بندی برای لغو خودکار
    def cancel_mood_message(user_id):
        if user_state.get(user_id) == "waiting_mood_message":
            user_state.pop(user_id, None)
            temp_data.pop(user_id, None)
            bot.send_message(user_id, "⏰ زمان ثبت پیام ویژه به پایان رسید.")

    # تنظیم تایمر 20 ثانیه
    threading.Timer(20.0, cancel_mood_message, [uid]).start()

    try:
        bot.edit_message_text(
            f"✅ حالت تو: {mood_data['emoji']} {mood_data['name']}\n\n"
            f"💌 می‌خوای پیام ویژه‌ای برای پارتنرت بنویسی؟\n"
            f"(اختیاری - ۲۰ ثانیه فرصت داری)\n\n"
            f"📝 یا «رد» رو بفرست تا رد کنی...",
            uid, call.message.message_id
        )
    except:
        bot.send_message(
            uid,
            f"✅ حالت تو: {mood_data['emoji']} {mood_data['name']}\n\n"
            f"💌 می‌خوای پیام ویژه‌ای برای پارتنرت بنویسی؟\n"
            f"(اختیاری - ۲۰ ثانیه فرصت داری)\n\n"
            f"📝 یا «رد» رو بفرست تا رد کنی..."
        )


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_mood_message")
def mood_message_handler(message):
    """دریافت پیام ویژه کاربر - نسخه به روز شده"""
    uid = message.chat.id

    if uid not in temp_data or "current_mood" not in temp_data[uid]:
        bot.send_message(uid, "❌ خطا در پردازش!")
        user_state.pop(uid, None)
        return

    mood_key = temp_data[uid]["current_mood"]
    mood_data = MOOD_CATEGORIES[mood_key]
    custom_message = None

    if message.text.strip().lower() not in ["رد", "skip", "no", "نه"]:
        custom_message = message.text.strip()

    # دریافت جنسیت کاربر برای شخصی‌سازی پیام
    user_gender_result = safe_execute_db(
        "SELECT gender, name FROM users WHERE user_id = ?", (uid,))
    user_gender = user_gender_result[0][0] if user_gender_result else "مرد"
    user_name = user_gender_result[0][1] if user_gender_result else "عزیزم"

    # ذخیره در دیتابیس
    try:
        conn = sqlite3.connect("mood_tracking.db", check_same_thread=False)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO mood_entries (user_id, mood_type, custom_message) VALUES (?, ?, ?)",
            (uid, mood_key, custom_message)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"خطا در ذخیره حالت خلقی: {e}")

    # ارسال به پارتنر با پیام‌های جنسیت‌محور
    send_mood_to_partner(uid, mood_key, custom_message)

    # پیام تأیید به کاربر با توجه به جنسیت
    if user_gender == "مرد":
        confirmation_text = f"✅ حالتت ثبت شد آقا {user_name}!\n\n🌙 امروز: {mood_data['name']} {mood_data['emoji']}"
    else:
        confirmation_text = f"✅ حالتت ثبت شد خانم {user_name}!\n\n🌙 امروز: {mood_data['name']} {mood_data['emoji']}"

    if custom_message:
        confirmation_text += f"\n💌 پیام ویژه: \"{custom_message}\""

    confirmation_text += f"\n\n📤 این اطلاعات برای پارتنرت ارسال شد..."

    bot.send_message(uid, confirmation_text)

    # پاکسازی state
    user_state.pop(uid, None)
    temp_data.pop(uid, None)


def send_mood_to_partner(user_id, mood_key, custom_message):
    """ارسال حالت خلقی به پارتنر با متون متفاوت بر اساس جنسیت"""
    try:
        # دریافت اطلاعات پارتنر و جنسیت کاربر
        result = safe_execute_db("""
            SELECT u.partner_id, u.gender, u.name, u2.gender as partner_gender, u2.name as partner_name 
            FROM users u 
            JOIN users u2 ON u.partner_id = u2.user_id 
            WHERE u.user_id = ? AND u.connection_status = 'connected'
        """, (user_id,))

        if not result or not result[0][0]:
            return False

        partner_id, user_gender, user_name, partner_gender, partner_name = result[0]
        mood_data = MOOD_CATEGORIES[mood_key]

        # انتخاب پیام بر اساس جنسیت کاربر
        if user_gender == "مرد":
            messages = get_man_mood_messages(mood_key, user_name, partner_name)
        else:  # زن
            messages = get_woman_mood_messages(
                mood_key, user_name, partner_name)

        random_message = random.choice(messages)

        # ساخت متن پیام
        message_text = f"🌙 گزارش حالت خلقی پارتنر:\n\n"
        message_text += f"💖 {user_name} امروز احساس: {mood_data['name']} {mood_data['emoji']}\n\n"
        message_text += f"💌 پیام ویژه: \"{random_message}\"\n\n"

        if custom_message:
            message_text += f"📝 پیام شخصی از {user_name}:\n\"{custom_message}\"\n\n"

        # پیشنهاد عملی بر اساس جنسیت
        suggestion = get_gender_specific_suggestion(user_gender, mood_key)
        message_text += f"💡 پیشنهاد ما: {suggestion}"

        bot.send_message(partner_id, message_text)
        return True

    except Exception as e:
        print(f"خطا در ارسال به پارتنر: {e}")
        return False


def get_partner_mood_display(partner_id):
    """دریافت حالت خلقی پارتنر برای نمایش در پروفایل - نسخه بهبود یافته"""
    try:
        conn = sqlite3.connect("mood_tracking.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("""
            SELECT mood_type, custom_message, created_at 
            FROM mood_entries 
            WHERE user_id = ? 
            ORDER BY created_at DESC LIMIT 1
        """, (partner_id,))

        result = cur.fetchone()
        conn.close()

        if not result:
            return "❌ هنوز حالت خلقی ثبت نکرده"

        mood_key, custom_message, created_at = result
        mood_data = MOOD_CATEGORIES.get(mood_key, {})

        # بررسی زمان ثبت
        created_time = datetime.fromisoformat(created_at)
        time_diff = datetime.now() - created_time

        # اگر بیش از 24 ساعت گذشته
        if time_diff.total_seconds() > 24 * 3600:
            hours_passed = int(time_diff.total_seconds() // 3600)
            return f"❌ آخرین ثبت: {hours_passed} ساعت پیش"

        # اگر امروز ثبت کرده
        display_text = f"✨ {mood_data.get('name', 'نامشخص')} {mood_data.get('emoji', '')}"

        if custom_message:
            # کوتاه کردن پیام اگر طولانی باشد
            short_message = custom_message[:30] + \
                "..." if len(custom_message) > 30 else custom_message
            display_text += f"\n💌 \"{short_message}\""

        # اضافه کردن زمان ثبت
        time_str = created_time.strftime("%H:%M")
        display_text += f"\n⏰ ثبت شده در: {time_str}"

        return display_text

    except Exception as e:
        print(f"خطا در دریافت حالت خلقی: {e}")
        return "❌ خطا در دریافت"


def check_and_send_mood_reminders():
    """بررسی و ارسال یادآوری حالت خلقی هر 27 ساعت - نسخه اصلاح شده"""
    try:
        # ابتدا مطمئن شو دیتابیس به‌روز است
        setup_mood_database()

        conn_users = sqlite3.connect(
            "relation_agent.db", check_same_thread=False)
        cur_users = conn_users.cursor()
        cur_users.execute("SELECT user_id FROM users")
        users = cur_users.fetchall()
        conn_users.close()

        conn_mood = sqlite3.connect(
            "mood_tracking.db", check_same_thread=False)
        cur_mood = conn_mood.cursor()

        reminded_count = 0
        skipped_count = 0

        for (user_id,) in users:
            try:
                # بررسی آخرین یادآوری ارسال شده به کاربر
                cur_mood.execute("""
                    SELECT last_reminder_time FROM mood_reminders 
                    WHERE user_id = ?
                """, (user_id,))

                reminder_result = cur_mood.fetchone()

                now = datetime.now()
                should_remind = False

                if not reminder_result or not reminder_result[0]:
                    # کاربر اولین بار است یا last_reminder_time خالی است
                    should_remind = True
                    print(
                        f"🔔 کاربر {user_id} اولین یادآوری یا last_reminder_time خالی")
                else:
                    # بررسی 27 ساعت گذشته از آخرین یادآوری
                    try:
                        last_reminder = datetime.fromisoformat(
                            reminder_result[0])
                        time_diff = now - last_reminder
                        if time_diff.total_seconds() >= 27 * 3600:  # 27 ساعت
                            should_remind = True
                            print(
                                f"🔔 کاربر {user_id} 27 ساعت گذشته یادآوری نشده")
                        else:
                            hours_passed = int(
                                time_diff.total_seconds() // 3600)
                            print(
                                Fore.LIGHTBLUE_EX + f"⏳ کاربر {user_id} {hours_passed} ساعت پیش یادآوری شده")
                    except (ValueError, TypeError) as e:

                        print(
                            f"⚠️ خطا در تاریخ یادآوری کاربر {user_id}: {e} - ارسال یادآوری جدید")
                        should_remind = True

                if should_remind:
                    # بررسی اینکه کاربر واقعاً نیاز به یادآوری دارد
                    cur_mood.execute("""
                        SELECT created_at FROM mood_entries 
                        WHERE user_id = ? 
                        ORDER BY created_at DESC LIMIT 1
                    """, (user_id,))

                    last_entry = cur_mood.fetchone()

                    needs_reminder = True
                    if last_entry and last_entry[0]:
                        # اگر کاربر در 27 ساعت گذشته حالت خلقی ثبت کرده، نیاز به یادآوری نیست
                        try:
                            last_entry_time = datetime.fromisoformat(
                                last_entry[0])
                            entry_time_diff = now - last_entry_time
                            if entry_time_diff.total_seconds() < 27 * 3600:
                                needs_reminder = False
                                skipped_count += 1
                                print(
                                    f"✅ کاربر {user_id} اخیراً حالت خلقی ثبت کرده")
                        except (ValueError, TypeError) as e:
                            print(
                                f"⚠️ خطا در تاریخ ثبت خلقی کاربر {user_id}: {e}")
                            # در صورت خطا، یادآوری ارسال کن
                            needs_reminder = True

                    if needs_reminder:
                        success = send_mood_reminder(user_id)
                        if success:

                            cur_mood.execute("""
                                INSERT OR REPLACE INTO mood_reminders 
                                (user_id, last_reminder_time) 
                                VALUES (?, ?)
                            """, (user_id, now.isoformat()))
                            conn_mood.commit()
                            reminded_count += 1
                            print(
                                Fore.LIGHTBLUE_EX + f"✅ Reminder seent to {user_id} ")
                        else:
                            print(
                                Fore.RED + f"❌ Mood reminder to user {user_id} not possible")
                    else:

                        cur_mood.execute("""
                            INSERT OR REPLACE INTO mood_reminders 
                            (user_id, last_reminder_time) 
                            VALUES (?, ?)
                        """, (user_id, now.isoformat()))
                        conn_mood.commit()
                        print(Fore.LIGHTBLUE_EX +
                              f"User reminder time {user_id} updated")

            except Exception as e:
                print(Fore.RED + f"ERROR IN CHECKING USER {user_id}: {e}")
                continue

        conn_mood.close()
        print(
            Fore.LIGHTBLUE_EX + f"✅ Moods checked- {reminded_count} Users notifed - {skipped_count} ")

    except Exception as e:
        print(Fore.RED + f"ERROR IN USER MOOD CHECKING: {e}")


def send_mood_reminder(user_id):
    """ارسال پیام یادآوری - نسخه اصلاح شده"""
    try:
        reminder_messages = [
            "💫 یادآوری محبت‌آمیز!\n\nعزیزم، نمی‌خوای پارتنرت رو از حال و اخلاق امروزت با خبر کنی؟",
            "🌙 فرصت طلایی!\n\nپارتنرت مشتاقه بدون امروز حالت چطوریه!",
            "💖 یک قدم به سمت صمیمیت بیشتر!\n\nیادت نره حالت امروزت رو ثبت کنی",
            "😊 رابطه‌ات رو زنده نگه دار!\n\nپارتنرت منتظر خبر از حال و احوالت!"
        ]

        message = random.choice(reminder_messages)
        message += "\n\n🌙 با ثبت حالت خلقی:\n• پارتنرت تو رو بهتر درک میکنه\n• پیام ویژه براش میفرستی\n• رابطه‌تون صمیمی‌تر میشه\n\nکافیه روی «🌙 حالت خلقی» کلیک کنی!"

        bot.send_message(user_id, message)
        print(Fore.LIGHTBLUE + f"✅ Reminder sent to {user_id}")
        return True

    except Exception as e:
        print(Fore.RED + f"❌ ERROR IN SENDING REMINDER TO USER{user_id}: {e}")
        return False


def send_mood_reminder(user_id):

    try:
        reminder_messages = [
            "💫 یادآوری محبت‌آمیز!\n\nعزیزم، نمی‌خوای پارتنرت رو از حال و اخلاق امروزت با خبر کنی؟",
            "🌙 فرصت طلایی!\n\nپارتنرت مشتاقه بدون امروز حالت چطوریه!",
            "💖 یک قدم به سمت صمیمیت بیشتر!\n\nیادت نره حالت امروزت رو ثبت کنی",
            "😊 رابطه‌ات رو زنده نگه دار!\n\nپارتنرت منتظر خبر از حال و احوالت!"
        ]

        message = random.choice(reminder_messages)
        message += "\n\n🌙 با ثبت حالت خلقی:\n• پارتنرت تو رو بهتر درک میکنه\n• پیام ویژه براش میفرستی\n• رابطه‌تون صمیمی‌تر میشه\n\nکافیه روی «🌙 حالت خلقی» کلیک کنی!"

        bot.send_message(user_id, message)
        print(f"✅ یادآوری برای کاربر {user_id} ارسال شد")
        return True

    except Exception as e:
        print(f"❌ خطا در ارسال یادآوری به {user_id}: {e}")
        return False


def notification_loop():
    """حلقه اصلی نوتیفیکیشن"""
    last_mood_check = datetime.now() - timedelta(hours=28)  # برای اولین اجرا

    while True:
        try:
            send_notifications()

            # چک کردن یادآوری حالت خلقی فقط هر 1 ساعت
            now = datetime.now()
            if (now - last_mood_check).total_seconds() >= 3600:  # هر 1 ساعت
                check_and_send_mood_reminders()
                last_mood_check = now

        except Exception as e:
            print(f"خطا در حلقه نوتیفیکیشن: {e}")
        time.sleep(300)  # هر 5 دقیقه چک کن


def get_gender_specific_suggestion(user_gender, mood_key):
    """پیشنهادات عملی بر اساس جنسیت کاربر"""

    suggestions_man = {
        "happy": "😎 اووووه شاد شده! باهاش بخند و همراهیش کن تا حس قدرت و خوشحالی خودش بالا بره 💪🎉",
        "romantic": "💌 یه جمله عاشقونه بگو و با یه کار کوچیک محبتت رو نشون بده، قلبش مال تو میشه 🔥",
        "calm": "🧘‍♂️ بذار آروم باشه، با سکوت محترمانه کنارش باش تا حس امنیت کنه 🌌",
        "sad": "🤫 فقط گوش بده و زیاد نصیحت نکن، اینجوری اعتمادش جلب میشه ❤️",
        "stressed": "💆‍♂️ یه راه ساده برای آروم شدنش پیشنهاد بده یا یه حس آرامش بساز ⚡",
        "energetic": "🏃‍♂️ فعال باش و باهاش حرکت کن، هیجانش بالا میره و حس رقابت‌جو پیدا میکنه 🔥",
        "focused": "📚 بذار روی کارش تمرکز کنه، مزاحمش نشو، اینجوری حس کارآمدی پیدا میکنه 🛡️",
        "thoughtful": "🕯️ بذار با افکارش باشه و همراهش باش بدون فشار، حس ارزشمندی میده 🌙",
        "playful": "😂 یه جوک بگو یا باهاش بخند، هم استرسش میره هم صمیمیت بیشتر میشه 🎭",
        "sensitive": "💖 با مراقبت حرف بزن و بدون سرزنش، حس امنیت و وابستگی ایجاد میشه 🌹",
        "determined": "🏹 اهدافش رو تحسین کن و پشتش باش، اعتماد به نفسش اوج میگیره ⚔️",
        "tired": "🛌 یه فضای آروم براش بساز یا ماساژ کوتاه بده تا شارژ شه 🌿"
    }

    suggestions_woman = {
        "happy": "💃 باهاش خوش بگذرون و همراهش بخند تا حس شادی و تعلقش اوج بگیره 🌈",
        "romantic": "🍷 یه لحظه رمانتیک بساز و عشقتو نشونش بده 💖",
        "calm": "🌌 با یه گفتگوی ساده در مورد احساساتش کنارش باش، حس امنیت میده ✨",
        "sad": "🤗 بغلش کن و گوش بده، اعتمادش جلب میشه ❤️",
        "stressed": "🕊️ محیط آروم بساز و بهش آرامش بده تا استرسش کم شه 🌿",
        "energetic": "🎨 باهاش فعالیت‌های جدید انجام بده، حس هیجان و همراهی بیشتر میشه 🔥",
        "focused": "🛋️ فضای کارش رو آروم نگه دار و حمایت کن، حس ارزشمندی پیدا میکنه 🌟",
        "thoughtful": "🕯️ ساکت و همراهش باش، افکارش محترم شمرده میشه 🌙",
        "playful": "🎭 یه بازی یا خنده بساز، حس صمیمیت و تعلقش اوج میگیره 💫",
        "sensitive": "🌹 با کلمات و رفتار مراقبت کن، حس امنیت و احترام عمیق ایجاد میشه 💖",
        "determined": "🏹 پشت اهدافش باش و اعتمادشو بالا ببر ⚡",
        "tired": "🛌 یه محیط آروم و راحت بساز تا انرژی و امنیتش برگرده 🌿"
    }

    if user_gender == "مرد":
        return suggestions_man.get(mood_key, "💌 با محبت و گوش دادن بدون قضاوت باهاش باش 🛡️")
    else:
        return suggestions_woman.get(mood_key, "💖 با حضور و مراقبت عاطفی باهاش باش 🌹")


def get_man_mood_messages(mood_key, man_name, woman_name):
    """پیام‌های ویژه زمانی که مرد حالتش را ثبت می‌کند"""

    messages = {
        "happy": [
            f"😎 امروز {man_name} حسابی شاد و سرحاله! یه برنامه توپ براش ترتیب بده تا با هم حال کنید! 💫",
            f"🎉 {man_name} امروز پرانرژی و خوشحاله! با یه حرکت باحال کنارش باش و خوش بگذرونید!",
            f"✨ امروز {man_name} پر از حس خوب و انگیزه‌ست! فرصت عالی برای یه تجربه مشترک!"
        ],
        "romantic": [
            f"💌 دل {man_name} امروز پر عشقه! یه توجه رمانتیک کنارش انجام بده و دلش رو بدست بیار! 🌹",
            f"💕 امروز {man_name} عاشق احساساته! یه حرکت عاشقانه و خاص براش داشته باش!",
            f"💘 قلب {man_name} امروز فقط برای تو می‌تپه! با عشق و توجه جوابش رو بده!"
        ],
        "calm": [
            f"🌿 امروز {man_name} در آرامشه! فضای مناسب برای صحبت‌های عمیق فراهم کن و گوش بده ☁️",
            f"☁️ حال آروم {man_name} بهترین فرصته برای شنیدن حرف‌هاش و کنار بودن باهاش",
            f"🌼 امروز {man_name} یه آرامش خاص داره! می‌تونی در مورد آینده و آرزوهاش صحبت کنید"
        ],
        "sad": [
            f"🤗 امروز {man_name} ناراحته! کنارش باش و بدون قضاوت گوش بده",
            f"💙 دل {man_name} سنگینه! با همدلی و حمایت بهش آرامش بده",
            f"🌧️ امروز {man_name} نیاز به پشت و پناه داره! کنار باش و قوت قلب بده"
        ],
        "stressed": [
            f"🌪️ امروز {man_name} تحت فشاره! فضای شخصی بهش بده و آرامش ایجاد کن",
            f"⚡ حال {man_name} شلوغه! یه راه ساده برای آروم شدنش پیدا کن",
            f"🌀 امروز {man_name} استرس داره! با آرامش و توجه حواسش رو راحت کن"
        ],
        "energetic": [
            f"⚡ {man_name} امروز پرانرژی و آماده ماجراجوییه! با هم یه تجربه جدید بسازید",
            f"🚀 امروز {man_name} دنبال چالش و تحرکه! یه فعالیت جذاب با هم انجام بدین",
            f"💪 انرژی امروز {man_name} بی‌نظیره! ورزش یا حرکت هیجان‌انگیز با هم داشته باشید"
        ],
        "focused": [
            f"🎯 امروز {man_name} کاملاً روی هدفش تمرکز کرده! مزاحمش نشو و حمایتش کن",
            f"📚 {man_name} امروز مشغول کار مهمیه! بهترین همراه و پشتیبان باش",
            f"🔥 تمرکز {man_name} بالاست! کنارش باش و به پیشرفتش کمک کن"
        ],
        "thoughtful": [
            f"🧠 امروز {man_name} در حال فکر و تأمله! به فضای فکریش احترام بذار و مزاحمش نشو",
            f"🌌 {man_name} امروز فکرای عمیق داره! با آرامش و احترام همراهش باش",
            f"💭 مسائل مهم ذهن {man_name} رو پر کرده! سکوت و همراهی آرام بساز"
        ],
        "playful": [
            f"😂 امروز {man_name} بازیگوش و شوخ‌طبعه! با هم بخندید و حال کنید",
            f"🎭 حال شوخی {man_name} عالیه! یه لحظه خنده‌دار با هم داشته باشید",
            f"🤡 امروز {man_name} آماده بازی و خوشی‌ست! باهاش همراه شو"
        ],
        "sensitive": [
            f"🌸 امروز {man_name} حساست! با دقت و محبت رفتار کن",
            f"💐 احساسات {man_name} ظریفه! مراقب حرف‌ها و رفتار خودت باش",
            f"🌹 امروز {man_name} دلش خیلی نازکه! با ملایمت و عشق برخورد کن"
        ],
        "determined": [
            f"💪 امروز {man_name} مصممه و قوی! پشتش باش و اهدافش رو تحسین کن",
            f"🔥 اراده {man_name} امروز فولادینه! حمایتش کن و تشویقش کن",
            f"🚀 امروز {man_name} برای هدفش مصممه! بهترین همراهی باش"
        ],
        "tired": [
            f"🌙 امروز {man_name} خسته‌ست! یه استراحت کوتاه یا ماساژ آروم براش بساز",
            f"😴 انرژی {man_name} کم شده! فشار نیار و فضای آروم ایجاد کن",
            f"💤 امروز {man_name} خسته‌ست! یه لحظه آرامش ویژه براش بساز"
        ]
    }

    return messages.get(mood_key, ["💖 پارتنرت امروز حالت خاصی داره! با درک و محبت باهاش رفتار کن!"])


def get_woman_mood_messages(mood_key, woman_name, man_name):
    """پیام‌های ویژه زمانی که زن حالتش را ثبت می‌کند"""

    messages = {
        "happy": [
            f"🌟 امروز {woman_name} حسابی شاد و پرانرژیه! یه سوپرایز باحال براش بساز!",
            f"💫 حال {woman_name} عالیه! از انرژی مثبتش استفاده کن و یه روز رویایی داشته باشید!",
            f"🎉 امروز {woman_name} پر از شادی و لذت‌ست! با هم بیرون برید و کیف کنید!"
        ],
        "romantic": [
            f"🌹 دل {woman_name} امروز پر عشقه! یه حرکت رمانتیک و خاص براش داشته باش",
            f"💕 حال عاشقانه {woman_name} عالیه! با یه کار ویژه دلش رو بدست بیار",
            f"💘 قلب {woman_name} امروز فقط برای تو می‌تپه! با عشق و توجه جوابش رو بده"
        ],
        "calm": [
            f"🌿 امروز {woman_name} آروم و متفکره! بهترین فرصت برای شنیدن احساساتش",
            f"☁️ حال {woman_name} امروز خیلی آرومه! موقعیت عالی برای ارتباط قلبی",
            f"🌸 امروز {woman_name} در آرامشه! می‌تونید در مورد رویاها و برنامه‌ها صحبت کنید"
        ],
        "sad": [
            f"🤗 امروز {woman_name} ناراحته! کنارش باش و بدون قضاوت گوش بده",
            f"💜 دل {woman_name} سنگینه! با همدلی و محبت واقعی آرامشش بده",
            f"🌧️ امروز {woman_name} نیاز به حمایت داره! کنار باش و قوت قلب بده"
        ],
        "stressed": [
            f"🌪️ امروز {woman_name} استرس داره! یه فضای امن و آروم براش بساز",
            f"⚡ حال {woman_name} شلوغه! ساده‌ترین و آرام‌بخش‌ترین راه برای آروم کردنش پیدا کن",
            f"🌀 امروز {woman_name} تحت فشاره! با آرامش و توجه حواسش رو راحت کن"
        ],
        "energetic": [
            f"⚡ امروز {woman_name} پرانرژی و آماده کشف چیزای جدیده! باهاش همراه شو",
            f"🚀 حال {woman_name} برای تجربیات جدید عالیه! با هم ماجراجویی کنید",
            f"💃 امروز {woman_name} پر از انگیزه‌ست! بهترین فرصت برای دنبال کردن علایقش"
        ],
        "focused": [
            f"🎯 امروز {woman_name} روی هدفش تمرکزه! حمایتش کن و فضای کار بهش بده",
            f"📚 حال {woman_name} برای کار مهم عالیه! بهترین پشتیبان و همراه باش",
            f"🔥 امروز {woman_name} کاملاً متمرکزه! مشوقش باش و انرژی مثبت بده"
        ],
        "thoughtful": [
            f"🧠 امروز {woman_name} در حال تفکره! به فضای فکریش احترام بذار و مزاحمش نشو",
            f"🌌 حال {woman_name} امروز عمیقه! همراهی آرام و بدون فشار داشته باش",
            f"💭 مسائل مهم ذهن {woman_name} رو پر کرده! سکوت و حمایت آرام بساز"
        ],
        "playful": [
            f"😂 امروز {woman_name} بازیگوش و شوخ‌طبعه! با هم بخندید و لذت ببرید",
            f"🎭 حال شوخی {woman_name} عالیه! یه لحظه خنده‌دار و سرگرم‌کننده با هم داشته باشید",
            f"🤡 امروز {woman_name} آماده بازی و خوشی‌ست! باهاش همراه شو"
        ],
        "sensitive": [
            f"🌸 امروز {woman_name} حساست! با دقت و مهربانی رفتار کن",
            f"💐 احساسات {woman_name} ظریفه! مراقب حرف‌ها و رفتار خودت باش",
            f"🌹 امروز {woman_name} دلش خیلی نازکه! با ملایمت و عشق برخورد کن"
        ],
        "determined": [
            f"💪 امروز {woman_name} مصممه و قوی! پشتش باش و اهدافش رو تحسین کن",
            f"🔥 اراده {woman_name} امروز فولادینه! حمایتش کن و تشویقش کن",
            f"🚀 امروز {woman_name} برای هدفش مصممه! بهترین همراهی باش"
        ],
        "tired": [
            f"🌙 امروز {woman_name} خسته‌ست! یه استراحت کوتاه یا فضای آروم براش بساز",
            f"😴 انرژی {woman_name} کم شده! فشار نیار و محیط آروم ایجاد کن",
            f"💤 امروز {woman_name} خسته‌ست! یه لحظه آرامش ویژه براش بساز"
        ]
    }

    return messages.get(mood_key, ["💖 پارتنرت امروز حالت خاصی داره! با درک و با محبت باهاش رفتار کن!"])


#################################################################################################### SuperHard################################SuperHard################################SuperHard################################SuperHard################################SuperHard################################################################################################


@bot.callback_query_handler(func=lambda call: call.data == "books_menu")
def books_menu_handler(call):
    """Handler منوی کتاب‌نویسی"""
    uid = call.message.chat.id

    # بررسی اتصال به پارتنر
    partner_id = get_user_partner(uid)
    if not partner_id:
        bot.answer_callback_query(
            call.id, "❌ برای کتاب‌نویسی باید به پارتنرت متصل باشی!")
        return

    # اطمینان از ایجاد دیتابیس
    try:
        setup_book_database()
    except:
        pass

    try:
        bot.edit_message_text(
            "📚 سیستم کتاب‌نویسی مشترک\n\n"
            "می‌تونی با پارتنرت کتاب بنویسی و داستان‌های مشترک خلق کنید!",
            uid,
            call.message.message_id,
            reply_markup=books_main_menu()
        )
    except:
        bot.send_message(
            uid,
            "📚 سیستم کتاب‌نویسی مشترک\n\n"
            "می‌تونی با پارتنرت کتاب بنویسی و داستان‌های مشترک خلق کنید!",
            reply_markup=books_main_menu()
        )


def setup_book_database():
    try:
        conn = sqlite3.connect(
            "books.db", check_same_thread=False, isolation_level=None)
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS user_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            partner_id INTEGER NOT NULL,
            book_name TEXT NOT NULL,
            genre TEXT NOT NULL,
            description TEXT,
            preface TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, partner_id, book_name)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS book_chapters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            chapter_number INTEGER NOT NULL,
            chapter_name TEXT NOT NULL,
            chapter_description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(book_id, chapter_number),
            FOREIGN KEY (book_id) REFERENCES user_books(id) ON DELETE CASCADE
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS book_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            chapter_id INTEGER NOT NULL,
            page_number INTEGER NOT NULL,
            content TEXT NOT NULL,
            author_id INTEGER NOT NULL,
            formatted_content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(book_id, chapter_id, page_number),
            FOREIGN KEY (book_id) REFERENCES user_books(id) ON DELETE CASCADE,
            FOREIGN KEY (chapter_id) REFERENCES book_chapters(id) ON DELETE CASCADE
        )
        """)

        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_books_user ON user_books(user_id, partner_id)")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_chapters_book ON book_chapters(book_id)")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_pages_book_chapter ON book_pages(book_id, chapter_id)")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_pages_author ON book_pages(author_id)")

        conn.commit()
        conn.close()
        print("✅ دیتابیس کتاب ایجاد شد")
        return True

    except Exception as e:
        print(f"❌ خطا در ایجاد دیتابیس کتاب: {e}")
        return False


BOOK_GENRES = {
    "romance": "رمان عاشقانه 💖",
    "adventure": "ماجراجویی 🗺️",
    "scifi": "علمی-تخیلی 🚀",
    "fantasy": "فانتزی 🧙‍♂️",
    "comedy": "کمدی 😂",
    "drama": "درام 🎭",
    "horror": "وحشت 👻",
    "mystery": "معمایی 🔍",
    "biography": "زندگینامه 📜",
    "history": "تاریخی 🏛️",
    "self_help": "خودیاری 💪",
    "poetry": "شعر 📝",
    "free": "آزاد ✨"
}


def safe_execute_book_db(query, params=()):
    try:
        conn = sqlite3.connect("books.db", check_same_thread=False)
        cur = conn.cursor()
        cur.execute(query, params)
        result = cur.fetchall()
        conn.commit()
        conn.close()
        return result
    except Exception as e:
        print(f"خطای دیتابیس کتاب: {e}")
        return None


def get_user_partner(user_id):
    try:
        conn = sqlite3.connect("relation_agent.db", check_same_thread=False)
        cur = conn.cursor()
        cur.execute(
            "SELECT partner_id FROM users WHERE user_id = ? AND connection_status = 'connected'", (user_id,))
        result = cur.fetchone()
        conn.close()
        return result[0] if result else None
    except:
        return None


def books_main_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(
        "📖 کتاب‌های من", callback_data="book_my_books"))
    markup.row(InlineKeyboardButton(
        "✍️ کتاب جدید", callback_data="book_create"))
    markup.row(InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main"))
    return markup


@bot.callback_query_handler(func=lambda call: call.data == "book_menu")
def book_menu_handler(call):
    uid = call.message.chat.id

    try:
        conn = sqlite3.connect("books.db", check_same_thread=False)
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_books'")
        table_exists = cur.fetchone()
        conn.close()

        if not table_exists:
            setup_book_database()
    except:
        setup_book_database()

    partner_id = get_user_partner(uid)
    if not partner_id:
        bot.answer_callback_query(
            call.id, "❌ برای کتاب‌نویسی باید به پارتنرت متصل باشی!")
        return

    try:
        bot.edit_message_text(
            "📚 سیستم کتاب‌نویسی مشترک",
            uid, call.message.chat.id,
            reply_markup=books_main_menu()
        )
    except:
        bot.send_message(uid, "📚 سیستم کتاب‌نویسی مشترک",
                         reply_markup=books_main_menu())


def can_create_more_books(user_id):
    try:
        partner_id = get_user_partner(user_id)
        if not partner_id:
            return False, "❌ برای کتاب‌نویسی باید به پارتنرت متصل باشی!"

        conn = sqlite3.connect("books.db", check_same_thread=False)
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_books'")
        table_exists = cur.fetchone()

        if not table_exists:
            conn.close()
            return True, "✅ می‌تونی اولین کتابت رو ایجاد کنی!"

        cur.execute("SELECT COUNT(*) FROM user_books WHERE (user_id = ? AND partner_id = ?) OR (user_id = ? AND partner_id = ?)",
                    (user_id, partner_id, partner_id, user_id))
        book_count = cur.fetchone()[0]
        conn.close()

        if book_count >= 2:
            return False, "❌ شما و پارتنرت حداکثر ۲ کتاب می‌تونید داشته باشید!"

        conn = sqlite3.connect("books.db", check_same_thread=False)
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM user_books WHERE user_id = ?", (user_id,))
        user_book_count = cur.fetchone()[0]
        conn.close()

        if user_book_count >= 1:
            return False, "❌ شما قبلاً یک کتاب ایجاد کردی! پارتنرت باید کتاب بعدی رو ایجاد کنه."

        return True, "✅ می‌تونی کتاب جدید ایجاد کنی!"

    except Exception as e:
        return False, "❌ خطا در بررسی محدودیت!"


@bot.callback_query_handler(func=lambda call: call.data == "book_create")
def book_create_handler(call):
    uid = call.message.chat.id

    can_create, message = can_create_more_books(uid)
    if not can_create:
        bot.answer_callback_query(call.id, message)
        return

    user_state[uid] = "book_waiting_name"
    temp_data[uid] = {"book_creation": {}}

    try:
        bot.edit_message_text(
            "📖 اسم کتابت رو چی می‌خوای بذاری؟", uid, call.message.message_id)
    except:
        bot.send_message(uid, "📖 اسم کتابت رو چی می‌خوای بذاری؟")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "book_waiting_name")
def book_name_handler(message):
    uid = message.chat.id

    book_name = message.text.strip()
    if len(book_name) < 2:
        bot.send_message(uid, "❌ اسم کتاب باید حداقل ۲ حرف داشته باشه!")
        return

    if len(book_name) > 50:
        bot.send_message(
            uid, "❌ اسم کتاب خیلی طولانیه! حداکثر ۵۰ کاراکتر مجاز است.")
        return

    temp_data[uid]["book_creation"]["book_name"] = book_name
    user_state[uid] = "book_waiting_genre"

    markup = InlineKeyboardMarkup()
    genres = list(BOOK_GENRES.items())
    for i in range(0, len(genres), 3):
        row = []
        for j in range(3):
            if i + j < len(genres):
                genre_key, genre_name = genres[i + j]
                row.append(InlineKeyboardButton(
                    genre_name, callback_data=f"book_genre_{genre_key}"))
        markup.row(*row)

    markup.row(InlineKeyboardButton("🔙 بازگشت", callback_data="book_menu"))

    bot.send_message(
        uid, f"✅ اسم کتاب ثبت شد: «{book_name}»\n🎭 ژانر کتابت رو انتخاب کن:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("book_genre_"))
def book_genre_handler(call):
    uid = call.message.chat.id

    if user_state.get(uid) != "book_waiting_genre":
        bot.answer_callback_query(call.id, "❌ وضعیت نامعتبر")
        return

    genre_key = call.data.split("_")[2]
    genre_name = BOOK_GENRES.get(genre_key)

    if not genre_name:
        bot.answer_callback_query(call.id, "❌ ژانر نامعتبر")
        return

    temp_data[uid]["book_creation"]["genre"] = genre_key
    temp_data[uid]["book_creation"]["genre_name"] = genre_name
    user_state[uid] = "book_waiting_description"

    bot.edit_message_text(
        f"✅ ژانر انتخاب شد: {genre_name}\n📝 می‌خوای توضیحی برای کتابت بنویسی؟ (اختیاری)", uid, call.message.message_id)


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "book_waiting_description")
def book_description_handler(message):
    uid = message.chat.id

    description = message.text.strip()

    if description.lower() in ["رد", "skip", "no", "نه"]:
        description = ""

    if description and len(description) > 200:
        bot.send_message(
            uid, "❌ توضیحات خیلی طولانیه! حداکثر ۲۰۰ کاراکتر مجاز است.")
        return

    temp_data[uid]["book_creation"]["description"] = description
    user_state[uid] = "book_waiting_preface_choice"

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(
        "✅ بله، مقدمه می‌نویسم", callback_data="book_preface_yes"))
    markup.row(InlineKeyboardButton(
        "❌ بدون مقدمه", callback_data="book_preface_no"))

    bot.send_message(uid, "🔖 می‌خوای برای کتابت مقدمه بنویسی؟",
                     reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("book_preface_"))
def book_preface_choice_handler(call):
    uid = call.message.chat.id

    if user_state.get(uid) != "book_waiting_preface_choice":
        bot.answer_callback_query(call.id, "❌ وضعیت نامعتبر")
        return

    choice = call.data.split("_")[2]

    if choice == "yes":
        user_state[uid] = "book_waiting_preface"
        bot.edit_message_text("✍️ مقدمه کتابت رو بنویس:",
                              uid, call.message.message_id)
    else:
        temp_data[uid]["book_creation"]["preface"] = ""
        book_create_in_db(uid, call)


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "book_waiting_preface")
def book_preface_handler(message):
    uid = message.chat.id

    if message.text.strip().lower() == "پایان":
        preface = ""
    else:
        preface = message.text.strip()
        if len(preface) > 1000:
            bot.send_message(
                uid, "❌ مقدمه خیلی طولانیه! حداکثر ۱۰۰۰ کاراکتر مجاز است.")
            return

    temp_data[uid]["book_creation"]["preface"] = preface
    book_create_in_db(uid, message)


def book_create_in_db(uid, source):
    try:
        book_data = temp_data[uid]["book_creation"]
        partner_id = get_user_partner(uid)

        if not partner_id:
            bot.send_message(uid, "❌ خطا: پارتنر پیدا نشد!")
            return

        result = safe_execute_book_db("INSERT INTO user_books (user_id, partner_id, book_name, genre, description, preface) VALUES (?, ?, ?, ?, ?, ?)", (
            uid, partner_id, book_data["book_name"], book_data["genre"], book_data.get("description", ""), book_data.get("preface", "")))

        if result is None:
            bot.send_message(uid, "❌ خطا در ایجاد کتاب!")
            return

        book_id = safe_execute_book_db("SELECT last_insert_rowid()")[0][0]
        safe_execute_book_db(
            "INSERT INTO book_chapters (book_id, chapter_number, chapter_name) VALUES (?, 1, 'فصل اول')", (book_id,))

        user_state.pop(uid, None)
        temp_data.pop(uid, None)

        success_text = f"🎉 کتاب «{book_data['book_name']}» ایجاد شد!\n🎭 ژانر: {book_data['genre_name']}"

        try:
            partner_name_result = safe_execute_db(
                "SELECT name FROM users WHERE user_id = ?", (uid,))
            partner_name = partner_name_result[0][0] if partner_name_result else "پارتنرت"

            bot.send_message(
                partner_id, f"📖 پارتنرت کتاب جدید ایجاد کرد!\n📚 نام کتاب: {book_data['book_name']}\n✍️ نویسندگان: {partner_name} و تو")
        except:
            pass

        if hasattr(source, 'message_id'):
            try:
                bot.edit_message_text(
                    success_text, uid, source.message_id, reply_markup=books_main_menu())
            except:
                bot.send_message(uid, success_text,
                                 reply_markup=books_main_menu())
        else:
            bot.send_message(uid, success_text, reply_markup=books_main_menu())

    except Exception as e:
        bot.send_message(uid, "❌ خطا در ایجاد کتاب!")
        user_state.pop(uid, None)
        temp_data.pop(uid, None)


def format_book_text(text):
    if not text:
        return text

    text = re.sub(r'\|\|(.*?)\|\|', r'<spoiler>\1</spoiler>', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)

    return text


def get_writing_turn(book_id):
    """بررسی نوبت نوشتن - نسخه کاملاً اصلاح شده"""
    try:
        conn = sqlite3.connect("books.db", check_same_thread=False)
        cur = conn.cursor()

        # دریافت اطلاعات کتاب
        cur.execute(
            "SELECT user_id, partner_id FROM user_books WHERE id = ?", (book_id,))
        book_info = cur.fetchone()

        if not book_info:
            conn.close()
            return None, None

        user_id, partner_id = book_info

        # بررسی وجود جدول صفحات
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='book_pages'")
        pages_table_exists = cur.fetchone()

        if not pages_table_exists:
            # اگر جدول صفحات وجود ندارد، نوبت صاحب کتاب است
            conn.close()
            return user_id, 1

        # دریافت آخرین صفحه نوشته شده
        cur.execute(
            "SELECT author_id, page_number FROM book_pages WHERE book_id = ? ORDER BY page_number DESC LIMIT 1", (book_id,))
        last_page = cur.fetchone()

        if not last_page:
            # اگر هیچ صفحه‌ای وجود ندارد، نوبت صاحب کتاب است
            conn.close()
            return user_id, 1

        last_author, last_page_number = last_page

        print(
            f"🔧 دیباگ: کتاب {book_id}, آخرین نویسنده: {last_author}, آخرین صفحه: {last_page_number}")
        print(f"🔧 دیباگ: کاربر کتاب: {user_id}, پارتنر: {partner_id}")

        # تشخیص نویسنده بعدی
        if last_author == user_id:
            next_author = partner_id
        elif last_author == partner_id:
            next_author = user_id
        else:
            # اگر نویسنده نامشخص است، نوبت صاحب کتاب
            next_author = user_id

        next_page = last_page_number + 1

        print(f"🔧 دیباگ: نویسنده بعدی: {next_author}, صفحه بعدی: {next_page}")

        conn.close()
        return next_author, next_page

    except Exception as e:
        print(f"❌ خطا در get_writing_turn: {e}")
        return None, None


@bot.callback_query_handler(func=lambda call: call.data.startswith("book_write_"))
def book_write_handler(call):
    uid = call.message.chat.id
    book_id = int(call.data.split("_")[2])

    next_author, next_page = get_writing_turn(book_id)

    if not next_author:
        bot.answer_callback_query(call.id, "❌ خطا در بررسی نوبت نوشتن!")
        return

    if next_author != uid:
        bot.answer_callback_query(
            call.id, "⏳ الان نوبت پارتنرت برای نوشتن است!")
        return

    user_state[uid] = f"book_writing_{book_id}"
    temp_data[uid] = {
        "current_book": book_id,
        "current_page": next_page
    }

    book_info = safe_execute_book_db(
        "SELECT book_name FROM user_books WHERE id = ?", (book_id,))
    book_name = book_info[0][0] if book_info else "کتاب"

    bot.edit_message_text(
        f"✍️ در حال نوشتن صفحه {next_page} از کتاب «{book_name}»\n\nمی‌تونی از این فرمت‌ها استفاده کنی:\n**متن بولد**\n*متن ایتالیک*\n||متن اسپویلر||\n\nحداکثر ۳۹۰۰ کاراکتر\nبرای پایان «پایان» رو بفرست", uid, call.message.message_id)


@bot.message_handler(func=lambda m: user_state.get(m.chat.id, "").startswith("book_writing_"))
def book_content_handler(message):
    uid = message.chat.id
    state = user_state.get(uid, "")

    if not state.startswith("book_writing_"):
        return

    book_id = int(state.split("_")[2])

    next_author, next_page = get_writing_turn(book_id)
    if next_author != uid:
        bot.send_message(uid, "❌ الان نوبت تو نیست برای نوشتن!")
        user_state.pop(uid, None)
        temp_data.pop(uid, None)
        return

    content = message.text.strip()

    if content.lower() == "پایان":
        bot.send_message(uid, "📝 نوشتن متوقف شد.")
        user_state.pop(uid, None)
        temp_data.pop(uid, None)
        return

    if len(content) > 3900:
        bot.send_message(
            uid, f"❌ متن تو {len(content)} کاراکتره! حداکثر ۳۹۰۰ کاراکتر مجاز است.")
        return

    if len(content) < 10:
        bot.send_message(uid, "❌ متن خیلی کوتاهه! حداقل ۱۰ کاراکتر لازم است.")
        return

    formatted_content = format_book_text(content)

    try:
        chapter_result = safe_execute_book_db(
            "SELECT id FROM book_chapters WHERE book_id = ? AND chapter_number = 1", (book_id,))
        chapter_id = chapter_result[0][0] if chapter_result else 1

        result = safe_execute_book_db("INSERT INTO book_pages (book_id, chapter_id, page_number, content, author_id, formatted_content) VALUES (?, ?, ?, ?, ?, ?)", (
            book_id, chapter_id, next_page, content, uid, formatted_content))

        if result is None:
            bot.send_message(uid, "❌ خطا در ذخیره صفحه!")
            return

        safe_execute_book_db(
            "UPDATE user_books SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (book_id,))

        book_info = safe_execute_book_db(
            "SELECT book_name, partner_id FROM user_books WHERE id = ?", (book_id,))
        book_name, partner_id = book_info[0]

        try:
            user_name_result = safe_execute_db(
                "SELECT name FROM users WHERE user_id = ?", (uid,))
            user_name = user_name_result[0][0] if user_name_result else "پارتنرت"

            preview = content[:50] + "..." if len(content) > 50 else content

            bot.send_message(partner_id, f"📖 نوبت توئه که بنویسی!\n✍️ {user_name} صفحه {next_page} رو نوشت:\n\"{preview}\"\n📚 حالا نوبت توئه که صفحه {next_page + 1} رو بنویسی!",
                             reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("📝 نوشتن صفحه بعد", callback_data=f"book_write_{book_id}")))
        except:
            pass

        book_show_page(uid, book_id, next_page, message.message_id)

        user_state.pop(uid, None)
        temp_data.pop(uid, None)

    except Exception as e:
        bot.send_message(uid, "❌ خطا در ذخیره صفحه!")


def book_show_page(uid, book_id, page_number, message_id=None):
    """نمایش صفحه کتاب با گزینه‌های کامل شامل مدیریت فصل"""
    try:
        # ابتدا اطلاعات فصل فعلی را پیدا کنیم
        chapter_result = safe_execute_book_db("""
            SELECT bc.id, bc.chapter_number, bc.chapter_name 
            FROM book_chapters bc 
            WHERE bc.book_id = ? AND bc.id = (
                SELECT chapter_id FROM book_pages WHERE book_id = ? AND page_number = ?
            )
        """, (book_id, book_id, page_number))

        current_chapter_id = None
        current_chapter_number = 1
        current_chapter_name = "فصل اول"

        if chapter_result:
            current_chapter_id, current_chapter_number, current_chapter_name = chapter_result[
                0]

        result = safe_execute_book_db(
            "SELECT content, formatted_content, author_id, created_at, chapter_id FROM book_pages WHERE book_id = ? AND page_number = ?", (book_id, page_number))

        if not result:
            # کد قبلی برای صفحات خالی...
            pass

        content, formatted_content, author_id, created_at, chapter_id = result[0]

        author_name = get_user_name(author_id)

        book_info = safe_execute_book_db(
            "SELECT book_name FROM user_books WHERE id = ?", (book_id,))
        book_name = book_info[0][0] if book_info else "کتاب"

        total_pages_result = safe_execute_book_db(
            "SELECT MAX(page_number) FROM book_pages WHERE book_id = ?", (book_id,))
        total_pages = total_pages_result[0][0] if total_pages_result and total_pages_result[0][0] else 1

        # اطلاعات فصل‌ها
        chapters_result = safe_execute_book_db(
            "SELECT id, chapter_number, chapter_name FROM book_chapters WHERE book_id = ? ORDER BY chapter_number", (book_id,))
        total_chapters = len(chapters_result) if chapters_result else 1

        created_dt = datetime.fromisoformat(created_at)
        created_str = created_dt.strftime("%Y/%m/%d %H:%M")

        text = f"📖 {book_name}\n"
        text += f"📚 فصل {current_chapter_number}: {current_chapter_name}\n"
        text += f"📄 صفحه {page_number}/{total_pages}\n\n"
        text += f"✍️ نویسنده: {author_name}\n"
        text += f"⏰ زمان: {created_str}\n\n"
        text += "📝 محتوا:\n"
        text += formatted_content if formatted_content else content

        markup = InlineKeyboardMarkup()

        # ردیف 1: ناوبری بین صفحات
        nav_buttons = []
        if page_number > 1:
            nav_buttons.append(InlineKeyboardButton(
                "⬅️ صفحه قبلی", callback_data=f"book_page_{book_id}_{page_number-1}"))

        nav_buttons.append(InlineKeyboardButton(
            f"{page_number}/{total_pages}", callback_data=f"book_info_{book_id}"))

        if page_number < total_pages:
            nav_buttons.append(InlineKeyboardButton(
                "صفحه بعدی ➡️", callback_data=f"book_page_{book_id}_{page_number+1}"))

        markup.row(*nav_buttons)

        # ردیف 2: ناوبری بین فصل‌ها (اگر بیش از یک فصل وجود دارد)
        if total_chapters > 1:
            chapter_nav_buttons = []
            if current_chapter_number > 1:
                chapter_nav_buttons.append(InlineKeyboardButton(
                    "⏪ فصل قبلی", callback_data=f"book_prev_chapter_{book_id}"))

            chapter_nav_buttons.append(InlineKeyboardButton(
                f"فصل {current_chapter_number}", callback_data=f"book_chapters_{book_id}"))

            if current_chapter_number < total_chapters:
                chapter_nav_buttons.append(InlineKeyboardButton(
                    "فصل بعدی ⏩", callback_data=f"book_next_chapter_{book_id}"))

            markup.row(*chapter_nav_buttons)

        # ردیف 3: گزینه‌های اقدام
        action_buttons = []

        if author_id == uid:
            action_buttons.append(InlineKeyboardButton(
                "✏️ ویرایش این صفحه", callback_data=f"book_edit_{book_id}_{page_number}"))

        action_buttons.append(InlineKeyboardButton(
            "🔢 پرش به صفحه", callback_data=f"book_jump_{book_id}"))
        markup.row(*action_buttons)

        # ردیف 4: مدیریت فصل‌ها
        chapter_buttons = []
        chapter_buttons.append(InlineKeyboardButton(
            "📚 مدیریت فصل‌ها", callback_data=f"book_chapters_{book_id}"))
        chapter_buttons.append(InlineKeyboardButton(
            "➕ افزودن فصل جدید", callback_data=f"book_add_chapter_{book_id}"))
        markup.row(*chapter_buttons)

        # ردیف 5: گزینه‌های اصلی
        markup.row(InlineKeyboardButton("👁️ نمایش کامل کتاب",
                   callback_data=f"book_full_view_{book_id}"))
        markup.row(InlineKeyboardButton("📝 افزودن صفحه جدید",
                   callback_data=f"book_add_page_{book_id}"))

        # ردیف 6: منوی پایین
        markup.row(
            InlineKeyboardButton(
                "📚 کتاب‌های من", callback_data="book_my_books"),
            InlineKeyboardButton("🏠 منوی اصلی", callback_data="book_menu")
        )

        if message_id:
            try:
                bot.edit_message_text(
                    text, uid, message_id, reply_markup=markup, parse_mode="HTML")
            except:
                bot.send_message(
                    uid, text, reply_markup=markup, parse_mode="HTML")
        else:
            bot.send_message(uid, text, reply_markup=markup, parse_mode="HTML")

    except Exception as e:
        print(f"❌ خطا در book_show_page: {e}")
        bot.send_message(uid, "❌ خطا در نمایش صفحه!")


@bot.callback_query_handler(func=lambda call: call.data == "book_my_books")
def book_my_books_handler(call):
    uid = call.message.chat.id

    books = get_user_books(uid)

    if not books:
        try:
            bot.edit_message_text(
                "📚 شما هنوز کتابی ندارید!\n\n"
                "می‌تونی اولین کتابت رو ایجاد کنی:",
                uid, call.message.message_id,
                reply_markup=InlineKeyboardMarkup().row(
                    InlineKeyboardButton(
                        "✍️ کتاب جدید", callback_data="book_create"),
                    InlineKeyboardButton("🔙 بازگشت", callback_data="book_menu")
                )
            )
        except:
            bot.send_message(
                uid,
                "📚 شما هنوز کتابی ندارید!\n\n"
                "می‌تونی اولین کتابت رو ایجاد کنی:",
                reply_markup=InlineKeyboardMarkup().row(
                    InlineKeyboardButton(
                        "✍️ کتاب جدید", callback_data="book_create"),
                    InlineKeyboardButton("🔙 بازگشت", callback_data="book_menu")
                )
            )
        return

    markup = InlineKeyboardMarkup()

    for book in books:
        book_id, book_name, genre_name, total_pages, last_activity = book
        button_text = f"📖 {book_name} ({total_pages} صفحه)"
        markup.row(InlineKeyboardButton(
            button_text, callback_data=f"book_view_{book_id}"))

    # ❌ حذف شد: markup.row(InlineKeyboardButton("📝 اضافه کردن صفحه به کتاب موجود", callback_data="book_add_page_menu"))
    markup.row(InlineKeyboardButton("🔙 بازگشت", callback_data="book_menu"))

    try:
        bot.edit_message_text(
            "📚 کتاب‌های تو:\n\n"
            "برای مشاهده یا ادامه نوشتن یک کتاب رو انتخاب کن:",
            uid, call.message.message_id,
            reply_markup=markup
        )
    except:
        bot.send_message(
            uid,
            "📚 کتاب‌های تو:\n\n"
            "برای مشاهده یا ادامه نوشتن یک کتاب رو انتخاب کن:",
            reply_markup=markup
        )


def get_user_books(user_id):
    try:
        result = safe_execute_book_db(
            "SELECT ub.id, ub.book_name, ub.genre, (SELECT COUNT(*) FROM book_pages WHERE book_id = ub.id) as total_pages, ub.updated_at FROM user_books ub WHERE ub.user_id = ? OR ub.partner_id = ? ORDER BY ub.updated_at DESC", (user_id, user_id))

        books = []
        for row in result:
            book_id, book_name, genre_key, total_pages, updated_at = row
            genre_name = BOOK_GENRES.get(genre_key, "آزاد")
            books.append((book_id, book_name, genre_name,
                         total_pages, updated_at))

        return books

    except Exception as e:
        return []


@bot.callback_query_handler(func=lambda call: call.data.startswith("book_view_"))
def book_view_handler(call):
    uid = call.message.chat.id
    book_id = int(call.data.split("_")[2])

    book_show_page(uid, book_id, 1, call.message.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("book_page_"))
def book_page_handler(call):
    uid = call.message.chat.id
    parts = call.data.split("_")
    book_id = int(parts[2])
    page_number = int(parts[3])

    book_show_page(uid, book_id, page_number, call.message.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("book_jump_"))
def book_jump_handler(call):
    uid = call.message.chat.id
    book_id = int(call.data.split("_")[2])

    total_pages_result = safe_execute_book_db(
        "SELECT MAX(page_number) FROM book_pages WHERE book_id = ?", (book_id,))
    total_pages = total_pages_result[0][0] if total_pages_result[0][0] else 0

    if total_pages == 0:
        bot.answer_callback_query(call.id, "❌ این کتاب هنوز صفحه‌ای ندارد!")
        return

    user_state[uid] = f"book_jump_{book_id}"
    temp_data[uid] = {"book_id": book_id, "total_pages": total_pages}

    bot.edit_message_text(
        f"🔢 پرش به صفحه\n📖 این کتاب {total_pages} صفحه دارد.\nشماره صفحه مورد نظرت رو وارد کن:", uid, call.message.message_id)


@bot.message_handler(func=lambda m: user_state.get(m.chat.id, "").startswith("book_jump_"))
def book_jump_receive_handler(message):
    uid = message.chat.id
    state = user_state.get(uid, "")

    if not state.startswith("book_jump_"):
        return

    book_id = temp_data[uid]["book_id"]
    total_pages = temp_data[uid]["total_pages"]

    try:
        page_number = int(message.text.strip())

        if page_number < 1 or page_number > total_pages:
            bot.send_message(
                uid, f"❌ شماره صفحه باید بین ۱ تا {total_pages} باشد!")
            return

        user_state.pop(uid, None)
        temp_data.pop(uid, None)

        book_show_page(uid, book_id, page_number)

    except ValueError:
        bot.send_message(uid, "❌ لطفاً فقط عدد وارد کن!")
    except Exception as e:
        bot.send_message(uid, "❌ خطا در پرش به صفحه!")
        user_state.pop(uid, None)
        temp_data.pop(uid, None)


@bot.callback_query_handler(func=lambda call: call.data.startswith("book_info_"))
def book_info_handler(call):
    uid = call.message.chat.id
    book_id = int(call.data.split("_")[2])

    try:
        result = safe_execute_book_db(
            "SELECT book_name, genre, description, preface, created_at, user_id, partner_id FROM user_books WHERE id = ?", (book_id,))

        if not result:
            bot.answer_callback_query(call.id, "❌ کتاب پیدا نشد!")
            return

        (book_name, genre_key, description, preface,
         created_at, user_id, partner_id) = result[0]

        genre_name = BOOK_GENRES.get(genre_key, "آزاد")

        user_name = get_user_name(user_id)
        partner_name = get_user_name(partner_id)

        pages_result = safe_execute_book_db(
            "SELECT COUNT(*) FROM book_pages WHERE book_id = ?", (book_id,))
        total_pages = pages_result[0][0] if pages_result else 0

        author_stats = safe_execute_book_db(
            "SELECT author_id, COUNT(*) as page_count FROM book_pages WHERE book_id = ? GROUP BY author_id", (book_id,))

        text = f"📖 اطلاعات کتاب: {book_name}\n\n"
        text += f"🎭 ژانر: {genre_name}\n"
        text += f"📄 تعداد صفحات: {total_pages}\n"
        text += f"✍️ نویسندگان: {user_name} و {partner_name}\n\n"

        if description:
            text += f"📝 توضیحات: {description}\n\n"

        if preface:
            text += f"🔖 مقدمه: {preface}\n\n"

        if author_stats:
            text += "📊 آمار نوشتن:\n"
            for author_id, page_count in author_stats:
                author_name = user_name if author_id == user_id else partner_name
                text += f"• {author_name}: {page_count} صفحه\n"

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton(
                "📖 مشاهده کتاب", callback_data=f"book_view_{book_id}"),
            InlineKeyboardButton("🔙 بازگشت", callback_data="book_my_books")
        )

        bot.edit_message_text(
            text, uid, call.message.chat.id, reply_markup=markup)

    except Exception as e:
        bot.answer_callback_query(call.id, "❌ خطا در نمایش اطلاعات!")


def get_user_name(user_id):
    try:
        conn = sqlite3.connect("relation_agent.db", check_same_thread=False)
        cur = conn.cursor()
        cur.execute("SELECT name FROM users WHERE user_id = ?", (user_id,))
        result = cur.fetchone()
        conn.close()
        return result[0] if result else "نویسنده"
    except:
        return "نویسنده"


@bot.callback_query_handler(func=lambda call: call.data.startswith("book_edit_"))
def book_edit_handler(call):
    uid = call.message.chat.id
    parts = call.data.split("_")
    book_id = int(parts[2])
    page_number = int(parts[3])

    result = safe_execute_book_db(
        "SELECT content, author_id FROM book_pages WHERE book_id = ? AND page_number = ?", (book_id, page_number))

    if not result:
        bot.answer_callback_query(call.id, "❌ صفحه پیدا نشد!")
        return

    content, author_id = result[0]

    if author_id != uid:
        bot.answer_callback_query(
            call.id, "❌ فقط نویسنده صفحه می‌تونه ویرایش کنه!")
        return

    user_state[uid] = f"book_editing_{book_id}_{page_number}"
    temp_data[uid] = {
        "book_id": book_id,
        "page_number": page_number,
        "original_content": content
    }

    book_info = safe_execute_book_db(
        "SELECT book_name FROM user_books WHERE id = ?", (book_id,))
    book_name = book_info[0][0] if book_info else "کتاب"

    bot.edit_message_text(
        f"✏️ در حال ویرایش صفحه {page_number} از کتاب «{book_name}»\n\nمحتوای فعلی:\n{content}\n\nمحتوای جدید رو وارد کن:", uid, call.message.message_id)


@bot.message_handler(func=lambda m: user_state.get(m.chat.id, "").startswith("book_editing_"))
def book_edit_receive_handler(message):
    uid = message.chat.id
    state = user_state.get(uid, "")

    if not state.startswith("book_editing_"):
        return

    parts = state.split("_")
    book_id = int(parts[2])
    page_number = int(parts[3])

    content = message.text.strip()

    if content.lower() == "پایان":
        bot.send_message(uid, "✏️ ویرایش متوقف شد.")
        user_state.pop(uid, None)
        temp_data.pop(uid, None)
        return

    if len(content) > 3900:
        bot.send_message(
            uid, f"❌ متن تو {len(content)} کاراکتره! حداکثر ۳۹۰۰ کاراکتر مجاز است.")
        return

    if len(content) < 10:
        bot.send_message(uid, "❌ متن خیلی کوتاهه! حداقل ۱۰ کاراکتر لازم است.")
        return

    formatted_content = format_book_text(content)

    try:
        result = safe_execute_book_db("UPDATE book_pages SET content = ?, formatted_content = ?, updated_at = CURRENT_TIMESTAMP WHERE book_id = ? AND page_number = ? AND author_id = ?", (
            content, formatted_content, book_id, page_number, uid))

        if result is None:
            bot.send_message(uid, "❌ خطا در ذخیره تغییرات!")
            return

        safe_execute_book_db(
            "UPDATE user_books SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (book_id,))

        bot.send_message(uid, "✅ صفحه با موفقیت ویرایش شد!")

        book_show_page(uid, book_id, page_number)

        user_state.pop(uid, None)
        temp_data.pop(uid, None)

    except Exception as e:
        bot.send_message(uid, "❌ خطا در ویرایش صفحه!")
        user_state.pop(uid, None)
        temp_data.pop(uid, None)


@bot.callback_query_handler(func=lambda call: call.data.startswith("book_add_page_"))
def book_add_page_handler(call):
    """شروع فرآیند اضافه کردن صفحه به کتاب انتخاب شده"""
    uid = call.message.chat.id
    book_id = int(call.data.split("_")[3])

    # بررسی نوبت نوشتن
    next_author, next_page = get_writing_turn(book_id)

    if not next_author:
        bot.answer_callback_query(call.id, "❌ خطا در بررسی نوبت نوشتن!")
        return

    if next_author != uid:
        bot.answer_callback_query(
            call.id, "⏳ الان نوبت پارتنرت برای نوشتن است!")
        return

    user_state[uid] = f"book_writing_{book_id}"
    temp_data[uid] = {
        "current_book": book_id,
        "current_page": next_page
    }

    book_info = safe_execute_book_db(
        "SELECT book_name FROM user_books WHERE id = ?", (book_id,))
    book_name = book_info[0][0] if book_info else "کتاب"

    # دریافت آخرین صفحه برای الهام گرفتن
    last_page_result = safe_execute_book_db(
        "SELECT content FROM book_pages WHERE book_id = ? ORDER BY page_number DESC LIMIT 1", (book_id,))
    last_page_content = last_page_result[0][0] if last_page_result else None

    try:
        message_text = f"✍️ در حال نوشتن صفحه {next_page} از کتاب «{book_name}»\n\n"

        if last_page_content:
            # نمایش بخشی از آخرین صفحه برای الهام
            preview = last_page_content[:100] + "..." if len(
                last_page_content) > 100 else last_page_content
            message_text += f"📖 صفحه قبل: \"{preview}\"\n\n"

        message_text += (
            f"می‌تونی از این فرمت‌ها استفاده کنی:\n"
            f"**متن بولد**\n"
            f"*متن ایتالیک*\n"
            f"||متن اسپویلر||\n\n"
            f"📝 حداکثر ۳۹۰۰ کاراکتر\n"
            f"⏰ برای پایان «پایان» رو بفرست"
        )

        bot.edit_message_text(
            message_text,
            uid, call.message.message_id
        )
    except:
        bot.send_message(uid, message_text)


@bot.callback_query_handler(func=lambda call: call.data.startswith("book_full_view_"))
def book_full_view_handler(call):
    """نمایش تمام صفحات کتاب به صورت پیوسته"""
    uid = call.message.chat.id
    book_id = int(call.data.split("_")[3])

    try:
        # دریافت اطلاعات کتاب
        book_info = safe_execute_book_db(
            "SELECT book_name FROM user_books WHERE id = ?", (book_id,))
        if not book_info:
            bot.answer_callback_query(call.id, "❌ کتاب پیدا نشد!")
            return

        book_name = book_info[0][0]

        # دریافت تمام صفحات
        pages_result = safe_execute_book_db("""
            SELECT page_number, content, author_id, created_at 
            FROM book_pages 
            WHERE book_id = ? 
            ORDER BY page_number ASC
        """, (book_id,))

        if not pages_result:
            bot.answer_callback_query(call.id, "❌ این کتاب صفحه‌ای ندارد!")
            return

        # ساخت متن کامل کتاب
        full_text = f"📖 **کتاب کامل: {book_name}**\n\n"
        full_text += "=" * 30 + "\n\n"

        for page_number, content, author_id, created_at in pages_result:
            author_name = get_user_name(author_id)
            created_dt = datetime.fromisoformat(created_at)
            created_str = created_dt.strftime("%Y/%m/%d")

            full_text += f"**صفحه {page_number}** - ✍️ {author_name} - 📅 {created_str}\n\n"
            full_text += f"{content}\n\n"
            full_text += "-" * 20 + "\n\n"

        # اگر متن خیلی طولانی شد، آن را تقسیم می‌کنیم
        if len(full_text) > 4000:
            parts = [full_text[i:i+4000]
                     for i in range(0, len(full_text), 4000)]
            for i, part in enumerate(parts):
                if i == 0:
                    bot.send_message(uid, part, parse_mode="Markdown")
                else:
                    bot.send_message(uid, part, parse_mode="Markdown")
        else:
            bot.send_message(uid, full_text, parse_mode="Markdown")

        # ارسال منوی مدیریت
        markup = InlineKeyboardMarkup()

        # ✅ اضافه کردن گزینه "افزودن صفحه" در این منو هم
        next_author, next_page = get_writing_turn(book_id)
        if next_author == uid:
            markup.row(InlineKeyboardButton("📝 افزودن صفحه جدید",
                       callback_data=f"book_add_page_{book_id}"))

        markup.row(
            InlineKeyboardButton("📖 مشاهده صفحه‌ای",
                                 callback_data=f"book_view_{book_id}"),
            InlineKeyboardButton(
                "📚 کتاب‌های من", callback_data="book_my_books")
        )
        markup.row(InlineKeyboardButton(
            "🏠 منوی اصلی", callback_data="book_menu"))

        bot.send_message(uid, "🎯 چه کاری می‌خواهی انجام دهی؟",
                         reply_markup=markup)

    except Exception as e:
        bot.answer_callback_query(call.id, "❌ خطا در نمایش کتاب!")


@bot.callback_query_handler(func=lambda call: call.data.startswith("book_chapters_"))
def book_chapters_handler(call):
    """نمایش لیست فصل‌های کتاب"""
    uid = call.message.chat.id
    book_id = int(call.data.split("_")[2])

    try:
        # دریافت اطلاعات کتاب
        book_info = safe_execute_book_db(
            "SELECT book_name FROM user_books WHERE id = ?", (book_id,))
        book_name = book_info[0][0] if book_info else "کتاب"

        # دریافت فصل‌ها
        chapters_result = safe_execute_book_db("""
            SELECT bc.id, bc.chapter_number, bc.chapter_name, bc.chapter_description,
                   COUNT(bp.id) as page_count
            FROM book_chapters bc 
            LEFT JOIN book_pages bp ON bc.id = bp.chapter_id
            WHERE bc.book_id = ?
            GROUP BY bc.id
            ORDER BY bc.chapter_number
        """, (book_id,))

        if not chapters_result:
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("➕ افزودن فصل اول",
                       callback_data=f"book_add_chapter_{book_id}"))
            markup.row(InlineKeyboardButton(
                "🔙 بازگشت", callback_data=f"book_view_{book_id}"))

            bot.edit_message_text(
                f"📖 {book_name}\n\n"
                "📚 این کتاب هنوز فصلی ندارد!\n"
                "می‌تونی اولین فصل رو اضافه کنی:",
                uid, call.message.message_id,
                reply_markup=markup
            )
            return

        text = f"📖 {book_name}\n\n"
        text += "📚 **فصل‌های کتاب:**\n\n"

        markup = InlineKeyboardMarkup()

        for chapter_id, chapter_number, chapter_name, chapter_desc, page_count in chapters_result:
            # اطلاعات فصل
            desc_preview = chapter_desc[:30] + "..." if chapter_desc and len(
                chapter_desc) > 30 else chapter_desc or "بدون توضیح"
            text += f"**فصل {chapter_number}: {chapter_name}**\n"
            text += f"📄 {page_count} صفحه | {desc_preview}\n\n"

            # دکمه‌های هر فصل
            markup.row(
                InlineKeyboardButton(
                    f"📖 فصل {chapter_number}", callback_data=f"book_chapter_{chapter_id}"),
                InlineKeyboardButton(
                    f"✏️ ویرایش", callback_data=f"book_edit_chapter_{chapter_id}")
            )

        # دکمه‌های مدیریت
        markup.row(
            InlineKeyboardButton("➕ افزودن فصل جدید",
                                 callback_data=f"book_add_chapter_{book_id}"),
            InlineKeyboardButton(
                "📖 مشاهده کتاب", callback_data=f"book_view_{book_id}")
        )
        markup.row(InlineKeyboardButton(
            "🔙 بازگشت", callback_data=f"book_view_{book_id}"))

        bot.edit_message_text(
            text,
            uid, call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )

    except Exception as e:
        print(f"❌ خطا در book_chapters_handler: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در نمایش فصل‌ها!")


@bot.callback_query_handler(func=lambda call: call.data.startswith("book_add_chapter_"))
def book_add_chapter_handler(call):
    """شروع فرآیند افزودن فصل جدید"""
    uid = call.message.chat.id
    book_id = int(call.data.split("_")[3])

    user_state[uid] = f"book_waiting_chapter_name_{book_id}"
    temp_data[uid] = {"book_id": book_id}

    # پیدا کردن شماره فصل بعدی
    last_chapter_result = safe_execute_book_db(
        "SELECT MAX(chapter_number) FROM book_chapters WHERE book_id = ?", (book_id,))
    next_chapter_number = (last_chapter_result[0][0] or 0) + 1

    temp_data[uid]["next_chapter_number"] = next_chapter_number

    bot.edit_message_text(
        f"📚 **افزودن فصل جدید**\n\n"
        f"📖 شماره فصل: {next_chapter_number}\n\n"
        f"✏️ نام فصل جدید رو وارد کن:",
        uid, call.message.message_id,
        parse_mode="Markdown"
    )


@bot.message_handler(func=lambda m: user_state.get(m.chat.id, "").startswith("book_waiting_chapter_name_"))
def book_chapter_name_handler(message):
    """دریافت نام فصل جدید"""
    uid = message.chat.id
    state = user_state.get(uid, "")

    if not state.startswith("book_waiting_chapter_name_"):
        return

    book_id = temp_data[uid]["book_id"]
    next_chapter_number = temp_data[uid]["next_chapter_number"]

    chapter_name = message.text.strip()

    if len(chapter_name) < 2:
        bot.send_message(uid, "❌ نام فصل باید حداقل ۲ حرف داشته باشد!")
        return

    if len(chapter_name) > 50:
        bot.send_message(
            uid, "❌ نام فصل خیلی طولانی است! حداکثر ۵۰ کاراکتر مجاز است.")
        return

    temp_data[uid]["chapter_name"] = chapter_name
    user_state[uid] = f"book_waiting_chapter_desc_{book_id}"

    bot.send_message(
        uid,
        f"✅ نام فصل ثبت شد: «{chapter_name}»\n\n"
        f"📝 می‌خوای توضیحی برای این فصل بنویسی؟ (اختیاری)\n"
        f"یا «رد» رو بفرست تا از این مرحله رد شی."
    )


@bot.message_handler(func=lambda m: user_state.get(m.chat.id, "").startswith("book_waiting_chapter_desc_"))
def book_chapter_desc_handler(message):
    """دریافت توضیحات فصل"""
    uid = message.chat.id
    state = user_state.get(uid, "")

    if not state.startswith("book_waiting_chapter_desc_"):
        return

    book_id = temp_data[uid]["book_id"]
    chapter_name = temp_data[uid]["chapter_name"]
    next_chapter_number = temp_data[uid]["next_chapter_number"]

    chapter_desc = message.text.strip()

    if chapter_desc.lower() in ["رد", "skip", "no", "نه"]:
        chapter_desc = ""

    if chapter_desc and len(chapter_desc) > 200:
        bot.send_message(
            uid, "❌ توضیحات خیلی طولانی است! حداکثر ۲۰۰ کاراکتر مجاز است.")
        return

    # ذخیره فصل در دیتابیس
    try:
        result = safe_execute_book_db(
            "INSERT INTO book_chapters (book_id, chapter_number, chapter_name, chapter_description) VALUES (?, ?, ?, ?)",
            (book_id, next_chapter_number, chapter_name, chapter_desc)
        )

        if result is None:
            bot.send_message(uid, "❌ خطا در ایجاد فصل!")
            return

        chapter_id = safe_execute_book_db("SELECT last_insert_rowid()")[0][0]

        # پاکسازی state
        user_state.pop(uid, None)
        temp_data.pop(uid, None)

        # پیام موفقیت
        success_text = f"🎉 **فصل جدید ایجاد شد!**\n\n"
        success_text += f"📚 **فصل {next_chapter_number}: {chapter_name}**\n"
        if chapter_desc:
            success_text += f"📝 {chapter_desc}\n\n"
        success_text += "✅ حالا می‌تونی صفحات این فصل رو بنویسی!"

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("📝 افزودن صفحه به این فصل",
                                 callback_data=f"book_add_page_{book_id}"),
            InlineKeyboardButton(
                "📚 مشاهده فصل‌ها", callback_data=f"book_chapters_{book_id}")
        )
        markup.row(InlineKeyboardButton("📖 مشاهده کتاب",
                   callback_data=f"book_view_{book_id}"))

        bot.send_message(uid, success_text,
                         reply_markup=markup, parse_mode="Markdown")

    except Exception as e:
        print(f"❌ خطا در ایجاد فصل: {e}")
        bot.send_message(uid, "❌ خطا در ایجاد فصل!")
        user_state.pop(uid, None)
        temp_data.pop(uid, None)


@bot.callback_query_handler(func=lambda call: call.data.startswith("book_chapter_"))
def book_chapter_view_handler(call):
    """مشاهده اولین صفحه یک فصل"""
    uid = call.message.chat.id
    chapter_id = int(call.data.split("_")[2])

    try:
        # دریافت اطلاعات فصل و کتاب
        chapter_info = safe_execute_book_db(
            "SELECT book_id, chapter_number FROM book_chapters WHERE id = ?", (chapter_id,))
        if not chapter_info:
            bot.answer_callback_query(call.id, "❌ فصل پیدا نشد!")
            return

        book_id, chapter_number = chapter_info[0]

        # پیدا کردن اولین صفحه این فصل
        first_page_result = safe_execute_book_db(
            "SELECT MIN(page_number) FROM book_pages WHERE chapter_id = ?", (chapter_id,))
        first_page = first_page_result[0][0] if first_page_result and first_page_result[0][0] else 1

        # نمایش اولین صفحه فصل
        book_show_page(uid, book_id, first_page, call.message.message_id)

    except Exception as e:
        print(f"❌ خطا در book_chapter_view_handler: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در نمایش فصل!")


@bot.callback_query_handler(func=lambda call: call.data.startswith("book_next_chapter_"))
def book_next_chapter_handler(call):
    """پرش به فصل بعدی"""
    uid = call.message.chat.id
    book_id = int(call.data.split("_")[3])

    try:
        # پیدا کردن فصل فعلی
        current_chapter_result = safe_execute_book_db("""
            SELECT bc.chapter_number 
            FROM book_chapters bc 
            WHERE bc.book_id = ? AND bc.id = (
                SELECT chapter_id FROM book_pages WHERE book_id = ? ORDER BY page_number DESC LIMIT 1
            )
        """, (book_id, book_id))

        if not current_chapter_result:
            bot.answer_callback_query(call.id, "❌ فصل فعلی پیدا نشد!")
            return

        current_chapter = current_chapter_result[0][0]
        next_chapter = current_chapter + 1

        # پیدا کردن فصل بعدی
        next_chapter_result = safe_execute_book_db(
            "SELECT id FROM book_chapters WHERE book_id = ? AND chapter_number = ?", (book_id, next_chapter))
        if not next_chapter_result:
            bot.answer_callback_query(call.id, "❌ فصل بعدی وجود ندارد!")
            return

        next_chapter_id = next_chapter_result[0][0]

        # پیدا کردن اولین صفحه فصل بعدی
        first_page_result = safe_execute_book_db(
            "SELECT MIN(page_number) FROM book_pages WHERE chapter_id = ?", (next_chapter_id,))
        first_page = first_page_result[0][0] if first_page_result and first_page_result[0][0] else 1

        # نمایش اولین صفحه فصل بعدی
        book_show_page(uid, book_id, first_page, call.message.message_id)

    except Exception as e:
        print(f"❌ خطا در book_next_chapter_handler: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در پرش به فصل بعدی!")


@bot.callback_query_handler(func=lambda call: call.data.startswith("book_prev_chapter_"))
def book_prev_chapter_handler(call):
    """پرش به فصل قبلی"""
    uid = call.message.chat.id
    book_id = int(call.data.split("_")[3])

    try:
        # پیدا کردن فصل فعلی
        current_chapter_result = safe_execute_book_db("""
            SELECT bc.chapter_number 
            FROM book_chapters bc 
            WHERE bc.book_id = ? AND bc.id = (
                SELECT chapter_id FROM book_pages WHERE book_id = ? ORDER BY page_number DESC LIMIT 1
            )
        """, (book_id, book_id))

        if not current_chapter_result:
            bot.answer_callback_query(call.id, "❌ فصل فعلی پیدا نشد!")
            return

        current_chapter = current_chapter_result[0][0]
        prev_chapter = current_chapter - 1

        if prev_chapter < 1:
            bot.answer_callback_query(call.id, "❌ این اولین فصل است!")
            return

        # پیدا کردن فصل قبلی
        prev_chapter_result = safe_execute_book_db(
            "SELECT id FROM book_chapters WHERE book_id = ? AND chapter_number = ?", (book_id, prev_chapter))
        if not prev_chapter_result:
            bot.answer_callback_query(call.id, "❌ فصل قبلی وجود ندارد!")
            return

        prev_chapter_id = prev_chapter_result[0][0]

        # پیدا کردن اولین صفحه فصل قبلی
        first_page_result = safe_execute_book_db(
            "SELECT MIN(page_number) FROM book_pages WHERE chapter_id = ?", (prev_chapter_id,))
        first_page = first_page_result[0][0] if first_page_result and first_page_result[0][0] else 1

        # نمایش اولین صفحه فصل قبلی
        book_show_page(uid, book_id, first_page, call.message.message_id)

    except Exception as e:
        print(f"❌ خطا در book_prev_chapter_handler: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در پرش به فصل قبلی!")


#################
#################
## Special Message##
#################
#################


def special_messages_menu():
    """منوی پیام‌های ویژه"""
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🔐 پیام رمزگذاری شده",
               callback_data="special_encrypted"))
    markup.row(InlineKeyboardButton("⏰ پیام زمان‌دار",
               callback_data="special_scheduled"))
    markup.row(InlineKeyboardButton(
        "🎁 پیام رمز+زمان", callback_data="special_combo"))
    markup.row(InlineKeyboardButton("📋 پیام‌های من",
               callback_data="special_my_messages"))
    markup.row(InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main"))
    return markup


@bot.callback_query_handler(func=lambda call: call.data == "special_messages")
def special_messages_handler(call):
    """ورود به بخش پیام‌های ویژه"""
    uid = call.message.chat.id

    # بررسی اتصال به پارتنر
    partner_id = get_user_partner(uid)
    if not partner_id:
        bot.answer_callback_query(
            call.id, "❌ برای ارسال پیام ویژه باید به پارتنرت متصل باشی!")
        return

    # ایجاد دیتابیس اگر وجود ندارد
    setup_special_messages_db()

    try:
        bot.edit_message_text(
            "🎁 **پیام‌های ویژه**\n\n"
            "می‌تونی پیام‌های خاص و رمزگذاری شده برای پارتنرت ارسال کنی!\n"
            "کدام نوع پیام رو می‌خوای ایجاد کنی؟",
            uid, call.message.message_id,
            reply_markup=special_messages_menu(),
            parse_mode="Markdown"
        )
    except:
        bot.send_message(
            uid,
            "🎁 **پیام‌های ویژه**\n\n"
            "می‌تونی پیام‌های خاص و رمزگذاری شده برای پارتنرت ارسال کنی!\n"
            "کدام نوع پیام رو می‌خوای ایجاد کنی؟",
            reply_markup=special_messages_menu(),
            parse_mode="Markdown"
        )


@bot.callback_query_handler(func=lambda call: call.data == "special_encrypted")
def special_encrypted_handler(call):
    """شروع ایجاد پیام رمزگذاری شده"""
    uid = call.message.chat.id

    user_state[uid] = "special_waiting_title"
    temp_data[uid] = {
        "message_type": "encrypted",
        "encryption_type": None,
        "encryption_key": None
    }

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(
        "🔐 رمز عبور", callback_data="enc_type_password"))
    markup.row(InlineKeyboardButton("🔢 پین کد", callback_data="enc_type_pin"))
    markup.row(InlineKeyboardButton(
        "🔙 بازگشت", callback_data="special_messages"))

    try:
        bot.edit_message_text(
            "🔐 **پیام رمزگذاری شده**\n\n"
            "اول نوع رمزگذاری رو انتخاب کن:",
            uid, call.message.message_id,
            reply_markup=markup
        )
    except:
        bot.send_message(
            uid,
            "🔐 **پیام رمزگذاری شده**\n\n"
            "اول نوع رمزگذاری رو انتخاب کن:",
            reply_markup=markup
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("enc_type_"))
def encryption_type_handler(call):
    """انتخاب نوع رمزگذاری"""
    uid = call.message.chat.id

    enc_type = call.data.split("_")[2]  # password یا pin
    temp_data[uid]["encryption_type"] = enc_type

    if enc_type == "password":
        user_state[uid] = "special_waiting_password"
        message_text = "🔐 **رمز عبور**\n\nیک رمز عبور حداقل ۲ حرفی انتخاب کن:"

        try:
            bot.edit_message_text(
                message_text,
                uid, call.message.message_id
            )
        except:
            bot.send_message(uid, message_text)

    else:  # pin
        # برای پین، مستقیماً کیبورد نمایش داده شود
        user_state[uid] = "special_waiting_pin"
        temp_data[uid]["current_pin"] = ""

        try:
            bot.edit_message_text(
                "🔢 **پین کد**\n\nپین کد مورد نظرت رو با کیبورد زیر وارد کن:",
                uid, call.message.message_id,
                reply_markup=create_pin_keyboard()
            )
        except:
            bot.send_message(
                uid,
                "🔢 **پین کد**\n\nپین کد مورد نظرت رو با کیبورد زیر وارد کن:",
                reply_markup=create_pin_keyboard()
            )


def create_pin_keyboard(current_pin=""):
    """ایجاد کیبورد برای وارد کردن پین"""
    markup = InlineKeyboardMarkup()

    # ردیف‌های اعداد
    markup.row(
        InlineKeyboardButton("1", callback_data="pin_1"),
        InlineKeyboardButton("2", callback_data="pin_2"),
        InlineKeyboardButton("3", callback_data="pin_3")
    )
    markup.row(
        InlineKeyboardButton("4", callback_data="pin_4"),
        InlineKeyboardButton("5", callback_data="pin_5"),
        InlineKeyboardButton("6", callback_data="pin_6")
    )
    markup.row(
        InlineKeyboardButton("7", callback_data="pin_7"),
        InlineKeyboardButton("8", callback_data="pin_8"),
        InlineKeyboardButton("9", callback_data="pin_9")
    )
    markup.row(
        InlineKeyboardButton("0", callback_data="pin_0"),
        InlineKeyboardButton("⌫ حذف", callback_data="pin_delete")
    )

    # دکمه تأیید فقط اگر پین وارد شده باشد
    if current_pin:
        markup.row(InlineKeyboardButton(
            f"✅ تأیید ({len(current_pin)} رقم)", callback_data="pin_confirm"))

    return markup


@bot.callback_query_handler(func=lambda call: user_state.get(call.message.chat.id) == "special_waiting_pin")
def pin_creation_handler(call):
    """مدیریت ورود پین در مرحله ساخت پیام"""
    uid = call.message.chat.id

    if "current_pin" not in temp_data[uid]:
        temp_data[uid]["current_pin"] = ""

    current_pin = temp_data[uid]["current_pin"]
    action = call.data.split("_")[1]

    if action == "delete":
        # حذف آخرین رقم
        if current_pin:
            current_pin = current_pin[:-1]
            temp_data[uid]["current_pin"] = current_pin

    elif action == "confirm":
        # تأیید پین
        if len(current_pin) >= 1:
            temp_data[uid]["encryption_key"] = current_pin
            user_state[uid] = "special_waiting_title"

            try:
                bot.edit_message_text(
                    f"✅ پین کد ثبت شد: {'*' * len(current_pin)}\n\n"
                    f"📝 حالا عنوان پیام رو وارد کن:",
                    uid, call.message.message_id
                )
            except:
                bot.send_message(
                    uid,
                    f"✅ پین کد ثبت شد: {'*' * len(current_pin)}\n\n"
                    f"📝 حالا عنوان پیام رو وارد کن:"
                )
            return
        else:
            bot.answer_callback_query(
                call.id, "❌ پین کد باید حداقل ۱ رقم باشد!")
            return
    else:
        # اضافه کردن رقم
        if len(current_pin) < 10:  # حداکثر ۱۰ رقم
            current_pin += action
            temp_data[uid]["current_pin"] = current_pin

    # نمایش پین فعلی
    display_pin = '*' * len(current_pin) if current_pin else "---"

    try:
        bot.edit_message_text(
            f"🔢 **پین کد**\n\n"
            f"پین فعلی: {display_pin}\n\n"
            f"اعداد رو انتخاب کن (حداقل ۱ رقم):",
            uid, call.message.message_id,
            reply_markup=create_pin_keyboard(current_pin)
        )
    except Exception as e:
        print(f"خطا در ویرایش پیام: {e}")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "special_waiting_password")
def special_password_handler(message):
    """دریافت رمز عبور"""
    uid = message.chat.id

    password = message.text.strip()
    if len(password) < 2:
        bot.send_message(uid, "❌ رمز عبور باید حداقل ۲ حرف داشته باشد!")
        return

    temp_data[uid]["encryption_key"] = password
    user_state[uid] = "special_waiting_title"

    bot.send_message(
        uid,
        f"✅ رمز عبور ثبت شد!\n\n"
        f"📝 حالا عنوان پیام رو وارد کن:"
    )


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "special_waiting_title")
def special_title_handler(message):
    """دریافت عنوان پیام ویژه"""
    uid = message.chat.id

    title = message.text.strip()
    if len(title) < 2:
        bot.send_message(uid, "❌ عنوان باید حداقل ۲ حرف داشته باشد!")
        return

    temp_data[uid]["title"] = title
    user_state[uid] = "special_waiting_message"

    bot.send_message(
        uid,
        f"✅ عنوان ثبت شد: {title}\n\n"
        f"📝 حالا متن پیام ویژه‌ات رو وارد کن:"
    )


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "special_waiting_message")
def special_message_handler(message):
    """دریافت متن پیام ویژه"""
    uid = message.chat.id

    message_text = message.text.strip()
    if len(message_text) < 5:
        bot.send_message(uid, "❌ متن پیام باید حداقل ۵ حرف داشته باشد!")
        return

    temp_data[uid]["message_text"] = message_text

    # اگر پیام زمان‌دار نباشد، مستقیماً ذخیره می‌شود
    if temp_data[uid]["message_type"] == "encrypted":
        save_special_message(uid)
    else:
        user_state[uid] = "special_waiting_date"
        bot.send_message(
            uid,
            f"✅ متن پیام ثبت شد!\n\n"
            f"📅 حالا تاریخ ارسال رو وارد کن:\n"
            f"مثلاً: 1403-10-15 یا 2025-01-05"
        )


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "special_waiting_date")
def special_date_handler(message):
    """دریافت تاریخ ارسال پیام ویژه"""
    uid = message.chat.id

    try:
        gdate, jdate = parse_date_input(message.text)

        # بررسی اینکه تاریخ در آینده باشد
        if gdate < datetime.now().date():
            bot.send_message(uid, "❌ تاریخ باید در آینده باشد!")
            return

        temp_data[uid]["scheduled_date"] = gdate.isoformat()
        save_special_message(uid)

    except ValueError as e:
        bot.send_message(uid, f"❌ خطا در تاریخ: {str(e)}")


def save_special_message(uid):
    """ذخیره پیام ویژه در دیتابیس"""
    try:
        data = temp_data[uid]
        partner_id = get_user_partner(uid)

        if not partner_id:
            bot.send_message(uid, "❌ خطا: پارتنر پیدا نشد!")
            return

        # ذخیره در دیتابیس - متن اصلی ذخیره می‌شود
        conn = sqlite3.connect("special_messages.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO special_messages 
            (user_id, partner_id, message_type, title, message_text, 
             encryption_type, encryption_key, scheduled_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            uid, partner_id, data["message_type"], data["title"],
            data["message_text"],  # متن اصلی ذخیره می‌شود
            data.get("encryption_type"),
            data.get("encryption_key"),
            data.get("scheduled_date", datetime.now().date().isoformat())
        ))

        conn.commit()
        conn.close()

        # پیام موفقیت
        send_success_message(uid, data)

        # پاکسازی داده‌های موقت
        user_state.pop(uid, None)
        temp_data.pop(uid, None)

    except Exception as e:
        print(f"❌ خطا در ذخیره پیام ویژه: {e}")
        bot.send_message(uid, "❌ خطا در ذخیره پیام!")


def send_success_message(uid, data):
    """ارسال پیام تأیید ایجاد پیام ویژه"""
    message_type_fa = {
        "encrypted": "🔐 پیام رمزگذاری شده",
        "scheduled": "⏰ پیام زمان‌دار",
        "combo": "🎁 پیام رمز+زمان"
    }

    text = f"✅ **پیام ویژه ایجاد شد!**\n\n"
    text += f"📌 نوع: {message_type_fa[data['message_type']]}\n"
    text += f"📝 عنوان: {data['title']}\n"

    if data.get("encryption_type"):
        enc_type = "رمز عبور" if data["encryption_type"] == "password" else "پین کد"
        text += f"🔐 رمزگذاری: {enc_type}\n"

    if data.get("scheduled_date"):
        jdate = jdatetime.date.fromgregorian(
            date=datetime.strptime(data["scheduled_date"], "%Y-%m-%d").date())
        text += f"📅 تاریخ ارسال: {jdate.year}/{jdate.month:02d}/{jdate.day:02d}\n"

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(
            "📋 پیام‌های من", callback_data="special_my_messages"),
        InlineKeyboardButton("🎁 پیام جدید", callback_data="special_messages")
    )

    bot.send_message(uid, text, reply_markup=markup, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: call.data == "special_scheduled")
def special_scheduled_handler(call):
    """شروع ایجاد پیام زمان‌دار"""
    uid = call.message.chat.id

    user_state[uid] = "special_waiting_title"
    temp_data[uid] = {
        "message_type": "scheduled",
        "encryption_type": None
    }

    try:
        bot.edit_message_text(
            "⏰ **پیام زمان‌دار**\n\n"
            "پیامی که در تاریخ مشخصی برای پارتنرت ارسال می‌شود!\n\n"
            "📝 اول عنوان پیام رو وارد کن:",
            uid, call.message.message_id
        )
    except:
        bot.send_message(
            uid,
            "⏰ **پیام زمان‌دار**\n\n"
            "پیامی که در تاریخ مشخصی برای پارتنرت ارسال می‌شود!\n\n"
            "📝 اول عنوان پیام رو وارد کن:",
        )


@bot.callback_query_handler(func=lambda call: call.data == "special_combo")
def special_combo_handler(call):
    """شروع ایجاد پیام ترکیبی (رمز+زمان)"""
    uid = call.message.chat.id

    user_state[uid] = "special_waiting_title"
    temp_data[uid] = {
        "message_type": "combo",
        "encryption_type": None,
        "encryption_key": None
    }

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(
        "🔐 رمز عبور", callback_data="enc_type_password"))
    markup.row(InlineKeyboardButton("🔢 پین کد", callback_data="enc_type_pin"))
    markup.row(InlineKeyboardButton(
        "🔙 بازگشت", callback_data="special_messages"))

    try:
        bot.edit_message_text(
            "🎁 **پیام رمز+زمان**\n\n"
            "پیام رمزگذاری شده که در تاریخ مشخص ارسال می‌شود!\n\n"
            "اول نوع رمزگذاری رو انتخاب کن:",
            uid, call.message.message_id,
            reply_markup=markup
        )
    except:
        bot.send_message(
            uid,
            "🎁 **پیام رمز+زمان**\n\n"
            "پیام رمزگذاری شده که در تاریخ مشخص ارسال می‌شود!\n\n"
            "اول نوع رمزگذاری رو انتخاب کن:",
            reply_markup=markup
        )


@bot.callback_query_handler(func=lambda call: call.data == "special_my_messages")
def special_my_messages_handler(call):
    """نمایش لیست پیام‌های ویژه کاربر با قابلیت حذف"""
    uid = call.message.chat.id

    try:
        conn = sqlite3.connect("special_messages.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("""
            SELECT id, title, message_type, encryption_type, scheduled_date, is_sent, is_read
            FROM special_messages 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        """, (uid,))

        messages = cur.fetchall()
        conn.close()

        if not messages:
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton(
                "🎁 ایجاد پیام جدید", callback_data="special_messages"))
            markup.row(InlineKeyboardButton(
                "🔙 بازگشت", callback_data="special_messages"))

            try:
                bot.edit_message_text(
                    "📭 شما هنوز پیام ویژه‌ای ندارید!",
                    uid, call.message.message_id,
                    reply_markup=markup
                )
            except:
                bot.send_message(
                    uid, "📭 شما هنوز پیام ویژه‌ای ندارید!", reply_markup=markup)
            return

        text = "📋 **پیام‌های ویژه شما:**\n\n"
        markup = InlineKeyboardMarkup()

        for msg_id, title, msg_type, enc_type, scheduled_date, is_sent, is_read in messages:
            # آیکون وضعیت
            status_icon = "✅" if is_sent else "⏳"
            if is_sent and is_read:
                status_icon = "👁️"

            # نوع پیام
            type_icon = "🔐" if "encrypted" in msg_type else "⏰" if msg_type == "scheduled" else "🎁"

            # تاریخ
            if scheduled_date:
                gdate = datetime.strptime(scheduled_date, "%Y-%m-%d").date()
                jdate = jdatetime.date.fromgregorian(date=gdate)
                date_str = f"{jdate.year}/{jdate.month:02d}/{jdate.day:02d}"
            else:
                date_str = "فوری"

            text += f"{status_icon} {type_icon} {title} - {date_str}\n"

            # ✅ دکمه‌های مشاهده و حذف در یک ردیف
            markup.row(
                InlineKeyboardButton(
                    f"👀 {title[:12]}...", callback_data=f"view_special_{msg_id}"),
                InlineKeyboardButton(
                    f"🗑️ حذف", callback_data=f"delete_special_{msg_id}")
            )

        markup.row(InlineKeyboardButton(
            "🔙 بازگشت", callback_data="special_messages"))

        try:
            bot.edit_message_text(
                text,
                uid, call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except:
            bot.send_message(uid, text, reply_markup=markup,
                             parse_mode="Markdown")

    except Exception as e:
        print(f"❌ خطا در نمایش پیام‌ها: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در نمایش پیام‌ها!")


@bot.callback_query_handler(func=lambda call: call.data.startswith("view_special_"))
def view_special_message_handler(call):
    """نمایش جزئیات پیام ویژه با دکمه حذف"""
    uid = call.message.chat.id
    msg_id = int(call.data.split("_")[2])

    try:
        conn = sqlite3.connect("special_messages.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("""
            SELECT title, message_text, message_type, encryption_type, 
                   scheduled_date, is_sent, is_read, created_at
            FROM special_messages 
            WHERE id = ? AND user_id = ?
        """, (msg_id, uid))

        result = cur.fetchone()
        conn.close()

        if not result:
            bot.answer_callback_query(call.id, "❌ پیام پیدا نشد!")
            return

        (title, message_text, msg_type, enc_type,
         scheduled_date, is_sent, is_read, created_at) = result

        # ساخت متن نمایش
        text = f"📋 **جزئیات پیام ویژه**\n\n"
        text += f"📌 **عنوان:** {title}\n"

        # نوع پیام
        type_fa = {
            "encrypted": "🔐 رمزگذاری شده",
            "scheduled": "⏰ زمان‌دار",
            "combo": "🎁 رمز+زمان"
        }
        text += f"🎯 **نوع:** {type_fa.get(msg_type, msg_type)}\n"

        # وضعیت
        status_fa = "✅ ارسال شده" if is_sent else "⏳ در انتظار ارسال"
        if is_sent and is_read:
            status_fa = "👁️ خوانده شده"
        text += f"📮 **وضعیت:** {status_fa}\n"

        # رمزگذاری
        if enc_type:
            enc_fa = "رمز عبور" if enc_type == "password" else "پین کد"
            text += f"🔐 **رمزگذاری:** {enc_fa}\n"

        # تاریخ‌ها
        if scheduled_date:
            gdate = datetime.strptime(scheduled_date, "%Y-%m-%d").date()
            jdate = jdatetime.date.fromgregorian(date=gdate)
            text += f"📅 **تاریخ ارسال:** {jdate.year}/{jdate.month:02d}/{jdate.day:02d}\n"

        created_dt = datetime.fromisoformat(created_at)
        created_str = created_dt.strftime("%Y/%m/%d %H:%M")
        text += f"🕒 **تاریخ ایجاد:** {created_str}\n\n"

        # متن پیام
        if enc_type and not is_sent:
            text += f"📝 **متن پیام:** \n🔒 *مخفی - پس از ارسال قابل مشاهده است*\n"
        else:
            text += f"📝 **متن پیام:** \n{message_text}\n"

        markup = InlineKeyboardMarkup()

        # دکمه‌های اقدام
        if not is_sent:
            markup.row(
                InlineKeyboardButton(
                    "✏️ ویرایش", callback_data=f"edit_special_{msg_id}"),
                InlineKeyboardButton(
                    "🗑️ حذف", callback_data=f"delete_special_{msg_id}")
            )
        else:
            text += f"\n⚠️ *پیام‌های ارسال شده قابل حذف نیستند*\n"

        markup.row(InlineKeyboardButton("📋 بازگشت به لیست",
                   callback_data="special_my_messages"))

        try:
            bot.edit_message_text(
                text,
                uid, call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except:
            bot.send_message(uid, text, reply_markup=markup,
                             parse_mode="Markdown")

    except Exception as e:
        print(f"❌ خطا در مشاهده پیام: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در مشاهده پیام!")


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_special_"))
def delete_special_message_handler(call):
    """حذف پیام ویژه با بررسی وضعیت"""
    uid = call.message.chat.id
    msg_id = int(call.data.split("_")[2])

    try:
        conn = sqlite3.connect("special_messages.db", check_same_thread=False)
        cur = conn.cursor()
        cur.execute(
            "SELECT title, is_sent FROM special_messages WHERE id = ? AND user_id = ?", (msg_id, uid))
        result = cur.fetchone()
        conn.close()

        if not result:
            bot.answer_callback_query(call.id, "❌ پیام پیدا نشد!")
            return

        title, is_sent = result

        if is_sent:
            bot.answer_callback_query(
                call.id, "❌ پیام ارسال شده قابل حذف نیست!")
            return

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton(
                "✅ بله، حذف کن", callback_data=f"confirm_delete_special_{msg_id}"),
            InlineKeyboardButton(
                "❌ خیر", callback_data=f"view_special_{msg_id}")
        )

        bot.edit_message_text(
            f"🗑️ **حذف پیام**\n\n"
            f"📌 **عنوان:** {title}\n\n"
            f"⚠️ آیا مطمئنی می‌خوای این پیام رو حذف کنی؟\n"
            f"❗ این عمل قابل بازگشت نیست!",
            uid, call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )

    except Exception as e:
        print(f"❌ خطا در حذف پیام: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در پردازش!")


@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_delete_special_"))
def confirm_delete_special_handler(call):
    """تأیید نهایی حذف پیام ویژه"""
    uid = call.message.chat.id
    msg_id = int(call.data.split("_")[3])

    try:
        conn = sqlite3.connect("special_messages.db", check_same_thread=False)
        cur = conn.cursor()

        # بررسی مجدد مالکیت
        cur.execute(
            "SELECT title FROM special_messages WHERE id = ? AND user_id = ?", (msg_id, uid))
        result = cur.fetchone()

        if not result:
            bot.answer_callback_query(call.id, "❌ پیام پیدا نشد!")
            conn.close()
            return

        title = result[0]

        # حذف پیام
        cur.execute(
            "DELETE FROM special_messages WHERE id = ? AND user_id = ?", (msg_id, uid))
        deleted_count = cur.rowcount
        conn.commit()
        conn.close()

        if deleted_count > 0:
            bot.answer_callback_query(call.id, f"✅ پیام '{title}' حذف شد!")
            # بازگشت به لیست پیام‌ها
            special_my_messages_handler(call)
        else:
            bot.answer_callback_query(call.id, "❌ خطا در حذف پیام!")

    except Exception as e:
        print(f"❌ خطا در حذف پیام: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در حذف پیام!")


@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_delete_special_"))
def confirm_delete_special_handler(call):
    """تأیید نهایی حذف پیام ویژه"""
    uid = call.message.chat.id
    msg_id = int(call.data.split("_")[3])

    try:
        conn = sqlite3.connect("special_messages.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute(
            "DELETE FROM special_messages WHERE id = ? AND user_id = ?", (msg_id, uid))
        conn.commit()
        conn.close()

        bot.answer_callback_query(call.id, "✅ پیام حذف شد!")
        special_my_messages_handler(call)  # بازگشت به لیست

    except Exception as e:
        print(f"❌ خطا در حذف پیام: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در حذف پیام!")


def send_scheduled_special_messages():
    """ارسال خودکار پیام‌های زمان‌دار"""
    try:
        conn = sqlite3.connect("special_messages.db", check_same_thread=False)
        cur = conn.cursor()

        # پیدا کردن پیام‌های زمان‌دار که باید ارسال شوند
        cur.execute("""
            SELECT id, user_id, partner_id, title, message_text, 
                   message_type, encryption_type, encryption_key
            FROM special_messages 
            WHERE scheduled_date <= date('now') 
            AND is_sent = 0
        """)

        messages = cur.fetchall()

        for msg in messages:
            msg_id, user_id, partner_id, title, message_text, msg_type, enc_type, enc_key = msg

            try:
                # ارسال پیام به پارتنر
                send_special_to_partner(
                    partner_id, user_id, title, message_text, msg_type, enc_type, enc_key)

                # به روزرسانی وضعیت
                cur.execute("""
                    UPDATE special_messages 
                    SET is_sent = 1, sent_at = datetime('now')
                    WHERE id = ?
                """, (msg_id,))

                conn.commit()

                print(f"✅ پیام ویژه {msg_id} برای کاربر {partner_id} ارسال شد")

            except Exception as e:
                print(f"❌ خطا در ارسال پیام {msg_id}: {e}")
                continue

        conn.close()

    except Exception as e:
        print(f"❌ خطا در ارسال خودکار پیام‌ها: {e}")


def send_special_to_partner(partner_id, sender_id, title, message_text, msg_type, enc_type, enc_key):
    """ارسال پیام ویژه به پارتنر"""
    try:
        sender_name = get_user_name(sender_id)

        text = f"🎁 **پیام ویژه از {sender_name}**\n\n"
        text += f"📌 **عنوان:** {title}\n"

        if enc_type:
            # پیام رمزگذاری شده
            if enc_type == "password":
                text += f"🔐 **نوع:** رمز عبور\n\n"
                text += f"📝 **پیام رمزگذاری شده:**\n"
                text += f"🔒 این پیام با رمز عبور محافظت شده است.\n\n"
                text += f"💡 **برای مشاهده پیام، یکی از روش‌های زیر را استفاده کن:**\n"
                text += f"• دستور: `/decrypt {enc_key}`\n"
                text += f"• یا: `/decrypt` و سپس رمز را وارد کن"

            else:  # pin
                text += f"🔐 **نوع:** پین کد\n\n"
                text += f"📝 **پیام رمزگذاری شده:**\n"
                text += f"🔒 این پیام با پین کد محافظت شده است.\n\n"
                text += f"💡 **برای مشاهده پیام:**\n"
                text += f"• از دستور /pin استفاده کن\n"
                text += f"• یا پین '{enc_key}' را وارد کن"

        else:
            # پیام عادی
            text += f"📝 **پیام:**\n{message_text}"

        bot.send_message(partner_id, text, parse_mode="Markdown")

    except Exception as e:
        print(f"❌ خطا در ارسال به پارتنر: {e}")


def encrypt_message(message, key):
    """رمزگذاری ساده و قابل پیش‌بینی"""
    try:
        # نمایش یک پیام ثابت که به کاربر بفهماند پیام رمزگذاری شده
        key_preview = str(key)[:3] + "..." if len(str(key)) > 3 else str(key)
        return f"🔒 [این پیام با کلید '{key_preview}' رمزگذاری شده است. برای مشاهده از دستور /decrypt استفاده کن]"
    except:
        return "🔒 [پیام رمزگذاری شده]"


def decrypt_message(encrypted_message, key, original_message):
    """رمزگشایی - در واقع پیام اصلی را برمی‌گرداند"""
    try:
        return original_message
    except:
        return "❌ خطا در رمزگشایی!"


@bot.message_handler(commands=['decrypt'])
def decrypt_command_handler(message):
    """دستور رمزگشایی پیام"""
    uid = message.chat.id

    # بررسی اینکه آیا کلید همراه دستور آمده
    parts = message.text.split()
    if len(parts) >= 2:
        key = parts[1]
        decrypt_with_key(uid, key)
    else:
        user_state[uid] = "waiting_decryption_key"

        bot.send_message(
            uid,
            "🔓 **رمزگشایی پیام**\n\n"
            "💡 می‌تونی بینهایت بار رمز عبور رو اشتباه وارد کنی!\n\n"
            "لطفاً رمز عبوری که برای پیام تنظیم شده را وارد کن:\n\n"
            "📝 یا از دستور `/cancel` برای لغو استفاده کن",
            parse_mode="Markdown"
        )


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_decryption_key")
def handle_decryption_key(message):
    """دریافت کلید رمزگشایی - با امکان تلاش نامحدود"""
    uid = message.chat.id
    key = message.text.strip()
    decrypt_with_key(uid, key)


@bot.message_handler(commands=['pin'])
def pin_command_handler(message):
    """دستور وارد کردن پین - همیشه state جدید ایجاد می‌کند"""
    uid = message.chat.id

    # همیشه state جدید ایجاد کن
    user_state[uid] = "waiting_pin_input"
    temp_data[uid] = {"current_pin": ""}

    markup = create_pin_keyboard()

    bot.send_message(
        uid,
        "🔢 **ورود پین کد**\n\n"
        "💡 می‌تونی بینهایت بار پین رو اشتباه وارد کنی!\n\n"
        "پین کد پیام ویژه را وارد کن:",
        reply_markup=markup
    )


@bot.message_handler(commands=['cancel'])
def cancel_command_handler(message):
    """دستور لغو عملیات جاری"""
    uid = message.chat.id

    current_state = user_state.get(uid)

    if current_state in ["waiting_decryption_key", "waiting_pin_input"]:
        user_state.pop(uid, None)
        temp_data.pop(uid, None)
        bot.send_message(uid, "✅ عملیات رمزگشایی لغو شد.")
    else:
        bot.send_message(uid, "⚠️ هیچ عملیات رمزگشایی فعالی وجود ندارد.")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_decryption_key")
def decryption_key_handler(message):
    """دریافت کلید رمزگشایی"""
    uid = message.chat.id

    key = message.text.strip()

    # پیدا کردن پیام‌های رمزگذاری شده کاربر
    try:
        conn = sqlite3.connect("special_messages.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("""
            SELECT id, message_text, encryption_key 
            FROM special_messages 
            WHERE partner_id = ? AND encryption_type = 'password' AND is_sent = 1
            ORDER BY sent_at DESC LIMIT 1
        """, (uid,))

        result = cur.fetchone()
        conn.close()

        if not result:
            bot.send_message(uid, "❌ پیام رمزگذاری شده‌ای پیدا نشد!")
            user_state.pop(uid, None)
            return

        msg_id, encrypted_message, correct_key = result

        if key == correct_key:
            # رمزگشایی موفق
            decrypted_message = decrypt_message(encrypted_message, key)

            # به روزرسانی وضعیت خوانده شده
            conn = sqlite3.connect("special_messages.db",
                                   check_same_thread=False)
            cur = conn.cursor()
            cur.execute(
                "UPDATE special_messages SET is_read = 1 WHERE id = ?", (msg_id,))
            conn.commit()
            conn.close()

            bot.send_message(
                uid,
                f"✅ **رمزگشایی موفق!**\n\n"
                f"📝 **پیام اصلی:**\n{decrypted_message}",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(uid, "❌ رمز عبور نادرست! لطفاً دوباره تلاش کن.")

        user_state.pop(uid, None)

    except Exception as e:
        print(f"❌ خطا در رمزگشایی: {e}")
        bot.send_message(uid, "❌ خطا در پردازش رمزگشایی!")
        user_state.pop(uid, None)


@bot.callback_query_handler(func=lambda call: user_state.get(call.message.chat.id) == "waiting_pin_input")
def pin_decryption_handler(call):
    """بررسی پین برای رمزگشایی"""
    uid = call.message.chat.id

    if call.data == "pin_confirm":
        # تأیید پین وارد شده
        current_pin = temp_data[uid].get("current_pin", "")

        if not current_pin:
            bot.answer_callback_query(call.id, "❌ لطفاً پین را وارد کن!")
            return

        # پیدا کردن پیام مربوطه
        try:
            conn = sqlite3.connect("special_messages.db",
                                   check_same_thread=False)
            cur = conn.cursor()

            cur.execute("""
                SELECT id, message_text, encryption_key 
                FROM special_messages 
                WHERE partner_id = ? AND encryption_type = 'pin' AND is_sent = 1
                ORDER BY sent_at DESC LIMIT 1
            """, (uid,))

            result = cur.fetchone()
            conn.close()

            if not result:
                bot.answer_callback_query(call.id, "❌ پیام پین‌دار پیدا نشد!")
                return

            msg_id, encrypted_message, correct_pin = result

            if current_pin == correct_pin:
                # رمزگشایی موفق
                decrypted_message = decrypt_message(
                    encrypted_message, current_pin)

                # به روزرسانی وضعیت خوانده شده
                conn = sqlite3.connect(
                    "special_messages.db", check_same_thread=False)
                cur = conn.cursor()
                cur.execute(
                    "UPDATE special_messages SET is_read = 1 WHERE id = ?", (msg_id,))
                conn.commit()
                conn.close()

                bot.edit_message_text(
                    f"✅ **رمزگشایی موفق!**\n\n"
                    f"📝 **پیام اصلی:**\n{decrypted_message}",
                    uid, call.message.message_id,
                    parse_mode="Markdown"
                )
            else:
                bot.answer_callback_query(call.id, "❌ پین نادرست!")

            user_state.pop(uid, None)
            temp_data.pop(uid, None)

        except Exception as e:
            print(f"❌ خطا در رمزگشایی پین: {e}")
            bot.answer_callback_query(call.id, "❌ خطا در پردازش!")

    else:
        # مدیریت ورود پین (مشابه قبلی)
        if "current_pin" not in temp_data[uid]:
            temp_data[uid]["current_pin"] = ""

        current_pin = temp_data[uid]["current_pin"]
        action = call.data.split("_")[1]

        if action == "delete":
            if current_pin:
                current_pin = current_pin[:-1]
        else:
            if len(current_pin) < 10:
                current_pin += action

        temp_data[uid]["current_pin"] = current_pin

        # نمایش پین فعلی
        display_pin = '*' * len(current_pin) if current_pin else "---"

        try:
            bot.edit_message_text(
                f"🔢 **ورود پین کد**\n\n"
                f"پین فعلی: {display_pin}\n\n"
                f"اعداد رو انتخاب کن:",
                uid, call.message.message_id,
                reply_markup=create_pin_keyboard(current_pin)
            )
        except:
            pass


def special_messages_monitor():
    """نظارت و ارسال خودکار پیام‌های زمان‌دار"""
    while True:
        try:
            send_scheduled_special_messages()
            time.sleep(60)  # هر 1 دقیقه چک کن
        except Exception as e:
            print(f"❌ خطا در مانیتور پیام‌ها: {e}")
            time.sleep(300)  # در صورت خطا 5 دقیقه صبر کن


def start_special_messages_monitor():
    """شروع مانیتورینگ در background"""
    monitor_thread = threading.Thread(
        target=special_messages_monitor, daemon=True)
    monitor_thread.start()
    print("✅ مانیتور پیام‌های ویژه شروع شد")


def setup_special_messages_db():
    try:
        conn = sqlite3.connect("special_messages.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS special_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                partner_id INTEGER NOT NULL,
                message_type TEXT NOT NULL,
                title TEXT NOT NULL,
                message_text TEXT NOT NULL,
                encryption_type TEXT,
                encryption_key TEXT,
                scheduled_date TEXT NOT NULL,
                is_sent BOOLEAN DEFAULT 0,
                is_read BOOLEAN DEFAULT 0,
                sent_at TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()
        print(Fore.LIGHTYELLOW_EX + "✅ Special messages database created")
        return True
    except Exception as e:
        print(Fore.RED + f"❌ ERROR IN CREATING SPECIAL MESSAGES DATABASE: {e}")
        return False


@bot.callback_query_handler(func=lambda call: user_state.get(call.message.chat.id) == "special_waiting_pin" and call.data.startswith("pin_"))
def handle_pin_creation(call):
    pin_creation_handler(call)


@bot.callback_query_handler(func=lambda call: user_state.get(call.message.chat.id) == "waiting_pin_input" and call.data.startswith("pin_"))
def handle_pin_decryption(call):

    uid = call.message.chat.id

    if "current_pin" not in temp_data.get(uid, {}):
        temp_data[uid] = {"current_pin": ""}

    current_pin = temp_data[uid]["current_pin"]
    action = call.data.split("_")[1]

    if action == "delete":
        # حذف آخرین رقم
        if current_pin:
            current_pin = current_pin[:-1]
            temp_data[uid]["current_pin"] = current_pin

    elif action == "confirm":
        # تأیید پین
        if len(current_pin) >= 1:
            # بررسی پین
            check_pin_decryption(uid, current_pin, call.message.message_id)
            return
        else:
            bot.answer_callback_query(
                call.id, "❌ پین کد باید حداقل ۱ رقم باشد!")
            return
    else:
        # اضافه کردن رقم
        if len(current_pin) < 10:
            current_pin += action
            temp_data[uid]["current_pin"] = current_pin

    # نمایش پین فعلی
    display_pin = '*' * len(current_pin) if current_pin else "---"

    try:
        bot.edit_message_text(
            f"🔢 **ورود پین کد**\n\n"
            f"پین فعلی: {display_pin}\n\n"
            f"💡 می‌تونی بینهایت بار تلاش کنی!\n"
            f"اعداد رو انتخاب کن:",
            uid, call.message.message_id,
            reply_markup=create_pin_keyboard(current_pin)
        )
    except Exception as e:
        print(f"خطا در ویرایش پیام پین: {e}")


def check_pin_decryption(uid, entered_pin, message_id):
    """بررسی پین برای رمزگشایی - با امکان تلاش نامحدود"""
    try:
        conn = sqlite3.connect("special_messages.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("""
            SELECT id, title, message_text, encryption_key 
            FROM special_messages 
            WHERE partner_id = ? AND encryption_type = 'pin' AND is_sent = 1
            ORDER BY sent_at DESC LIMIT 1
        """, (uid,))

        result = cur.fetchone()
        conn.close()

        if not result:
            bot.edit_message_text(
                "❌ پیام پین‌دار پیدا نشد!",
                uid, message_id
            )
            return

        msg_id, title, original_message, correct_pin = result

        if entered_pin == correct_pin:
            # رمزگشایی موفق
            conn = sqlite3.connect("special_messages.db",
                                   check_same_thread=False)
            cur = conn.cursor()
            cur.execute(
                "UPDATE special_messages SET is_read = 1 WHERE id = ?", (msg_id,))
            conn.commit()
            conn.close()

            bot.edit_message_text(
                f"✅ **رمزگشایی موفق!**\n\n"
                f"📌 **عنوان:** {title}\n\n"
                f"📝 **پیام اصلی:**\n{original_message}",
                uid, message_id,
                parse_mode="Markdown"
            )

            # پاکسازی state و temp_data فقط در صورت موفقیت
            user_state.pop(uid, None)
            temp_data.pop(uid, None)

        else:
            # پین نادرست - state و temp_data باقی می‌مانند
            # پین را خالی می‌کنیم تا دوباره وارد کند
            temp_data[uid]["current_pin"] = ""

            bot.edit_message_text(
                f"❌ **پین نادرست!**\n\n"
                f"💡 می‌تونی دوباره پین رو وارد کنی!\n\n"
                f"پین جدید رو انتخاب کن:",
                uid, message_id,
                reply_markup=create_pin_keyboard()
            )

    except Exception as e:
        print(f"❌ خطا در رمزگشایی پین: {e}")
        bot.edit_message_text(
            "❌ خطا در پردازش! لطفاً دوباره تلاش کن.",
            uid, message_id
        )


################################################################################################################################################################################################################################################################################################################# ADMIN HANDLER######## #######################################################################################################################################################################################################################################################################


# ==================== پنل ادمین - تعریف کلاس‌ها ====================

class AdminPanel:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.admin_users = self.load_admin_users()
        self.setup_admin_database()

    def load_admin_users(self):
        """بارگذاری لیست ادمین‌ها"""
        try:
            with open("admin_users.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            default_admins = {
                # آیدی خودت رو اینجا بذار
                "8000307737": {"level": "superadmin", "name": "Developer"}
            }
            self.save_admin_users(default_admins)
            return default_admins

    def save_admin_users(self, admins):
        """ذخیره لیست ادمین‌ها"""
        with open("admin_users.json", "w", encoding="utf-8") as f:
            json.dump(admins, f, ensure_ascii=False, indent=2)

    def setup_admin_database(self):
        """ایجاد دیتابیس مدیریتی"""
        try:
            conn = sqlite3.connect("admin_panel.db", check_same_thread=False)
            cur = conn.cursor()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    action TEXT,
                    target TEXT,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            conn.close()
            print("✅ دیتابیس پنل ادمین ایجاد شد")
        except Exception as e:
            print(f"❌ خطا در ایجاد دیتابیس ادمین: {e}")

    def is_admin(self, user_id):
        """بررسی اینکه کاربر ادمین است یا نه"""
        return str(user_id) in self.admin_users

    def get_admin_level(self, user_id):
        """دریافت سطح دسترسی ادمین"""
        user_id_str = str(user_id)
        if user_id_str in self.admin_users:
            return self.admin_users[user_id_str].get("level", "admin")
        return None

    def log_admin_action(self, admin_id, action, target="", details=""):
        """ثبت لاگ فعالیت ادمین"""
        try:
            conn = sqlite3.connect("admin_panel.db", check_same_thread=False)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO admin_logs (admin_id, action, target, details) VALUES (?, ?, ?, ?)",
                (admin_id, action, target, details)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ خطا در ثبت لاگ ادمین: {e}")

# ==================== نمونه‌سازی پنل ادمین ====================

# این خطوط رو بعد از ایجاد bot اضافه کن


# ایجاد نمونه پنل ادمین
admin_panel = AdminPanel(bot)

# ==================== تابع نمایش داشبورد ====================


def show_admin_dashboard(uid, message_id):
    """نمایش داشبورد مدیریتی - نسخه ساده"""
    try:
        # آمار ساده کاربران
        conn = sqlite3.connect("relation_agent.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM users WHERE connection_status = 'connected'")
        connected_users = cur.fetchone()[0]

        cur.execute("SELECT gender, COUNT(*) FROM users GROUP BY gender")
        gender_stats = dict(cur.fetchall())

        conn.close()

        text = "📊 **داشبورد مدیریتی**\n\n"
        text += f"👥 کاربران کل: {total_users:,}\n"
        text += f"💑 کاربران متصل: {connected_users:,}\n"
        text += f"🚶 کاربران سینگل: {total_users - connected_users:,}\n\n"

        if gender_stats:
            text += f"👨 پسران: {gender_stats.get('مرد', 0):,}\n"
            text += f"👩 دختران: {gender_stats.get('زن', 0):,}\n\n"

        text += f"🕒 زمان سرور: {datetime.now().strftime('%H:%M:%S')}"

        bot.edit_message_text(
            text,
            uid, message_id,
            reply_markup=admin_main_menu(),
            parse_mode="Markdown"
        )

        admin_panel.log_admin_action(uid, "view_dashboard")

    except Exception as e:
        bot.edit_message_text(
            f"❌ خطا در بارگذاری داشبورد:\n{str(e)}",
            uid, message_id,
            reply_markup=admin_main_menu()
        )


def admin_user_management_menu():
    """منوی مدیریت کاربران"""
    markup = InlineKeyboardMarkup()

    # ردیف 1: آمار و لیست
    markup.row(
        InlineKeyboardButton(
            "📊 آمار کاربران", callback_data="admin_user_stats"),
        InlineKeyboardButton("👥 لیست کاربران", callback_data="admin_user_list")
    )

    # ردیف 2: جستجو و پیام
    markup.row(
        InlineKeyboardButton(
            "🔍 جستجوی کاربر", callback_data="admin_user_search"),
        InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast")
    )

    # ردیف 3: فیلترها
    markup.row(
        InlineKeyboardButton("👨 پسران", callback_data="admin_filter_male"),
        InlineKeyboardButton("👩 دختران", callback_data="admin_filter_female")
    )

    markup.row(
        InlineKeyboardButton(
            "💑 متصل‌ها", callback_data="admin_filter_connected"),
        InlineKeyboardButton("🚶 سینگل‌ها", callback_data="admin_filter_single")
    )

    markup.row(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main"))

    return markup


def admin_bot_management_menu():
    """منوی مدیریت ربات"""
    markup = InlineKeyboardMarkup()

    markup.row(
        InlineKeyboardButton("🟢 روشن کردن", callback_data="admin_bot_start"),
        InlineKeyboardButton("🔴 خاموش کردن", callback_data="admin_bot_stop")
    )

    markup.row(
        InlineKeyboardButton(
            "🛠️ حالت تعمیر", callback_data="admin_bot_maintenance"),
        InlineKeyboardButton("🔄 ریستارت", callback_data="admin_bot_restart")
    )

    markup.row(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main"))

    return markup


def admin_server_management_menu():
    """منوی مدیریت سرور"""
    markup = InlineKeyboardMarkup()

    markup.row(
        InlineKeyboardButton(
            "📊 وضعیت سرور", callback_data="admin_server_status"),
        InlineKeyboardButton("💾 حجم دیتابیس", callback_data="admin_db_size")
    )

    markup.row(
        InlineKeyboardButton("🧹 بهینه‌سازی", callback_data="admin_optimize"),
        InlineKeyboardButton("📋 لاگ‌ها", callback_data="admin_logs")
    )

    markup.row(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main"))

    return markup


def admin_main_menu():
    """منوی اصلی ادمین"""
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(
        "👥 مدیریت کاربران", callback_data="admin_users"))
    markup.row(InlineKeyboardButton(
        "📢 پیام همگانی", callback_data="admin_broadcast"))
    markup.row(InlineKeyboardButton("🤖 مدیریت ربات",
               callback_data="admin_bot_management"))
    markup.row(InlineKeyboardButton(
        "🖥️ مدیریت سرور", callback_data="admin_server"))
    return markup


@bot.message_handler(commands=['admin'])
def admin_command_handler(message):
    """دستور /admin"""
    uid = message.chat.id

    if not admin_panel.is_admin(uid):
        bot.reply_to(message, "❌ دسترسی denied! شما ادمین نیستید.")
        return

    admin_panel.log_admin_action(uid, "access_admin_panel")

    bot.send_message(
        uid,
        "🛠️ **پنل مدیریت ربات رابطه‌یاب**\n\n"
        "به پنل مدیریت خوش آمدید! لطفاً بخش مورد نظر را انتخاب کنید:",
        reply_markup=admin_main_menu(),
        parse_mode="Markdown"
    )


@bot.callback_query_handler(func=lambda call: call.data == "admin_main")
def admin_main_handler(call):
    """منوی اصلی مدیریت"""
    uid = call.message.chat.id

    if not is_admin(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی denied!")
        return

    try:
        bot.edit_message_text(
            "🛠️ **پنل مدیریت ربات**\n\n"
            "لطفا بخش مورد نظر را انتخاب کنید:",
            uid,
            call.message.message_id,
            reply_markup=admin_main_menu(),
            parse_mode="Markdown"
        )
    except:
        bot.send_message(
            uid,
            "🛠️ **پنل مدیریت ربات**\n\n"
            "لطفا بخش مورد نظر را انتخاب کنید:",
            reply_markup=admin_main_menu(),
            parse_mode="Markdown"
        )


@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users_handler(call):
    """منوی مدیریت کاربران"""
    uid = call.message.chat.id

    markup = InlineKeyboardMarkup()

    markup.row(InlineKeyboardButton(
        "📊 آمار کاربران", callback_data="users_stats"))
    markup.row(InlineKeyboardButton(
        "🔍 جستجوی کاربر", callback_data="search_user"))
    markup.row(InlineKeyboardButton(
        "📋 لیست کاربران", callback_data="users_list"))
    markup.row(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main"))

    try:
        bot.edit_message_text(
            "👥 **مدیریت کاربران**\n\n"
            "لطفا گزینه مورد نظر را انتخاب کنید:",
            uid, call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except:
        bot.send_message(
            uid,
            "👥 **مدیریت کاربران**\n\n"
            "لطفا گزینه مورد نظر را انتخاب کنید:",
            reply_markup=markup,
            parse_mode="Markdown"
        )


@bot.callback_query_handler(func=lambda call: call.data == "admin_server")
def admin_server_handler(call):
    """منوی مدیریت سرور"""
    uid = call.message.chat.id

    markup = InlineKeyboardMarkup()

    markup.row(InlineKeyboardButton(
        "📊 آمار سرور", callback_data="server_stats"))
    markup.row(InlineKeyboardButton(
        "⚙️ تنظیمات", callback_data="server_settings"))
    markup.row(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main"))

    try:
        bot.edit_message_text(
            "🖥️ **مدیریت سرور**\n\n"
            "لطفا گزینه مورد نظر را انتخاب کنید:",
            uid, call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except:
        bot.send_message(
            uid,
            "🖥️ **مدیریت سرور**\n\n"
            "لطفا گزینه مورد نظر را انتخاب کنید:",
            reply_markup=markup,
            parse_mode="Markdown"
        )

# ==================== هندلر دستور مدیریت ====================


@bot.message_handler(commands=['admin'])
def admin_command_handler(message):
    """دستور مدیریت"""
    uid = message.chat.id

    if not is_admin(uid):
        bot.send_message(uid, "❌ دسترسی denied!")
        return

    markup = InlineKeyboardMarkup()

    markup.row(InlineKeyboardButton(
        "👥 مدیریت کاربران", callback_data="admin_users"))
    markup.row(InlineKeyboardButton(
        "📢 پیام همگانی", callback_data="admin_broadcast"))
    markup.row(InlineKeyboardButton("🤖 مدیریت ربات",
               callback_data="admin_bot_management"))
    markup.row(InlineKeyboardButton(
        "🖥️ مدیریت سرور", callback_data="admin_server"))

    bot.send_message(
        uid,
        "🛠️ **پنل مدیریت ربات**\n\n"
        "لطفا بخش مورد نظر را انتخاب کنید:",
        reply_markup=markup,
        parse_mode="Markdown"
    )


# ==================== مدیریت کاربران - آمار ====================

def admin_user_management_menu():
    """منوی اصلی مدیریت کاربران"""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(
            "📊 آمار کاربران", callback_data="admin_user_stats"),
        InlineKeyboardButton("👥 لیست کاربران", callback_data="admin_user_list")
    )
    markup.row(
        InlineKeyboardButton(
            "🔍 جستجوی کاربر", callback_data="admin_user_search"),
        InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast")
    )
    markup.row(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main"))
    return markup


def get_detailed_user_stats():
    """آمار دقیق کاربران"""
    try:
        conn = sqlite3.connect("relation_agent.db", check_same_thread=False)
        cur = conn.cursor()

        # آمار کلی
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]

        # آمار جنسیتی
        cur.execute("SELECT gender, COUNT(*) FROM users GROUP BY gender")
        gender_stats = dict(cur.fetchall())

        # آمار وضعیت رابطه
        cur.execute(
            "SELECT connection_status, COUNT(*) FROM users GROUP BY connection_status")
        relation_stats = dict(cur.fetchall())

        # آمار ترکیبی (پسران متصل، دختران متصل)
        cur.execute("""
            SELECT gender, connection_status, COUNT(*) 
            FROM users 
            GROUP BY gender, connection_status
        """)
        combined_stats = cur.fetchall()

        # کاربران مسدود (اگر جدول مسدودیت‌ها وجود دارد)
        banned_users = 0
        try:
            cur.execute("SELECT COUNT(*) FROM blocked_users")
            banned_users = cur.fetchone()[0]
        except:
            pass

        conn.close()

        # محاسبه آمار ترکیبی
        male_connected = 0
        female_connected = 0

        for gender, status, count in combined_stats:
            if gender == 'مرد' and status == 'connected':
                male_connected = count
            elif gender == 'زن' and status == 'connected':
                female_connected = count

        return {
            'total_users': total_users,
            'male_users': gender_stats.get('مرد', 0),
            'female_users': gender_stats.get('زن', 0),
            'connected_users': relation_stats.get('connected', 0),
            'single_users': relation_stats.get('single', 0) + relation_stats.get('pending', 0),
            'banned_users': banned_users,
            'male_connected': male_connected,
            'female_connected': female_connected
        }

    except Exception as e:
        print(f"❌ خطا در دریافت آمار کاربران: {e}")
        return {}


def format_user_stats_text(stats):
    """فرمت‌بندی آمار کاربران"""
    text = "👥 **آمار دقیق کاربران**\n\n"

    text += "📊 **آمار کلی:**\n"
    text += f"• جمعیت کل کاربران: {stats.get('total_users', 0):,}\n"
    text += f"• کاربران متصل: {stats.get('connected_users', 0):,}\n"
    text += f"• کاربران سینگل: {stats.get('single_users', 0):,}\n"
    text += f"• کاربران مسدود شده: {stats.get('banned_users', 0):,}\n\n"

    text += "👫 **تقسیم‌بندی جنسیتی:**\n"
    text += f"• کاربران پسر: {stats.get('male_users', 0):,}\n"
    text += f"• کاربران دختر: {stats.get('female_users', 0):,}\n\n"

    text += "💑 **کاربران متصل:**\n"
    text += f"• پسران متصل: {stats.get('male_connected', 0):,}\n"
    text += f"• دختران متصل: {stats.get('female_connected', 0):,}\n\n"

    # محاسبه درصدها
    if stats.get('total_users', 0) > 0:
        male_percent = (stats.get('male_users', 0) /
                        stats.get('total_users', 1)) * 100
        female_percent = (stats.get('female_users', 0) /
                          stats.get('total_users', 1)) * 100
        connected_percent = (stats.get('connected_users', 0) /
                             stats.get('total_users', 1)) * 100

        text += "📈 **درصدها:**\n"
        text += f"• پسران: {male_percent:.1f}%\n"
        text += f"• دختران: {female_percent:.1f}%\n"
        text += f"• متصل: {connected_percent:.1f}%\n"

    text += f"\n🕒 آخرین بروزرسانی: {datetime.now().strftime('%H:%M:%S')}"

    return text


def admin_user_stats_menu():
    """منوی آمار کاربران"""
    markup = InlineKeyboardMarkup()

    # دکمه‌های شیشه‌ای برای فیلترها
    markup.row(
        InlineKeyboardButton(
            "👥 همه کاربران", callback_data="admin_filter_all"),
        InlineKeyboardButton("👨 پسران", callback_data="admin_filter_male")
    )
    markup.row(
        InlineKeyboardButton("👩 دختران", callback_data="admin_filter_female"),
        InlineKeyboardButton(
            "💑 متصل‌ها", callback_data="admin_filter_connected")
    )
    markup.row(
        InlineKeyboardButton(
            "🚶 سینگل‌ها", callback_data="admin_filter_single"),
        InlineKeyboardButton(
            "🚫 مسدود شده‌ها", callback_data="admin_filter_banned")
    )
    markup.row(InlineKeyboardButton(
        "🔄 بروزرسانی آمار", callback_data="admin_user_stats"))
    markup.row(InlineKeyboardButton(
        "🔙 بازگشت", callback_data="admin_manage_users"))

    return markup

# هندلرهای مربوطه


@bot.callback_query_handler(func=lambda call: call.data == "admin_manage_users")
def admin_manage_users_handler(call):
    """ورود به مدیریت کاربران"""
    uid = call.message.chat.id
    if not admin_panel.is_admin(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی denied!")
        return

    admin_panel.log_admin_action(uid, "view_user_management")
    bot.edit_message_text(
        "👥 **مدیریت کاربران**\n\n"
        "لطفاً عملیات مورد نظر را انتخاب کنید:",
        uid, call.message.message_id,
        reply_markup=admin_user_management_menu(),
        parse_mode="Markdown"
    )


@bot.callback_query_handler(func=lambda call: call.data == "admin_user_stats")
def admin_user_stats_handler(call):
    """نمایش آمار کاربران"""
    uid = call.message.chat.id
    if not admin_panel.is_admin(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی denied!")
        return

    admin_panel.log_admin_action(uid, "view_user_stats")

    try:
        stats = get_detailed_user_stats()
        stats_text = format_user_stats_text(stats)

        bot.edit_message_text(
            stats_text,
            uid, call.message.message_id,
            reply_markup=admin_user_stats_menu(),
            parse_mode="Markdown"
        )

    except Exception as e:
        bot.edit_message_text(
            f"❌ خطا در دریافت آمار: {str(e)}",
            uid, call.message.message_id,
            reply_markup=admin_user_stats_menu()
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_filter_"))
def admin_filter_users_handler(call):
    """فیلتر کردن کاربران"""
    uid = call.message.chat.id
    if not admin_panel.is_admin(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی denied!")
        return

    filter_type = call.data.split('_')[2]
    admin_panel.log_admin_action(uid, f"filter_users_{filter_type}")

    # اینجا بعداً لیست کاربران فیلتر شده رو نمایش می‌دیم
    bot.answer_callback_query(call.id, f"🔄 فیلتر {filter_type} اعمال شد!")


# ==================== مدیریت کاربران - لیست کاربران ====================

def get_users_list(page=0, filter_type=None):
    """دریافت لیست کاربران با صفحه‌بندی"""
    try:
        conn = sqlite3.connect("relation_agent.db", check_same_thread=False)
        cur = conn.cursor()

        # ساخت کوئری بر اساس فیلتر
        query = "SELECT user_id, name, gender, connection_status FROM users"
        params = []

        if filter_type:
            if filter_type == "male":
                query += " WHERE gender = ?"
                params.append("مرد")
            elif filter_type == "female":
                query += " WHERE gender = ?"
                params.append("زن")
            elif filter_type == "connected":
                query += " WHERE connection_status = ?"
                params.append("connected")
            elif filter_type == "single":
                query += " WHERE connection_status != ?"
                params.append("connected")

        query += " ORDER BY created_at DESC LIMIT 10 OFFSET ?"
        params.append(page * 10)

        cur.execute(query, params)
        users = cur.fetchall()

        # تعداد کل کاربران برای صفحه‌بندی
        count_query = "SELECT COUNT(*) FROM users"
        if filter_type:
            if filter_type == "male":
                count_query += " WHERE gender = 'مرد'"
            elif filter_type == "female":
                count_query += " WHERE gender = 'زن'"
            elif filter_type == "connected":
                count_query += " WHERE connection_status = 'connected'"
            elif filter_type == "single":
                count_query += " WHERE connection_status != 'connected'"

        cur.execute(count_query)
        total_users = cur.fetchone()[0]

        conn.close()

        return {
            'users': users,
            'total_users': total_users,
            'current_page': page,
            'total_pages': (total_users + 9) // 10  # محاسبه تعداد صفحات
        }

    except Exception as e:
        print(f"❌ خطا در دریافت لیست کاربران: {e}")
        return {'users': [], 'total_users': 0, 'current_page': 0, 'total_pages': 0}


def format_user_list_text(users_data, filter_type=None):
    """فرمت‌بندی لیست کاربران"""
    users = users_data['users']
    current_page = users_data['current_page']
    total_pages = users_data['total_pages']
    total_users = users_data['total_users']

    # عنوان بر اساس فیلتر
    filter_titles = {
        None: "👥 لیست همه کاربران",
        "male": "👨 لیست پسران",
        "female": "👩 لیست دختران",
        "connected": "💑 لیست متصل‌ها",
        "single": "🚶 لیست سینگل‌ها"
    }

    title = filter_titles.get(filter_type, "👥 لیست کاربران")

    text = f"{title}\n\n"
    text += f"📄 صفحه {current_page + 1} از {total_pages}\n"
    text += f"📊 تعداد کل: {total_users:,} کاربر\n\n"

    if not users:
        text += "❌ کاربری یافت نشد.\n"
        return text

    for i, (user_id, name, gender, connection_status) in enumerate(users, 1):
        index = (current_page * 10) + i
        status_icon = "💑" if connection_status == "connected" else "🚶"
        gender_icon = "👨" if gender == "مرد" else "👩"

        text += f"{index}. {gender_icon} {status_icon} {name}\n"
        text += f"   🆔 `{user_id}`\n\n"

    text += "💡 برای مشاهده اطلاعات کاربر روی آیدی کلیک کنید."

    return text


def admin_user_list_menu(users_data, filter_type=None):
    """منوی لیست کاربران با صفحه‌بندی"""
    markup = InlineKeyboardMarkup()

    current_page = users_data['current_page']
    total_pages = users_data['total_pages']

    # دکمه‌های کاربران
    for user_id, name, gender, connection_status in users_data['users']:
        gender_icon = "👨" if gender == "مرد" else "👩"
        status_icon = "💑" if connection_status == "connected" else "🚶"
        button_text = f"{gender_icon}{status_icon} {user_id}"

        markup.row(InlineKeyboardButton(
            button_text, callback_data=f"admin_view_user_{user_id}"))

    # دکمه‌های صفحه‌بندی
    nav_buttons = []

    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton(
            "⬅️ قبلی", callback_data=f"admin_user_page_{current_page - 1}_{filter_type or 'all'}"))

    nav_buttons.append(InlineKeyboardButton(
        f"{current_page + 1}/{total_pages}", callback_data="admin_user_list_info"))

    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            "بعدی ➡️", callback_data=f"admin_user_page_{current_page + 1}_{filter_type or 'all'}"))

    if nav_buttons:
        markup.row(*nav_buttons)

    # دکمه‌های فیلتر
    filter_buttons = []
    filter_buttons.append(InlineKeyboardButton(
        "👥 همه", callback_data="admin_user_list_all"))
    filter_buttons.append(InlineKeyboardButton(
        "👨 پسران", callback_data="admin_user_list_male"))
    markup.row(*filter_buttons)

    filter_buttons2 = []
    filter_buttons2.append(InlineKeyboardButton(
        "👩 دختران", callback_data="admin_user_list_female"))
    filter_buttons2.append(InlineKeyboardButton(
        "💑 متصل", callback_data="admin_user_list_connected"))
    markup.row(*filter_buttons2)

    markup.row(InlineKeyboardButton(
        "🔙 بازگشت", callback_data="admin_manage_users"))

    return markup

# هندلرهای لیست کاربران


@bot.callback_query_handler(func=lambda call: call.data == "admin_user_list")
def admin_user_list_handler(call):
    """نمایش لیست کاربران"""
    uid = call.message.chat.id
    if not admin_panel.is_admin(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی denied!")
        return

    admin_panel.log_admin_action(uid, "view_user_list")
    show_user_list(uid, call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_user_list_"))
def admin_user_list_filter_handler(call):
    """فیلتر کردن لیست کاربران"""
    uid = call.message.chat.id
    if not admin_panel.is_admin(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی denied!")
        return

    filter_type = call.data.split('_')[3]  # all, male, female, connected

    if filter_type == "all":
        filter_type = None
    elif filter_type == "male":
        filter_type = "male"
    elif filter_type == "female":
        filter_type = "female"
    elif filter_type == "connected":
        filter_type = "connected"

    admin_panel.log_admin_action(
        uid, f"filter_user_list_{filter_type or 'all'}")
    show_user_list(uid, call.message.message_id, 0, filter_type)


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_user_page_"))
def admin_user_list_page_handler(call):
    """تغییر صفحه لیست کاربران"""
    uid = call.message.chat.id
    if not admin_panel.is_admin(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی denied!")
        return

    parts = call.data.split('_')
    page = int(parts[3])
    filter_type = parts[4]

    if filter_type == "all":
        filter_type = None

    admin_panel.log_admin_action(uid, f"user_list_page_{page}")
    show_user_list(uid, call.message.message_id, page, filter_type)


def show_user_list(uid, message_id, page=0, filter_type=None):
    """نمایش لیست کاربران"""
    try:
        users_data = get_users_list(page, filter_type)
        list_text = format_user_list_text(users_data, filter_type)
        markup = admin_user_list_menu(users_data, filter_type)

        bot.edit_message_text(
            list_text,
            uid, message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )

    except Exception as e:
        bot.edit_message_text(
            f"❌ خطا در نمایش لیست کاربران: {str(e)}",
            uid, message_id,
            reply_markup=admin_user_management_menu()
        )


# ==================== مدیریت کاربران - مشاهده اطلاعات کاربر ====================

def get_user_details(user_id):
    """دریافت اطلاعات کامل کاربر"""
    try:
        conn = sqlite3.connect("relation_agent.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("""
            SELECT user_id, name, gender, birthdate, partner_name, 
                   partner_nick, relation_type, connection_status, 
                   partner_id, created_at
            FROM users WHERE user_id = ?
        """, (user_id,))

        user_data = cur.fetchone()
        conn.close()

        if user_data:
            return format_user_details(user_data)
        else:
            return None

    except Exception as e:
        print(f"❌ خطا در دریافت اطلاعات کاربر: {e}")
        return None


def format_user_details(user_data):
    """فرمت‌بندی اطلاعات کاربر"""
    (user_id, name, gender, birthdate, partner_name,
     partner_nick, relation_type, connection_status,
     partner_id, created_at) = user_data

    # محاسبه سن
    age = "نامشخص"
    if birthdate:
        try:
            birth_date = datetime.strptime(birthdate, "%Y-%m-%d").date()
            today = datetime.now().date()
            age = today.year - birth_date.year - \
                ((today.month, today.day) < (birth_date.month, birth_date.day))
        except:
            pass

    # تاریخ عضویت
    created_dt = datetime.fromisoformat(created_at)
    created_str = created_dt.strftime("%Y/%m/%d %H:%M")
    days_since_join = (datetime.now() - created_dt).days

    # آیکون‌ها
    gender_icon = "👨" if gender == "مرد" else "👩"
    status_icon = "💑" if connection_status == "connected" else "🚶"

    text = f"{gender_icon} {status_icon} **اطلاعات کاربر**\n\n"

    text += f"**👤 اطلاعات اصلی:**\n"
    text += f"• نام: {name}\n"
    text += f"• آیدی: `{user_id}`\n"
    text += f"• جنسیت: {gender}\n"
    text += f"• سن: {age} سال\n\n"

    text += f"**💑 وضعیت رابطه:**\n"
    text += f"• نوع: {relation_type}\n"
    text += f"• وضعیت: {connection_status}\n"

    if partner_name:
        text += f"• پارتنر: {partner_name}\n"
        if partner_nick:
            text += f"• لقب: {partner_nick}\n"
        if partner_id:
            text += f"• آیدی پارتنر: `{partner_id}`\n"
    text += "\n"

    text += f"**📅 اطلاعات عضویت:**\n"
    text += f"• تاریخ عضویت: {created_str}\n"
    text += f"• روزهای گذشته: {days_since_join} روز\n"

    return text


def admin_user_actions_menu(user_id):
    """منوی اقدامات برای کاربر"""
    markup = InlineKeyboardMarkup()

    # ردیف 1: مسدود کردن و ارسال پیام
    markup.row(
        InlineKeyboardButton(
            "🚫 مسدود کردن", callback_data=f"admin_ban_{user_id}"),
        InlineKeyboardButton(
            "✉️ ارسال پیام", callback_data=f"admin_send_msg_{user_id}")
    )

    # ردیف 2: اتصال و اطلاعات بیشتر
    markup.row(
        InlineKeyboardButton(
            "🔗 اتصال/قطع", callback_data=f"admin_connect_{user_id}"),
        InlineKeyboardButton(
            "📊 آمار فعالیت", callback_data=f"admin_stats_{user_id}")
    )

    # ردیف 3: بازگشت
    markup.row(InlineKeyboardButton(
        "🔙 بازگشت به لیست", callback_data="admin_user_list"))

    return markup

# هندلر مشاهده کاربر


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_view_user_"))
def admin_view_user_handler(call):
    """مشاهده اطلاعات کاربر"""
    uid = call.message.chat.id
    if not admin_panel.is_admin(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی denied!")
        return

    user_id = int(call.data.split('_')[3])
    admin_panel.log_admin_action(uid, f"view_user_{user_id}")

    user_details = get_user_details(user_id)

    if user_details:
        markup = admin_user_actions_menu(user_id)
        bot.edit_message_text(
            user_details,
            uid, call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    else:
        bot.answer_callback_query(call.id, "❌ کاربر پیدا نشد!")

# هندلر مسدود کردن کاربر


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_ban_"))
def admin_ban_user_handler(call):
    """مسدود کردن کاربر"""
    uid = call.message.chat.id
    if not admin_panel.is_admin(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی denied!")
        return

    user_id = int(call.data.split('_')[2])
    admin_panel.log_admin_action(uid, f"ban_user_{user_id}")

    # ایجاد جدول مسدودیت‌ها اگر وجود ندارد
    try:
        conn = sqlite3.connect("admin_panel.db", check_same_thread=False)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS banned_users (
                user_id INTEGER PRIMARY KEY,
                admin_id INTEGER,
                reason TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # بررسی آیا کاربر قبلاً مسدود شده
        cur.execute("SELECT 1 FROM banned_users WHERE user_id = ?", (user_id,))
        already_banned = cur.fetchone()

        if already_banned:
            # آنبلاک کردن
            cur.execute(
                "DELETE FROM banned_users WHERE user_id = ?", (user_id,))
            conn.commit()
            action_text = "آنبلاک"
            success_text = f"✅ کاربر با آیدی `{user_id}` آنبلاک شد."
        else:
            # مسدود کردن
            cur.execute("INSERT INTO banned_users (user_id, admin_id, reason) VALUES (?, ?, ?)",
                        (user_id, uid, "مسدودیت توسط ادمین"))
            conn.commit()
            action_text = "مسدود"
            success_text = f"✅ کاربر با آیدی `{user_id}` مسدود شد."

        conn.close()

        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton(
            "🔙 بازگشت", callback_data=f"admin_view_user_{user_id}"))

        bot.edit_message_text(
            success_text,
            uid, call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )

    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ خطا در عملیات: {str(e)}")

# هندلر ارسال پیام به کاربر


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_send_msg_"))
def admin_send_msg_handler(call):
    """شروع فرآیند ارسال پیام به کاربر"""
    uid = call.message.chat.id
    if not admin_panel.is_admin(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی denied!")
        return

    user_id = int(call.data.split('_')[3])
    admin_panel.log_admin_action(uid, f"start_send_msg_{user_id}")

    # ذخیره اطلاعات در state
    user_state[uid] = f"admin_send_msg_{user_id}"
    temp_data[uid] = {"target_user": user_id}

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(
        "🔙 لغو", callback_data=f"admin_view_user_{user_id}"))

    bot.edit_message_text(
        f"✉️ **ارسال پیام به کاربر**\n\n"
        f"آیدی کاربر: `{user_id}`\n\n"
        f"لطفاً پیام خود را وارد کنید:\n"
        f"• متن ساده\n"
        f"• یا فایل/عکس/ویدیو با کپشن\n"
        f"• نوع محتوا به طور خودکار تشخیص داده می‌شود",
        uid, call.message.message_id,
        reply_markup=markup,
        parse_mode="Markdown"
    )

# هندلر دریافت پیام برای کاربر


@bot.message_handler(func=lambda m: user_state.get(m.chat.id, "").startswith("admin_send_msg_"))
def admin_send_msg_content_handler(message):
    """دریافت محتوای پیام برای ارسال به کاربر"""
    uid = message.chat.id
    state = user_state.get(uid, "")

    if not state.startswith("admin_send_msg_"):
        return

    user_id = int(state.split('_')[3])
    admin_panel.log_admin_action(uid, f"send_msg_to_{user_id}")

    try:
        # تشخیص نوع محتوا و ارسال
        if message.text:
            # پیام متنی
            bot.send_message(user_id, f"📨 پیام از مدیریت:\n\n{message.text}")
            result_text = "✅ پیام متنی ارسال شد"

        elif message.photo:
            # عکس
            photo_id = message.photo[-1].file_id
            caption = message.caption or "📨 پیام از مدیریت"
            bot.send_photo(user_id, photo_id, caption=caption)
            result_text = "✅ عکس با کپشن ارسال شد"

        elif message.video:
            # ویدیو
            video_id = message.video.file_id
            caption = message.caption or "📨 پیام از مدیریت"
            bot.send_video(user_id, video_id, caption=caption)
            result_text = "✅ ویدیو با کپشن ارسال شد"

        elif message.document:
            # فایل
            doc_id = message.document.file_id
            caption = message.caption or "📨 پیام از مدیریت"
            bot.send_document(user_id, doc_id, caption=caption)
            result_text = "✅ فایل با کپشن ارسال شد"

        else:
            result_text = "❌ نوع محتوای پشتیبانی نشده"

        # پیام موفقیت
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton(
            "🔙 بازگشت", callback_data=f"admin_view_user_{user_id}"))

        bot.send_message(
            uid,
            f"{result_text}\n\n👤 کاربر: `{user_id}`",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    except Exception as e:
        error_msg = f"❌ خطا در ارسال پیام: {str(e)}"
        if "bot was blocked" in str(e).lower():
            error_msg = "❌ کاربر ربات را مسدود کرده است"
        elif "user not found" in str(e).lower():
            error_msg = "❌ کاربر یافت نشد"

        bot.send_message(uid, error_msg)

    finally:
        # پاکسازی state
        user_state.pop(uid, None)
        temp_data.pop(uid, None)


# ==================== مدیریت کاربران - اتصال و آمار ====================

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_connect_"))
def admin_connect_user_handler(call):
    """اتصال یا قطع اتصال کاربر"""
    uid = call.message.chat.id
    if not admin_panel.is_admin(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی denied!")
        return

    user_id = int(call.data.split('_')[2])
    admin_panel.log_admin_action(uid, f"connect_action_{user_id}")

    try:
        conn = sqlite3.connect("relation_agent.db", check_same_thread=False)
        cur = conn.cursor()

        # دریافت وضعیت فعلی کاربر
        cur.execute(
            "SELECT connection_status, partner_id FROM users WHERE user_id = ?", (user_id,))
        user_data = cur.fetchone()

        if not user_data:
            bot.answer_callback_query(call.id, "❌ کاربر پیدا نشد!")
            return

        connection_status, partner_id = user_data

        if connection_status == "connected" and partner_id:
            # قطع اتصال
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton(
                    "✅ بله، قطع کن", callback_data=f"admin_disconnect_confirm_{user_id}"),
                InlineKeyboardButton(
                    "❌ لغو", callback_data=f"admin_view_user_{user_id}")
            )

            bot.edit_message_text(
                f"🔗 **قطع اتصال کاربر**\n\n"
                f"آیدی کاربر: `{user_id}`\n"
                f"این کاربر در حال حاضر به کاربر `{partner_id}` متصل است.\n\n"
                f"⚠️ آیا مطمئن هستید می‌خواهید اتصال را قطع کنید؟",
                uid, call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )

        else:
            # اتصال کاربر - درخواست آیدی پارتنر
            user_state[uid] = f"admin_connect_{user_id}"
            temp_data[uid] = {"target_user": user_id}

            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton(
                "🔙 لغو", callback_data=f"admin_view_user_{user_id}"))

            bot.edit_message_text(
                f"🔗 **اتصال کاربر به پارتنر**\n\n"
                f"آیدی کاربر: `{user_id}`\n\n"
                f"لطفاً آیدی عددی پارتنر را وارد کنید:",
                uid, call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )

        conn.close()

    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ خطا: {str(e)}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_disconnect_confirm_"))
def admin_disconnect_confirm_handler(call):
    """تأیید قطع اتصال کاربر"""
    uid = call.message.chat.id
    if not admin_panel.is_admin(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی denied!")
        return

    user_id = int(call.data.split('_')[3])

    try:
        conn = sqlite3.connect("relation_agent.db", check_same_thread=False)
        cur = conn.cursor()

        # دریافت اطلاعات پارتنر
        cur.execute(
            "SELECT partner_id FROM users WHERE user_id = ?", (user_id,))
        partner_id = cur.fetchone()[0]

        # قطع اتصال هر دو کاربر
        cur.execute(
            "UPDATE users SET connection_status = 'single', partner_id = NULL WHERE user_id = ?", (user_id,))
        cur.execute(
            "UPDATE users SET connection_status = 'single', partner_id = NULL WHERE user_id = ?", (partner_id,))

        conn.commit()
        conn.close()

        admin_panel.log_admin_action(
            uid, f"disconnect_{user_id}_from_{partner_id}")

        # اطلاع‌رسانی به کاربران
        try:
            bot.send_message(
                user_id, "🔗 اتصال شما با پارتنر توسط مدیریت قطع شد.")
            bot.send_message(
                partner_id, "🔗 اتصال شما با پارتنر توسط مدیریت قطع شد.")
        except:
            pass

        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton(
            "🔙 بازگشت", callback_data=f"admin_view_user_{user_id}"))

        bot.edit_message_text(
            f"✅ **اتصال قطع شد**\n\n"
            f"• کاربر `{user_id}`\n"
            f"• پارتنر `{partner_id}`\n\n"
            f"اتصال بین دو کاربر با موفقیت قطع شد.",
            uid, call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )

    except Exception as e:
        bot.edit_message_text(
            f"❌ خطا در قطع اتصال: {str(e)}",
            uid, call.message.message_id,
            reply_markup=InlineKeyboardMarkup().row(
                InlineKeyboardButton(
                    "🔙 بازگشت", callback_data=f"admin_view_user_{user_id}")
            )
        )


@bot.message_handler(func=lambda m: user_state.get(m.chat.id, "").startswith("admin_connect_"))
def admin_connect_partner_handler(message):
    """دریافت آیدی پارتنر برای اتصال"""
    uid = message.chat.id
    state = user_state.get(uid, "")

    if not state.startswith("admin_connect_"):
        return

    user_id = int(state.split('_')[2])

    try:
        partner_id = int(message.text.strip())

        # بررسی وجود پارتنر
        conn = sqlite3.connect("relation_agent.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("SELECT name FROM users WHERE user_id = ?", (partner_id,))
        partner_data = cur.fetchone()

        if not partner_data:
            bot.send_message(uid, "❌ کاربری با این آیدی پیدا نشد!")
            user_state.pop(uid, None)
            return

        partner_name = partner_data[0]

        # اتصال کاربران
        cur.execute("UPDATE users SET connection_status = 'connected', partner_id = ? WHERE user_id = ?",
                    (partner_id, user_id))
        cur.execute("UPDATE users SET connection_status = 'connected', partner_id = ? WHERE user_id = ?",
                    (user_id, partner_id))

        conn.commit()
        conn.close()

        admin_panel.log_admin_action(uid, f"connect_{user_id}_to_{partner_id}")

        # اطلاع‌رسانی به کاربران
        try:
            user_name_result = safe_execute_db(
                "SELECT name FROM users WHERE user_id = ?", (user_id,))
            user_name = user_name_result[0][0] if user_name_result else "کاربر"

            bot.send_message(
                user_id, f"🔗 شما توسط مدیریت به {partner_name} متصل شدید!")
            bot.send_message(
                partner_id, f"🔗 شما توسط مدیریت به {user_name} متصل شدید!")
        except:
            pass

        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton(
            "🔙 بازگشت", callback_data=f"admin_view_user_{user_id}"))

        bot.send_message(
            uid,
            f"✅ **اتصال ایجاد شد**\n\n"
            f"• کاربر: `{user_id}`\n"
            f"• پارتنر: `{partner_id}` - {partner_name}\n\n"
            f"دو کاربر با موفقیت به هم متصل شدند.",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    except ValueError:
        bot.send_message(uid, "❌ آیدی باید عدد باشد!")
    except Exception as e:
        bot.send_message(uid, f"❌ خطا در اتصال: {str(e)}")

    finally:
        user_state.pop(uid, None)
        temp_data.pop(uid, None)


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_stats_"))
def admin_user_stats_handler(call):
    """نمایش آمار فعالیت کاربر"""
    uid = call.message.chat.id
    if not admin_panel.is_admin(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی denied!")
        return

    user_id = int(call.data.split('_')[2])
    admin_panel.log_admin_action(uid, f"view_stats_{user_id}")

    try:
        stats = get_user_activity_stats(user_id)
        stats_text = format_user_activity_stats(stats, user_id)

        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton(
            "🔙 بازگشت", callback_data=f"admin_view_user_{user_id}"))

        bot.edit_message_text(
            stats_text,
            uid, call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )

    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ خطا در دریافت آمار: {str(e)}")


def get_user_activity_stats(user_id):
    """دریافت آمار فعالیت کاربر"""
    stats = {}

    try:
        # تعداد کتاب‌ها
        try:
            conn_books = sqlite3.connect("books.db", check_same_thread=False)
            cur_books = conn_books.cursor()
            cur_books.execute(
                "SELECT COUNT(*) FROM user_books WHERE user_id = ? OR partner_id = ?", (user_id, user_id))
            stats['total_books'] = cur_books.fetchone()[0]

            cur_books.execute(
                "SELECT COUNT(*) FROM book_pages WHERE author_id = ?", (user_id,))
            stats['pages_written'] = cur_books.fetchone()[0]
            conn_books.close()
        except:
            stats['total_books'] = 0
            stats['pages_written'] = 0

        # حالت‌های خلقی
        try:
            conn_mood = sqlite3.connect(
                "mood_tracking.db", check_same_thread=False)
            cur_mood = conn_mood.cursor()
            cur_mood.execute(
                "SELECT COUNT(*) FROM mood_entries WHERE user_id = ?", (user_id,))
            stats['mood_updates'] = cur_mood.fetchone()[0]

            # آخرین بروزرسانی حالت خلقی
            cur_mood.execute(
                "SELECT created_at FROM mood_entries WHERE user_id = ? ORDER BY created_at DESC LIMIT 1", (user_id,))
            last_mood = cur_mood.fetchone()
            stats['last_mood'] = last_mood[0] if last_mood else None
            conn_mood.close()
        except:
            stats['mood_updates'] = 0
            stats['last_mood'] = None

        # پیام‌های مخفی
        try:
            conn_secret = sqlite3.connect(
                "secret_messages.db", check_same_thread=False)
            cur_secret = conn_secret.cursor()
            cur_secret.execute(
                "SELECT COUNT(*) FROM secret_messages WHERE sender_id = ?", (user_id,))
            stats['sent_messages'] = cur_secret.fetchone()[0]

            cur_secret.execute(
                "SELECT COUNT(*) FROM secret_messages WHERE receiver_id = ?", (user_id,))
            stats['received_messages'] = cur_secret.fetchone()[0]
            conn_secret.close()
        except:
            stats['sent_messages'] = 0
            stats['received_messages'] = 0

        # اطلاعات اصلی کاربر
        conn_main = sqlite3.connect(
            "relation_agent.db", check_same_thread=False)
        cur_main = conn_main.cursor()
        cur_main.execute(
            "SELECT created_at FROM users WHERE user_id = ?", (user_id,))
        user_created = cur_main.fetchone()[0]
        stats['join_date'] = user_created
        conn_main.close()

    except Exception as e:
        print(f"❌ خطا در دریافت آمار فعالیت کاربر: {e}")

    return stats


def format_user_activity_stats(stats, user_id):
    """فرمت‌بندی آمار فعالیت کاربر"""
    text = f"📊 **آمار فعالیت کاربر**\n\n"
    text += f"👤 آیدی: `{user_id}`\n\n"

    text += "📚 **فعالیت کتاب‌نویسی:**\n"
    text += f"• کتاب‌های مشترک: {stats.get('total_books', 0)}\n"
    text += f"• صفحات نوشته شده: {stats.get('pages_written', 0)}\n\n"

    text += "🌙 **حالت‌های خلقی:**\n"
    text += f"• بروزرسانی‌ها: {stats.get('mood_updates', 0)}\n"
    if stats.get('last_mood'):
        last_mood_dt = datetime.fromisoformat(stats['last_mood'])
        last_mood_str = last_mood_dt.strftime("%Y/%m/%d %H:%M")
        text += f"• آخرین بروزرسانی: {last_mood_str}\n"
    text += "\n"

    text += "💌 **پیام‌های مخفی:**\n"
    text += f"• پیام‌های ارسالی: {stats.get('sent_messages', 0)}\n"
    text += f"• پیام‌های دریافتی: {stats.get('received_messages', 0)}\n\n"

    # محاسبه روزهای عضویت
    if stats.get('join_date'):
        join_dt = datetime.fromisoformat(stats['join_date'])
        days_since_join = (datetime.now() - join_dt).days
        text += f"📅 روزهای عضویت: {days_since_join} روز\n"

    return text


# ==================== مدیریت کاربران - جستجوی کاربر ====================

def admin_user_search_menu():
    """منوی جستجوی کاربر"""
    markup = InlineKeyboardMarkup()

    markup.row(
        InlineKeyboardButton(
            "🔍 با آیدی عددی", callback_data="admin_search_by_id"),
        InlineKeyboardButton(
            "📛 با نام کاربر", callback_data="admin_search_by_name")
    )

    markup.row(InlineKeyboardButton(
        "🔙 بازگشت", callback_data="admin_manage_users"))

    return markup


def search_user_by_id(user_id):
    """جستجوی کاربر با آیدی عددی"""
    try:
        conn = sqlite3.connect("relation_agent.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("""
            SELECT user_id, name, gender, birthdate, partner_name, 
                   partner_nick, relation_type, connection_status, 
                   partner_id, created_at
            FROM users WHERE user_id = ?
        """, (user_id,))

        user_data = cur.fetchone()
        conn.close()

        return user_data

    except Exception as e:
        print(f"❌ خطا در جستجوی کاربر با آیدی: {e}")
        return None


def search_users_by_name(name_query):
    """جستجوی کاربران با نام"""
    try:
        conn = sqlite3.connect("relation_agent.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("""
            SELECT user_id, name, gender, connection_status, created_at
            FROM users 
            WHERE name LIKE ? 
            ORDER BY created_at DESC 
            LIMIT 20
        """, (f"%{name_query}%",))

        users = cur.fetchall()
        conn.close()

        return users

    except Exception as e:
        print(f"❌ خطا در جستجوی کاربر با نام: {e}")
        return []


def format_search_results(users, search_type, query):
    """فرمت‌بندی نتایج جستجو"""
    if not users:
        return f"❌ هیچ کاربری با {search_type} '{query}' پیدا نشد."

    if search_type == "آیدی":
        # برای جستجوی آیدی، فقط یک کاربر نمایش داده می‌شود
        user_data = users
        return format_user_details(user_data)
    else:
        # برای جستجوی نام، لیست کاربران نمایش داده می‌شود
        text = f"🔍 **نتایج جستجو برای: {query}**\n\n"
        text += f"📊 تعداد نتایج: {len(users)}\n\n"

        for i, (user_id, name, gender, connection_status, created_at) in enumerate(users, 1):
            status_icon = "💑" if connection_status == "connected" else "🚶"
            gender_icon = "👨" if gender == "مرد" else "👩"

            text += f"{i}. {gender_icon} {status_icon} {name}\n"
            text += f"   🆔 `{user_id}`\n\n"

        text += "💡 برای مشاهده اطلاعات کاربر روی آیدی کلیک کنید."
        return text


def admin_search_results_menu(users, search_type, query):
    """منوی نتایج جستجو"""
    markup = InlineKeyboardMarkup()

    if search_type == "آیدی":
        # برای جستجوی آیدی، فقط یک کاربر وجود دارد
        user_id = users[0]  # users در اینجا یک تاپل است
        markup.row(InlineKeyboardButton("👀 مشاهده کاربر",
                   callback_data=f"admin_view_user_{user_id}"))

    else:
        # برای جستجوی نام، لیست کاربران نمایش داده می‌شود
        for user_id, name, gender, connection_status, created_at in users:
            gender_icon = "👨" if gender == "مرد" else "👩"
            status_icon = "💑" if connection_status == "connected" else "🚶"
            button_text = f"{gender_icon}{status_icon} {user_id}"

            markup.row(InlineKeyboardButton(
                button_text, callback_data=f"admin_view_user_{user_id}"))

    # دکمه جستجوی مجدد
    if search_type == "آیدی":
        markup.row(InlineKeyboardButton("🔍 جستجوی مجدد با آیدی",
                   callback_data="admin_search_by_id"))
    else:
        markup.row(InlineKeyboardButton("🔍 جستجوی مجدد با نام",
                   callback_data="admin_search_by_name"))

    markup.row(InlineKeyboardButton("🔙 بازگشت به جستجو",
               callback_data="admin_user_search"))

    return markup

# هندلرهای جستجو


@bot.callback_query_handler(func=lambda call: call.data == "admin_user_search")
def admin_user_search_handler(call):
    """ورود به بخش جستجوی کاربر"""
    uid = call.message.chat.id
    if not admin_panel.is_admin(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی denied!")
        return

    admin_panel.log_admin_action(uid, "view_user_search")
    bot.edit_message_text(
        "🔍 **جستجوی کاربر**\n\n"
        "لطفاً روش جستجو را انتخاب کنید:",
        uid, call.message.message_id,
        reply_markup=admin_user_search_menu(),
        parse_mode="Markdown"
    )


@bot.callback_query_handler(func=lambda call: call.data == "admin_search_by_id")
def admin_search_by_id_handler(call):
    """شروع جستجو با آیدی عددی"""
    uid = call.message.chat.id
    if not admin_panel.is_admin(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی denied!")
        return

    admin_panel.log_admin_action(uid, "start_search_by_id")
    user_state[uid] = "admin_search_user_id"

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(
        "🔙 لغو", callback_data="admin_user_search"))

    bot.edit_message_text(
        "🔍 **جستجو با آیدی عددی**\n\n"
        "لطفاً آیدی عددی کاربر را وارد کنید:",
        uid, call.message.message_id,
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == "admin_search_by_name")
def admin_search_by_name_handler(call):
    """شروع جستجو با نام کاربر"""
    uid = call.message.chat.id
    if not admin_panel.is_admin(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی denied!")
        return

    admin_panel.log_admin_action(uid, "start_search_by_name")
    user_state[uid] = "admin_search_user_name"

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(
        "🔙 لغو", callback_data="admin_user_search"))

    bot.edit_message_text(
        "🔍 **جستجو با نام کاربر**\n\n"
        "لطفاً نام کاربر (یا بخشی از آن) را وارد کنید:",
        uid, call.message.message_id,
        reply_markup=markup
    )


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "admin_search_user_id")
def admin_search_user_id_handler(message):
    """دریافت آیدی برای جستجو"""
    uid = message.chat.id

    try:
        user_id = int(message.text.strip())
        admin_panel.log_admin_action(uid, f"search_user_id_{user_id}")

        user_data = search_user_by_id(user_id)

        if user_data:
            # ذخیره اطلاعات کاربر در temp_data برای نمایش
            temp_data[uid] = {
                "search_results": [user_data],
                "search_type": "آیدی",
                "search_query": str(user_id)
            }

            results_text = format_search_results(
                user_data, "آیدی", str(user_id))
            markup = admin_search_results_menu(
                [user_data], "آیدی", str(user_id))

            bot.send_message(
                uid,
                results_text,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        else:
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("🔍 جستجوی مجدد",
                       callback_data="admin_search_by_id"))
            markup.row(InlineKeyboardButton(
                "🔙 بازگشت", callback_data="admin_user_search"))

            bot.send_message(
                uid,
                f"❌ کاربری با آیدی `{user_id}` پیدا نشد.",
                reply_markup=markup,
                parse_mode="Markdown"
            )

        user_state.pop(uid, None)

    except ValueError:
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔍 جستجوی مجدد",
                   callback_data="admin_search_by_id"))

        bot.send_message(
            uid,
            "❌ آیدی باید عدد باشد! لطفاً یک عدد وارد کنید.",
            reply_markup=markup
        )
    except Exception as e:
        bot.send_message(
            uid,
            f"❌ خطا در جستجو: {str(e)}",
            reply_markup=admin_user_search_menu()
        )
        user_state.pop(uid, None)


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "admin_search_user_name")
def admin_search_user_name_handler(message):
    """دریافت نام برای جستجو"""
    uid = message.chat.id

    try:
        name_query = message.text.strip()

        if len(name_query) < 2:
            bot.send_message(uid, "❌ نام باید حداقل ۲ حرف داشته باشد!")
            return

        admin_panel.log_admin_action(uid, f"search_user_name_{name_query}")

        users = search_users_by_name(name_query)

        if users:
            # ذخیره نتایج جستجو در temp_data
            temp_data[uid] = {
                "search_results": users,
                "search_type": "نام",
                "search_query": name_query
            }

            results_text = format_search_results(users, "نام", name_query)
            markup = admin_search_results_menu(users, "نام", name_query)

            bot.send_message(
                uid,
                results_text,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        else:
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("🔍 جستجوی مجدد",
                       callback_data="admin_search_by_name"))
            markup.row(InlineKeyboardButton(
                "🔙 بازگشت", callback_data="admin_user_search"))

            bot.send_message(
                uid,
                f"❌ هیچ کاربری با نام '{name_query}' پیدا نشد.",
                reply_markup=markup
            )

        user_state.pop(uid, None)

    except Exception as e:
        bot.send_message(
            uid,
            f"❌ خطا در جستجو: {str(e)}",
            reply_markup=admin_user_search_menu()
        )
        user_state.pop(uid, None)

# هندلر برای نمایش اطلاعات کاربر از نتایج جستجو


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_view_user_"))
def admin_view_user_from_search_handler(call):
    """مشاهده اطلاعات کاربر از نتایج جستجو"""
    uid = call.message.chat.id
    if not admin_panel.is_admin(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی denied!")
        return

    user_id = int(call.data.split('_')[3])
    admin_panel.log_admin_action(uid, f"view_user_from_search_{user_id}")

    user_details = get_user_details(user_id)

    if user_details:
        markup = admin_user_actions_menu(user_id)
        bot.edit_message_text(
            user_details,
            uid, call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    else:
        bot.answer_callback_query(call.id, "❌ کاربر پیدا نشد!")


# ==================== دیتابیس پیام همگانی ====================


def setup_broadcast_db():
    """ایجاد دیتابیس پیام همگانی"""
    try:
        conn = sqlite3.connect("broadcast.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS broadcast_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            message_type TEXT NOT NULL,
            target_type TEXT NOT NULL,
            content TEXT NOT NULL,
            file_id TEXT,
            caption TEXT,
            scheduled_time TEXT,
            is_sent BOOLEAN DEFAULT 0,
            sent_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_at TIMESTAMP NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS broadcast_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            broadcast_id INTEGER,
            user_id INTEGER,
            status TEXT DEFAULT 'pending',
            sent_at TIMESTAMP NULL,
            FOREIGN KEY (broadcast_id) REFERENCES broadcast_messages(id)
        )
        """)

        conn.commit()
        conn.close()
        print("✅ دیتابیس پیام همگانی ایجاد شد")
        return True
    except Exception as e:
        print(f"❌ خطا در ایجاد دیتابیس پیام همگانی: {e}")
        return False


def safe_execute_broadcast_db(query, params=()):
    """اجرای ایمن کوئری‌های دیتابیس پیام همگانی"""
    try:
        conn = sqlite3.connect("broadcast.db", check_same_thread=False)
        cur = conn.cursor()
        cur.execute(query, params)
        result = cur.fetchall()
        conn.commit()
        conn.close()
        return result
    except Exception as e:
        print(f"خطای دیتابیس پیام همگانی: {e}")
        return None

# ==================== منوی پیام همگانی ====================


def broadcast_menu():
    """منوی اصلی پیام همگانی"""
    markup = InlineKeyboardMarkup()

    markup.row(InlineKeyboardButton("🎯 ارسال هدفمند",
               callback_data="broadcast_targeted"))
    markup.row(InlineKeyboardButton("⏰ ارسال زمان‌بندی شده",
               callback_data="broadcast_scheduled"))
    markup.row(InlineKeyboardButton("⚡ ارسال فوری",
               callback_data="broadcast_instant"))
    markup.row(InlineKeyboardButton(
        "📊 آمار ارسال‌ها", callback_data="broadcast_stats"))
    markup.row(InlineKeyboardButton(
        "🔙 بازگشت به مدیریت", callback_data="admin_main"))

    return markup


@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def admin_broadcast_handler(call):
    """ورود به بخش پیام همگانی"""
    uid = call.message.chat.id

    if not is_admin(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی denied!")
        return

    # ایجاد دیتابیس اگر وجود ندارد
    setup_broadcast_db()

    try:
        bot.edit_message_text(
            "📢 **سیستم پیام همگانی**\n\n"
            "لطفا نوع ارسال پیام رو انتخاب کن:",
            uid, call.message.message_id,
            reply_markup=broadcast_menu(),
            parse_mode="Markdown"
        )
    except:
        bot.send_message(
            uid,
            "📢 **سیستم پیام همگانی**\n\n"
            "لطفا نوع ارسال پیام رو انتخاب کن:",
            reply_markup=broadcast_menu(),
            parse_mode="Markdown"
        )

# ==================== ارسال هدفمند ====================


@bot.callback_query_handler(func=lambda call: call.data == "broadcast_targeted")
def broadcast_targeted_handler(call):
    """منوی ارسال هدفمند"""
    uid = call.message.chat.id

    markup = InlineKeyboardMarkup()

    markup.row(
        InlineKeyboardButton("👤 کاربران سینگل", callback_data="target_single"),
        InlineKeyboardButton(
            "💞 کاربران متصل", callback_data="target_connection()ected")
    )
    markup.row(
        InlineKeyboardButton("👨 پسران", callback_data="target_boys"),
        InlineKeyboardButton("👩 دختران", callback_data="target_girls")
    )
    markup.row(
        InlineKeyboardButton(
            "👨‍💼 پسران متصل", callback_data="target_boys_connected"),
        InlineKeyboardButton(
            "👩‍💼 دختران متصل", callback_data="target_girls_connected")
    )
    markup.row(InlineKeyboardButton(
        "🔙 بازگشت", callback_data="admin_broadcast"))

    try:
        bot.edit_message_text(
            "🎯 **ارسال هدفمند**\n\n"
            "لطفا گروه هدف رو انتخاب کن:",
            uid, call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except:
        bot.send_message(
            uid,
            "🎯 **ارسال هدفمند**\n\n"
            "لطفا گروه هدف رو انتخاب کن:",
            reply_markup=markup,
            parse_mode="Markdown"
        )

# ==================== ارسال زمان‌بندی شده ====================


@bot.callback_query_handler(func=lambda call: call.data == "broadcast_scheduled")
def broadcast_scheduled_handler(call):
    """شروع ارسال زمان‌بندی شده"""
    uid = call.message.chat.id

    user_state[uid] = "broadcast_waiting_schedule_time"
    temp_data[uid] = {
        "broadcast_type": "scheduled",
        "target_type": "all"  # پیش‌فرض همه کاربران
    }

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(
        "🔙 بازگشت", callback_data="admin_broadcast"))

    try:
        bot.edit_message_text(
            "⏰ **ارسال زمان‌بندی شده**\n\n"
            "لطفا تاریخ و زمان ارسال رو وارد کن:\n"
            "فرمت: 1403-01-15 14:30\n"
            "یا: 2024-04-05 14:30",
            uid, call.message.message_id,
            reply_markup=markup
        )
    except:
        bot.send_message(
            uid,
            "⏰ **ارسال زمان‌بندی شده**\n\n"
            "لطفا تاریخ و زمان ارسال رو وارد کن:\n"
            "فرمت: 1403-01-15 14:30\n"
            "یا: 2024-04-05 14:30",
            reply_markup=markup
        )


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "broadcast_waiting_schedule_time")
def broadcast_schedule_time_handler(message):
    """دریافت زمان ارسال"""
    uid = message.chat.id

    try:
        # تجزیه تاریخ و زمان
        time_input = message.text.strip()
        scheduled_time = parse_datetime_input(time_input)

        if not scheduled_time:
            bot.send_message(uid, "❌ فرمت زمان نامعتبر! لطفا دوباره وارد کن:")
            return

        # بررسی اینکه زمان در آینده باشد
        if scheduled_time <= datetime.now():
            bot.send_message(
                uid, "❌ زمان باید در آینده باشد! لطفا دوباره وارد کن:")
            return

        temp_data[uid]["scheduled_time"] = scheduled_time.isoformat()
        user_state[uid] = "broadcast_waiting_target_scheduled"

        # نمایش منوی انتخاب هدف برای زمان‌بندی شده
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("👤 همه کاربران", callback_data="target_all"),
            InlineKeyboardButton(
                "💞 کاربران متصل", callback_data="target_connection()ected")
        )
        markup.row(
            InlineKeyboardButton(
                "👤 کاربران سینگل", callback_data="target_single"),
            InlineKeyboardButton("👨 پسران", callback_data="target_boys")
        )
        markup.row(
            InlineKeyboardButton("👩 دختران", callback_data="target_girls"),
            InlineKeyboardButton(
                "🔙 بازگشت", callback_data="broadcast_scheduled")
        )

        bot.send_message(
            uid,
            f"✅ زمان ارسال ثبت شد: {scheduled_time.strftime('%Y-%m-%d %H:%M')}\n\n"
            "🎯 حالا گروه هدف رو انتخاب کن:",
            reply_markup=markup
        )

    except Exception as e:
        bot.send_message(uid, f"❌ خطا در پردازش زمان: {str(e)}")


def parse_datetime_input(text):
    """تبدیل متن تاریخ و زمان به شی datetime"""
    try:
        text = text.strip()

        if " " in text:
            date_part, time_part = text.split(" ", 1)

            # بررسی فرمت شمسی
            if "-" in date_part and len(date_part.split("-")) == 3:
                parts = date_part.split("-")
                if len(parts[0]) == 4:  # سال شمسی
                    y, m, d = map(int, parts)
                    jd = jdatetime.date(y, m, d)
                    gdate = jd.togregorian()

                    # تجزیه زمان
                    if ":" in time_part:
                        hour, minute = map(int, time_part.split(":"))
                        return datetime.combine(gdate, datetime.min.time().replace(hour=hour, minute=minute))

            # بررسی فرمت میلادی
            elif "-" in date_part and len(date_part.split("-")) == 3:
                gdate = datetime.strptime(date_part, "%Y-%m-%d").date()

                # تجزیه زمان
                if ":" in time_part:
                    hour, minute = map(int, time_part.split(":"))
                    return datetime.combine(gdate, datetime.min.time().replace(hour=hour, minute=minute))

        return None
    except:
        return None

# ==================== ارسال فوری ====================


@bot.callback_query_handler(func=lambda call: call.data == "broadcast_instant")
def broadcast_instant_handler(call):
    """شروع ارسال فوری"""
    uid = call.message.chat.id

    user_state[uid] = "broadcast_waiting_content"
    temp_data[uid] = {
        "broadcast_type": "instant",
        "target_type": "all"  # پیش‌فرض همه کاربران
    }

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(
        "🔙 بازگشت", callback_data="admin_broadcast"))

    try:
        bot.edit_message_text(
            "⚡ **ارسال فوری**\n\n"
            "لطفا محتوای پیام رو ارسال کن:\n"
            "• متن ساده\n"
            "• عکس\n"
            "• ویدیو\n"
            "• فایل\n"
            "• یا هرکدام با کپشن",
            uid, call.message.message_id,
            reply_markup=markup
        )
    except:
        bot.send_message(
            uid,
            "⚡ **ارسال فوری**\n\n"
            "لطفا محتوای پیام رو ارسال کن:\n"
            "• متن ساده\n"
            "• عکس\n"
            "• ویدیو\n"
            "• فایل\n"
            "• یا هرکدام با کپشن",
            reply_markup=markup
        )

# ==================== انتخاب هدف ====================


@bot.callback_query_handler(func=lambda call: call.data.startswith("target_"))
def broadcast_target_handler(call):
    """انتخاب گروه هدف"""
    uid = call.message.chat.id

    target_type = call.data.split("_")[1]

    # برای ارسال زمان‌بندی شده
    if user_state.get(uid) == "broadcast_waiting_target_scheduled":
        temp_data[uid]["target_type"] = target_type
        user_state[uid] = "broadcast_waiting_content"

        target_names = {
            "all": "همه کاربران",
            "single": "کاربران سینگل",
            "connected": "کاربران متصل",
            "boys": "پسران",
            "girls": "دختران",
            "boys_connected": "پسران متصل",
            "girls_connected": "دختران متصل"
        }

        bot.edit_message_text(
            f"✅ گروه هدف: {target_names.get(target_type, target_type)}\n\n"
            f"📝 حالا محتوای پیام رو ارسال کن:",
            uid, call.message.message_id
        )

    # برای ارسال هدفمند
    else:
        temp_data[uid] = {
            "broadcast_type": "targeted",
            "target_type": target_type
        }
        user_state[uid] = "broadcast_waiting_content"

        target_names = {
            "single": "کاربران سینگل",
            "connected": "کاربران متصل",
            "boys": "پسران",
            "girls": "دختران",
            "boys_connected": "پسران متصل",
            "girls_connected": "دختران متصل"
        }

        bot.edit_message_text(
            f"🎯 **ارسال هدفمند**\n\n"
            f"✅ گروه هدف: {target_names.get(target_type, target_type)}\n\n"
            f"📝 حالا محتوای پیام رو ارسال کن:",
            uid, call.message.message_id,
            parse_mode="Markdown"
        )

# ==================== دریافت محتوا ====================


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "broadcast_waiting_content",
                     content_types=['text', 'photo', 'video', 'document', 'audio'])
def broadcast_content_handler(message):
    """دریافت محتوای پیام همگانی"""
    uid = message.chat.id

    try:
        data = temp_data[uid]
        content_data = {}

        # تشخیص نوع محتوا
        if message.content_type == 'text':
            content_data = {
                'message_type': 'text',
                'content': message.text,
                'file_id': None,
                'caption': None
            }

        elif message.content_type == 'photo':
            content_data = {
                'message_type': 'photo',
                'content': 'عکس',
                'file_id': message.photo[-1].file_id,  # بالاترین کیفیت
                'caption': message.caption
            }

        elif message.content_type == 'video':
            content_data = {
                'message_type': 'video',
                'content': 'ویدیو',
                'file_id': message.video.file_id,
                'caption': message.caption
            }

        elif message.content_type == 'document':
            content_data = {
                'message_type': 'document',
                'content': 'فایل',
                'file_id': message.document.file_id,
                'caption': message.caption
            }

        elif message.content_type == 'audio':
            content_data = {
                'message_type': 'audio',
                'content': 'آudio',
                'file_id': message.audio.file_id,
                'caption': message.caption
            }

        # ذخیره داده‌ها
        data.update(content_data)

        # نمایش تأیید و شروع ارسال
        show_broadcast_confirmation(uid, data, message.message_id)

    except Exception as e:
        print(f"❌ خطا در پردازش محتوا: {e}")
        bot.send_message(uid, "❌ خطا در پردازش محتوا!")


def show_broadcast_confirmation(uid, data, message_id=None):
    """نمایش تأیید نهایی و شروع ارسال"""

    # محاسبه تعداد کاربران هدف
    target_count = count_target_users(data['target_type'])

    # ساخت متن تأیید
    confirmation_text = "✅ **پیام همگانی آماده ارسال**\n\n"

    # نوع ارسال
    broadcast_types = {
        "instant": "⚡ فوری",
        "scheduled": "⏰ زمان‌بندی شده",
        "targeted": "🎯 هدفمند"
    }

    confirmation_text += f"📤 **نوع ارسال:** {broadcast_types[data['broadcast_type']]}\n"

    # گروه هدف
    target_names = {
        "all": "همه کاربران",
        "single": "کاربران سینگل",
        "connected": "کاربران متصل",
        "boys": "پسران",
        "girls": "دختران",
        "boys_connected": "پسران متصل",
        "girls_connected": "دختران متصل"
    }

    confirmation_text += f"🎯 **گروه هدف:** {target_names[data['target_type']]}\n"
    confirmation_text += f"👥 **تعداد کاربران:** {target_count} نفر\n"

    # زمان ارسال (برای زمان‌بندی شده)
    if data['broadcast_type'] == 'scheduled' and 'scheduled_time' in data:
        scheduled_dt = datetime.fromisoformat(data['scheduled_time'])
        confirmation_text += f"⏰ **زمان ارسال:** {scheduled_dt.strftime('%Y-%m-%d %H:%M')}\n"

    # نوع محتوا
    content_types = {
        'text': '📝 متن ساده',
        'photo': '🖼️ عکس',
        'video': '🎥 ویدیو',
        'document': '📎 فایل',
        'audio': '🎵 آudio'
    }

    confirmation_text += f"📦 **نوع محتوا:** {content_types[data['message_type']]}\n\n"

    # پیش‌نمایش محتوا
    if data['message_type'] == 'text':
        preview = data['content'][:100] + \
            "..." if len(data['content']) > 100 else data['content']
        confirmation_text += f"📋 **پیش‌نمایش:**\n{preview}\n\n"
    elif data['caption']:
        preview = data['caption'][:100] + \
            "..." if len(data['caption']) > 100 else data['caption']
        confirmation_text += f"📋 **کپشن:**\n{preview}\n\n"

    confirmation_text += "⚠️ **آیا مطمئنی می‌خوای ارسال کنی؟**"

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(
            "✅ بله، ارسال کن", callback_data="confirm_broadcast"),
        InlineKeyboardButton("❌ لغو", callback_data="cancel_broadcast")
    )

    if message_id:
        try:
            bot.edit_message_text(
                confirmation_text,
                uid, message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except:
            bot.send_message(uid, confirmation_text,
                             reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(uid, confirmation_text,
                         reply_markup=markup, parse_mode="Markdown")


def count_target_users(target_type):
    """شمارش کاربران بر اساس نوع هدف"""
    try:
        conn = sqlite3.connect("relation_agent.db", check_same_thread=False)
        cur = conn.cursor()

        query = "SELECT COUNT(*) FROM users WHERE 1=1"

        if target_type == "single":
            query += " AND (partner_id IS NULL OR connection_status != 'connected')"
        elif target_type == "connected":
            query += " AND connection_status = 'connected'"
        elif target_type == "boys":
            query += " AND gender = 'مرد'"
        elif target_type == "girls":
            query += " AND gender = 'زن'"
        elif target_type == "boys_connected":
            query += " AND gender = 'مرد' AND connection_status = 'connected'"
        elif target_type == "girls_connected":
            query += " AND gender = 'زن' AND connection_status = 'connected'"

        cur.execute(query)
        count = cur.fetchone()[0]
        conn.close()

        return count

    except Exception as e:
        print(f"❌ خطا در شمارش کاربران: {e}")
        return 0

# ==================== تأیید و ارسال ====================


@bot.callback_query_handler(func=lambda call: call.data == "confirm_broadcast")
def confirm_broadcast_handler(call):
    """تأیید نهایی و شروع ارسال"""
    uid = call.message.chat.id

    if uid not in temp_data:
        bot.answer_callback_query(call.id, "❌ داده‌ها پیدا نشد!")
        return

    data = temp_data[uid]

    try:
        # ذخیره در دیتابیس
        broadcast_id = save_broadcast_to_db(uid, data)

        if not broadcast_id:
            bot.answer_callback_query(call.id, "❌ خطا در ذخیره پیام!")
            return

        # ارسال پیام
        if data['broadcast_type'] == 'instant':
            # ارسال فوری
            start_instant_broadcast(uid, broadcast_id, data)
        elif data['broadcast_type'] == 'scheduled':
            # زمان‌بندی شده
            schedule_broadcast(uid, broadcast_id, data)
        else:
            # هدفمند
            start_targeted_broadcast(uid, broadcast_id, data)

        # پاکسازی state
        user_state.pop(uid, None)
        temp_data.pop(uid, None)

    except Exception as e:
        print(f"❌ خطا در ارسال پیام همگانی: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در ارسال!")


def save_broadcast_to_db(admin_id, data):
    """ذخیره پیام همگانی در دیتابیس - نسخه اصلاح شده"""
    try:
        print(f"🔧 دیباگ: شروع ذخیره پیام برای ادمین {admin_id}")
        print(f"🔧 دیباگ: داده‌ها: {data}")

        conn = sqlite3.connect("broadcast.db", check_same_thread=False)
        cur = conn.cursor()

        # بررسی وجود جدول
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='broadcast_messages'")
        table_exists = cur.fetchone()

        if not table_exists:
            print("❌ جدول broadcast_messages وجود ندارد!")
            conn.close()
            return None

        # ذخیره پیام
        cur.execute("""
            INSERT INTO broadcast_messages 
            (admin_id, message_type, target_type, content, file_id, caption, scheduled_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            admin_id,
            data.get('message_type', 'text'),
            data.get('target_type', 'all'),
            data.get('content', ''),
            data.get('file_id'),
            data.get('caption'),
            data.get('scheduled_time')
        ))

        conn.commit()

        # دریافت آیدی پیام ذخیره شده
        cur.execute("SELECT last_insert_rowid()")
        result = cur.fetchone()
        broadcast_id = result[0] if result else None

        conn.close()

        print(f"✅ دیباگ: پیام با موفقیت ذخیره شد. ID: {broadcast_id}")
        return broadcast_id

    except Exception as e:
        print(f"❌ خطا در ذخیره پیام همگانی: {e}")
        import traceback
        traceback.print_exc()
        return None


@bot.callback_query_handler(func=lambda call: call.data == "confirm_broadcast")
def confirm_broadcast_handler(call):
    """تأیید نهایی و شروع ارسال - نسخه اصلاح شده"""
    uid = call.message.chat.id

    try:
        bot.answer_callback_query(call.id, "⏳ درحال پردازش...")

        if uid not in temp_data:
            bot.answer_callback_query(call.id, "❌ داده‌ها پیدا نشد!")
            return

        data = temp_data[uid]
        print(f"🔧 دیباگ: داده‌های temp_data: {data}")

        # ذخیره در دیتابیس
        broadcast_id = save_broadcast_to_db(uid, data)

        if not broadcast_id:
            bot.edit_message_text(
                "❌ **خطا در ذخیره پیام!**\n\nلطفا دوباره تلاش کنید.",
                uid, call.message.message_id,
                parse_mode="Markdown"
            )
            return

        # ارسال پیام بر اساس نوع
        if data['broadcast_type'] == 'instant':
            start_instant_broadcast(uid, broadcast_id, data)
        elif data['broadcast_type'] == 'scheduled':
            schedule_broadcast(uid, broadcast_id, data)
        else:  # targeted
            start_targeted_broadcast(uid, broadcast_id, data)

        # پاکسازی state
        user_state.pop(uid, None)
        temp_data.pop(uid, None)

    except Exception as e:
        print(f"❌ خطا در تأیید ارسال: {e}")
        import traceback
        traceback.print_exc()

        bot.answer_callback_query(call.id, "❌ خطا در ارسال!")
        bot.edit_message_text(
            "❌ **خطا در ارسال پیام!**\n\nلطفا دوباره تلاش کنید.",
            uid, call.message.message_id,
            parse_mode="Markdown"
        )


def start_targeted_broadcast(admin_id, broadcast_id, data):
    """شروع ارسال هدفمند"""
    try:
        # شمارش کاربران
        target_count = count_target_users(data['target_type'])

        bot.send_message(
            admin_id,
            f"🎯 **شروع ارسال هدفمند**\n\n"
            f"📤 درحال ارسال به {target_count} کاربر...\n"
            f"⏳ لطفا صبر کن...",
            parse_mode="Markdown"
        )

        # شروع ارسال در thread جداگانه
        thread = threading.Thread(
            target=send_broadcast_messages,
            args=(admin_id, broadcast_id, data)
        )
        thread.daemon = True
        thread.start()

    except Exception as e:
        print(f"❌ خطا در شروع ارسال هدفمند: {e}")

# همچنین تابع count_target_users رو هم چک می‌کنیم:


def count_target_users(target_type):
    """شمارش کاربران بر اساس نوع هدف - نسخه اصلاح شده"""
    try:
        conn = sqlite3.connect("relation_agent.db", check_same_thread=False)
        cur = conn.cursor()

        # بررسی وجود جدول users
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        table_exists = cur.fetchone()

        if not table_exists:
            print("❌ جدول users وجود ندارد!")
            conn.close()
            return 0

        query = "SELECT COUNT(*) FROM users WHERE 1=1"
        params = []

        if target_type == "single":
            query += " AND (partner_id IS NULL OR partner_id = '' OR connection_status != 'connected')"
        elif target_type == "connected":
            query += " AND connection_status = 'connected'"
        elif target_type == "boys":
            query += " AND gender = 'مرد'"
        elif target_type == "girls":
            query += " AND gender = 'زن'"
        elif target_type == "boys_connected":
            query += " AND gender = 'مرد' AND connection_status = 'connected'"
        elif target_type == "girls_connected":
            query += " AND gender = 'زن' AND connection_status = 'connected'"

        print(f"🔧 دیباگ: اجرای کوئری: {query}")
        cur.execute(query)
        count = cur.fetchone()[0]
        conn.close()

        print(f"✅ دیباگ: تعداد کاربران {target_type}: {count}")
        return count

    except Exception as e:
        print(f"❌ خطا در شمارش کاربران: {e}")
        import traceback
        traceback.print_exc()
        return 0

# و تابع setup_broadcast_db رو مطمئن می‌کنیم که درست کار کند:


def setup_broadcast_db():
    """ایجاد دیتابیس پیام همگانی - نسخه بهبود یافته"""
    try:
        conn = sqlite3.connect("broadcast.db", check_same_thread=False)
        cur = conn.cursor()

        # ایجاد جدول اصلی پیام‌ها
        cur.execute("""
        CREATE TABLE IF NOT EXISTS broadcast_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            message_type TEXT NOT NULL,
            target_type TEXT NOT NULL,
            content TEXT NOT NULL,
            file_id TEXT,
            caption TEXT,
            scheduled_time TEXT,
            is_sent BOOLEAN DEFAULT 0,
            sent_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_at TIMESTAMP NULL
        )
        """)

        # ایجاد جدول آمار
        cur.execute("""
        CREATE TABLE IF NOT EXISTS broadcast_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            broadcast_id INTEGER,
            user_id INTEGER,
            status TEXT DEFAULT 'pending',
            sent_at TIMESTAMP NULL,
            FOREIGN KEY (broadcast_id) REFERENCES broadcast_messages(id)
        )
        """)

        # ایجاد ایندکس‌ها
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_broadcast_admin ON broadcast_messages(admin_id)")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_broadcast_sent ON broadcast_messages(is_sent)")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_stats_broadcast ON broadcast_stats(broadcast_id)")

        conn.commit()
        conn.close()
        print("✅ دیتابیس پیام همگانی ایجاد/بررسی شد")
        return True
    except Exception as e:
        print(f"❌ خطا در ایجاد دیتابیس پیام همگانی: {e}")
        import traceback
        traceback.print_exc()
        return False


# همچنین مطمئن شویم که در ابتدا دیتابیس راه‌اندازی شده:
print("🔄 راه‌اندازی دیتابیس پیام همگانی...")
setup_broadcast_db()


def start_instant_broadcast(admin_id, broadcast_id, data):
    """شروع ارسال فوری"""
    try:
        # شمارش کاربران
        target_count = count_target_users(data['target_type'])

        # ارسال پیام شروع
        bot.send_message(
            admin_id,
            f"🚀 **شروع ارسال فوری**\n\n"
            f"📤 درحال ارسال به {target_count} کاربر...\n"
            f"⏳ لطفا صبر کن...",
            parse_mode="Markdown"
        )

        # شروع ارسال در thread جداگانه
        thread = threading.Thread(
            target=send_broadcast_messages,
            args=(admin_id, broadcast_id, data)
        )
        thread.daemon = True
        thread.start()

    except Exception as e:
        print(f"❌ خطا در شروع ارسال فوری: {e}")


def send_broadcast_messages(admin_id, broadcast_id, data):
    """ارسال پیام‌ها به کاربران"""
    try:
        # دریافت لیست کاربران هدف
        users = get_target_users(data['target_type'])
        total_users = len(users)
        sent_count = 0
        failed_count = 0

        # به روزرسانی وضعیت
        safe_execute_broadcast_db(
            "UPDATE broadcast_messages SET is_sent = 1, sent_at = CURRENT_TIMESTAMP WHERE id = ?",
            (broadcast_id,)
        )

        # ارسال به هر کاربر
        for user_id in users:
            try:
                success = send_message_to_user(user_id, data)

                if success:
                    sent_count += 1
                    # ذخیره وضعیت موفق
                    safe_execute_broadcast_db("""
                        INSERT INTO broadcast_stats (broadcast_id, user_id, status, sent_at)
                        VALUES (?, ?, 'sent', CURRENT_TIMESTAMP)
                    """, (broadcast_id, user_id))
                else:
                    failed_count += 1
                    # ذخیره وضعیت ناموفق
                    safe_execute_broadcast_db("""
                        INSERT INTO broadcast_stats (broadcast_id, user_id, status)
                        VALUES (?, ?, 'failed')
                    """, (broadcast_id, user_id))

                # گزارش پیشرفت هر 10 کاربر
                if (sent_count + failed_count) % 10 == 0:
                    progress = (sent_count + failed_count) / total_users * 100
                    bot.send_message(
                        admin_id,
                        f"📊 **پیشرفت ارسال:** {progress:.1f}%\n"
                        f"✅ ارسال شده: {sent_count}\n"
                        f"❌ ناموفق: {failed_count}",
                        parse_mode="Markdown"
                    )

                # تأخیر برای جلوگیری از محدودیت تلگرام
                time.sleep(0.1)

            except Exception as e:
                print(f"❌ خطا در ارسال به کاربر {user_id}: {e}")
                failed_count += 1
                continue

        # گزارش نهایی
        final_report = (
            f"🎉 **ارسال پیام همگانی تکمیل شد!**\n\n"
            f"📊 **گزارش نهایی:**\n"
            f"• کل کاربران: {total_users}\n"
            f"• ✅ ارسال موفق: {sent_count}\n"
            f"• ❌ ارسال ناموفق: {failed_count}\n"
            f"• 📈 نرخ موفقیت: {(sent_count/total_users*100):.1f}%"
        )

        # به روزرسانی آمار در دیتابیس
        safe_execute_broadcast_db("""
            UPDATE broadcast_messages 
            SET sent_count = ?, failed_count = ? 
            WHERE id = ?
        """, (sent_count, failed_count, broadcast_id))

        bot.send_message(admin_id, final_report, parse_mode="Markdown")

    except Exception as e:
        print(f"❌ خطا در ارسال پیام‌ها: {e}")
        bot.send_message(admin_id, "❌ خطا در ارسال پیام همگانی!")


def get_target_users(target_type):
    """دریافت لیست کاربران هدف"""
    try:
        conn = sqlite3.connect("relation_agent.db", check_same_thread=False)
        cur = conn.cursor()

        query = "SELECT user_id FROM users WHERE 1=1"

        if target_type == "single":
            query += " AND (partner_id IS NULL OR connection_status != 'connected')"
        elif target_type == "connected":
            query += " AND connection_status = 'connected'"
        elif target_type == "boys":
            query += " AND gender = 'مرد'"
        elif target_type == "girls":
            query += " AND gender = 'زن'"
        elif target_type == "boys_connected":
            query += " AND gender = 'مرد' AND connection_status = 'connected'"
        elif target_type == "girls_connected":
            query += " AND gender = 'زن' AND connection_status = 'connected'"

        cur.execute(query)
        users = [row[0] for row in cur.fetchall()]
        conn.close()

        return users

    except Exception as e:
        print(f"❌ خطا در دریافت کاربران هدف: {e}")
        return []


def send_message_to_user(user_id, data):
    """ارسال پیام به یک کاربر"""
    try:
        if data['message_type'] == 'text':
            bot.send_message(user_id, data['content'])

        elif data['message_type'] == 'photo':
            if data.get('caption'):
                bot.send_photo(
                    user_id, data['file_id'], caption=data['caption'])
            else:
                bot.send_photo(user_id, data['file_id'])

        elif data['message_type'] == 'video':
            if data.get('caption'):
                bot.send_video(
                    user_id, data['file_id'], caption=data['caption'])
            else:
                bot.send_video(user_id, data['file_id'])

        elif data['message_type'] == 'document':
            if data.get('caption'):
                bot.send_document(
                    user_id, data['file_id'], caption=data['caption'])
            else:
                bot.send_document(user_id, data['file_id'])

        elif data['message_type'] == 'audio':
            if data.get('caption'):
                bot.send_audio(
                    user_id, data['file_id'], caption=data['caption'])
            else:
                bot.send_audio(user_id, data['file_id'])

        return True

    except Exception as e:
        print(f"❌ خطا در ارسال به کاربر {user_id}: {e}")
        return False

# ==================== سیستم زمان‌بندی ====================


def schedule_broadcast(admin_id, broadcast_id, data):
    """زمان‌بندی ارسال پیام"""
    try:
        scheduled_time = datetime.fromisoformat(data['scheduled_time'])
        now = datetime.now()
        delay = (scheduled_time - now).total_seconds()

        if delay <= 0:
            # اگر زمان گذشته، ارسال فوری
            start_instant_broadcast(admin_id, broadcast_id, data)
        else:
            # زمان‌بندی ارسال
            bot.send_message(
                admin_id,
                f"⏰ **پیام زمان‌بندی شد**\n\n"
                f"📅 در تاریخ: {scheduled_time.strftime('%Y-%m-%d %H:%M')}\n"
                f"⏳ زمان باقی‌مانده: {int(delay//3600)} ساعت و {int((delay%3600)//60)} دقیقه",
                parse_mode="Markdown"
            )

            # زمان‌بندی در thread
            threading.Timer(delay, start_instant_broadcast, [
                            admin_id, broadcast_id, data]).start()

    except Exception as e:
        print(f"❌ خطا در زمان‌بندی: {e}")
        bot.send_message(admin_id, "❌ خطا در زمان‌بندی پیام!")

# ==================== لغو ارسال ====================


@bot.callback_query_handler(func=lambda call: call.data == "cancel_broadcast")
def cancel_broadcast_handler(call):
    """لغو ارسال پیام همگانی"""
    uid = call.message.chat.id

    # پاکسازی state
    user_state.pop(uid, None)
    temp_data.pop(uid, None)

    bot.edit_message_text(
        "❌ **ارسال پیام لغو شد**",
        uid, call.message.message_id
    )

    # بازگشت به منوی اصلی
    admin_broadcast_handler(call)

# ==================== آمار ارسال‌ها ====================


@bot.callback_query_handler(func=lambda call: call.data == "broadcast_stats")
def broadcast_stats_handler(call):
    """نمایش آمار ارسال‌های قبلی"""
    uid = call.message.chat.id

    try:
        # دریافت آخرین ارسال‌ها
        broadcasts = safe_execute_broadcast_db("""
            SELECT id, message_type, target_type, sent_count, failed_count, created_at, scheduled_time
            FROM broadcast_messages 
            WHERE admin_id = ?
            ORDER BY created_at DESC 
            LIMIT 10
        """, (uid,))

        if not broadcasts:
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton(
                "📢 ارسال پیام جدید", callback_data="admin_broadcast"))
            markup.row(InlineKeyboardButton(
                "🔙 بازگشت", callback_data="admin_main"))

            bot.edit_message_text(
                "📊 **آمار ارسال‌ها**\n\n"
                "هنوز هیچ پیامی ارسال نکرده‌اید!",
                uid, call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
            return

        text = "📊 **آمار آخرین ارسال‌ها**\n\n"

        for broadcast in broadcasts:
            (b_id, msg_type, target_type, sent, failed,
             created_at, scheduled_time) = broadcast

            # نوع پیام
            type_icons = {'text': '📝', 'photo': '🖼️',
                          'video': '🎥', 'document': '📎', 'audio': '🎵'}

            # گروه هدف
            target_names = {
                "all": "همه", "single": "سینگل", "connected": "متصل",
                "boys": "پسران", "girls": "دختران"
            }

            created_dt = datetime.fromisoformat(created_at)
            created_str = created_dt.strftime("%m/%d %H:%M")

            total = sent + failed
            success_rate = (sent / total * 100) if total > 0 else 0

            text += (
                f"{type_icons.get(msg_type, '📨')} **{target_names.get(target_type, target_type)}**\n"
                f"📅 {created_str} | ✅ {sent} | ❌ {failed} | 📈 {success_rate:.1f}%\n\n"
            )

        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton(
            "📢 ارسال پیام جدید", callback_data="admin_broadcast"))
        markup.row(InlineKeyboardButton(
            "🔙 بازگشت", callback_data="admin_main"))

        bot.edit_message_text(
            text,
            uid, call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )

    except Exception as e:
        print(f"❌ خطا در نمایش آمار: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در نمایش آمار!")

# ==================== تابع کمکی ====================


def is_admin(user_id):
    """بررسی اینکه کاربر ادمین است"""
    # این تابع باید با توجه به سیستم ادمین‌های شما پیاده‌سازی شود
    ADMIN_IDS = [8000307737]  # آیدی‌های ادمین‌ها
    return user_id in ADMIN_IDS


# راه‌اندازی اولیه
setup_broadcast_db()


# ==================== دیتابیس مدیریت ربات ====================


def setup_bot_management_db():
    """ایجاد دیتابیس مدیریت ربات"""
    try:
        conn = sqlite3.connect("bot_management.db", check_same_thread=False)
        cur = conn.cursor()

        # تنظیمات ربات
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bot_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT NOT NULL,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # وضعیت ربات
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bot_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL,
            changed_by INTEGER NOT NULL,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # بکاپ‌ها
        cur.execute("""
        CREATE TABLE IF NOT EXISTS backup_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            backup_name TEXT NOT NULL,
            file_size INTEGER,
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # تنظیمات اولیه
        cur.execute(
            "INSERT OR IGNORE INTO bot_settings (setting_key, setting_value, description) VALUES ('bot_state', 'active', 'وضعیت ربات')")
        cur.execute("INSERT OR IGNORE INTO bot_settings (setting_key, setting_value, description) VALUES ('maintenance_message', '🤖 ربات در حال تعمیرات است. لطفاً稍后 مراجعه کنید.', 'پیام حالت تعمیر')")
        cur.execute("INSERT OR IGNORE INTO bot_settings (setting_key, setting_value, description) VALUES ('stop_message', '❌ ربات موقتاً غیرفعال شده است.', 'پیام خاموشی')")
        cur.execute(
            "INSERT OR IGNORE INTO bot_settings (setting_key, setting_value, description) VALUES ('auto_backup', '1', 'پشتیبان‌گیری خودکار')")
        cur.execute("INSERT OR IGNORE INTO bot_settings (setting_key, setting_value, description) VALUES ('backup_interval', '24', 'فاصله پشتیبان‌گیری (ساعت)')")

        conn.commit()
        conn.close()
        print("✅ دیتابیس مدیریت ربات ایجاد شد")
        return True
    except Exception as e:
        print(f"❌ خطا در ایجاد دیتابیس مدیریت: {e}")
        return False


def safe_execute_management_db(query, params=()):
    """اجرای ایمن کوئری‌های دیتابیس مدیریت"""
    try:
        conn = sqlite3.connect("bot_management.db", check_same_thread=False)
        cur = conn.cursor()
        cur.execute(query, params)
        result = cur.fetchall()
        conn.commit()
        conn.close()
        return result
    except Exception as e:
        print(f"خطای دیتابیس مدیریت: {e}")
        return None

# ==================== وضعیت ربات ====================


def get_bot_state():
    """دریافت وضعیت فعلی ربات"""
    try:
        result = safe_execute_management_db(
            "SELECT setting_value FROM bot_settings WHERE setting_key = 'bot_state'")
        return result[0][0] if result else 'active'
    except:
        return 'active'


def set_bot_state(new_state, admin_id, reason=""):
    """تغییر وضعیت ربات"""
    try:
        # ذخیره وضعیت قبلی برای لاگ
        old_state = get_bot_state()

        # به‌روزرسانی وضعیت
        safe_execute_management_db(
            "UPDATE bot_settings SET setting_value = ? WHERE setting_key = 'bot_state'", (new_state,))

        # ذخیره در تاریخچه
        safe_execute_management_db("INSERT INTO bot_status (status, changed_by, reason) VALUES (?, ?, ?)",
                                   (new_state, admin_id, reason))

        print(
            f"✅ وضعیت ربات از {old_state} به {new_state} تغییر کرد توسط ادمین {admin_id}")
        return True
    except Exception as e:
        print(f"❌ خطا در تغییر وضعیت ربات: {e}")
        return False


def get_bot_status_message():
    """دریافت پیام متناسب با وضعیت ربات"""
    state = get_bot_state()

    if state == 'maintenance':
        result = safe_execute_management_db(
            "SELECT setting_value FROM bot_settings WHERE setting_key = 'maintenance_message'")
        return result[0][0] if result else "🤖 ربات در حال تعمیرات است..."
    elif state == 'stopped':
        result = safe_execute_management_db(
            "SELECT setting_value FROM bot_settings WHERE setting_key = 'stop_message'")
        return result[0][0] if result else "❌ ربات موقتاً غیرفعال شده است."
    else:
        return None


# دیتابیس ادمین‌ها
def setup_admin_db():
    conn = sqlite3.connect("admin_management.db", check_same_thread=False)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        full_name TEXT,
        permissions TEXT DEFAULT 'all',
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ادمین پیشفرض
    cur.execute("INSERT OR IGNORE INTO admins (user_id, username, permissions, created_by) VALUES (?, ?, ?, ?)",
                (8000307737, "Developer", "all", 0))

    conn.commit()
    conn.close()


def get_admin_permissions(user_id):
    """دریافت دسترسی‌های ادمین"""
    result = safe_execute_db(
        "SELECT permissions FROM admins WHERE user_id = ?", (user_id,), "admin_management")
    return result[0][0] if result else None


def is_admin(user_id):
    """بررسی ادمین بودن"""
    result = safe_execute_db(
        "SELECT 1 FROM admins WHERE user_id = ?", (user_id,), "admin_management")
    return result is not None


def add_admin(admin_id, target_user_id, username="", full_name=""):
    """افزودن ادمین جدید"""
    try:
        safe_execute_db("INSERT INTO admins (user_id, username, full_name, created_by) VALUES (?, ?, ?, ?)",
                        (target_user_id, username, full_name, admin_id), "admin_management")
        return True
    except:
        return False


def remove_admin(admin_id, target_user_id):
    """حذف ادمین"""
    safe_execute_db("DELETE FROM admins WHERE user_id = ? AND user_id != ?",
                    (target_user_id, admin_id), "admin_management")
    return True


def update_admin_permissions(admin_id, target_user_id, permissions):
    """ویرایش دسترسی ادمین"""
    safe_execute_db("UPDATE admins SET permissions = ? WHERE user_id = ?",
                    (permissions, target_user_id), "admin_management")
    return True


def setup_bot_status_db():
    conn = sqlite3.connect("bot_status.db", check_same_thread=False)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bot_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        status TEXT DEFAULT 'active',
        changed_by INTEGER,
        changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # وضعیت پیشفرض
    cur.execute(
        "INSERT OR IGNORE INTO bot_status (status, changed_by) VALUES ('active', 0)")

    conn.commit()
    conn.close()


def get_bot_status():
    """دریافت وضعیت ربات"""
    result = safe_execute_db(
        "SELECT status FROM bot_status ORDER BY id DESC LIMIT 1", db_type="bot_status")
    return result[0][0] if result else 'active'


def set_bot_status(new_status, admin_id):
    """تغییر وضعیت ربات"""
    safe_execute_db("INSERT INTO bot_status (status, changed_by) VALUES (?, ?)",
                    (new_status, admin_id), "bot_status")
    return True


def should_respond_to_user(user_id):
    """آیا ربات باید به کاربر پاسخ دهد؟"""
    status = get_bot_status()
    if status == 'stopped':
        return is_admin(user_id)  # فقط ادمین‌ها
    return True  # حالت فعال


def setup_logging_system():
    """سیستم لاگ‌گیری"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(
                f'bot_logs/{datetime.now().strftime("%Y-%m-%d")}.log'),
            logging.StreamHandler()
        ]
    )


def get_recent_logs(lines=50):
    """دریافت آخرین خطوط لاگ"""
    try:
        log_file = f'bot_logs/{datetime.now().strftime("%Y-%m-%d")}.log'
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            return ''.join(all_lines[-lines:])
    except:
        return "لاگی موجود نیست"


def get_log_files():
    """دریافت لیست فایل‌های لاگ"""
    import os
    if not os.path.exists('bot_logs'):
        os.makedirs('bot_logs')
    return [f for f in os.listdir('bot_logs') if f.endswith('.log')]


def get_database_files():
    """لیست تمام فایل‌های دیتابیس"""
    return [
        "relation_agent.db", "notifications.db", "secret_messages.db",
        "mood_tracking.db", "books.db", "special_messages.db",
        "broadcast.db", "admin_management.db", "bot_status.db"
    ]


def create_backup(admin_id, specific_file=None):
    """ایجاد بکاپ"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"backups/backup_{timestamp}"
        os.makedirs(backup_dir, exist_ok=True)

        files_to_backup = [
            specific_file] if specific_file else get_database_files()
        backed_up = []

        for file in files_to_backup:
            if os.path.exists(file):
                shutil.copy2(file, f"{backup_dir}/{file}")
                backed_up.append(file)

        # ذخیره اطلاعات بکاپ
        safe_execute_db("""
            INSERT INTO backup_history (backup_name, files, created_by) 
            VALUES (?, ?, ?)
        """, (f"backup_{timestamp}", ','.join(backed_up), admin_id), "backup_management")

        return True, backup_dir, backed_up
    except Exception as e:
        return False, str(e), []


def get_backup_files():
    """دریافت لیست بکاپ‌ها"""
    if not os.path.exists('backups'):
        os.makedirs('backups')
    return [f for f in os.listdir('backups') if os.path.isdir(f"backups/{f}")]


def create_zip_backup(admin_id):
    """ایجاد بکاپ زیپ شده"""
    try:
        success, backup_dir, files = create_backup(admin_id)
        if not success:
            return False, backup_dir

        zip_path = f"{backup_dir}.zip"
        shutil.make_archive(backup_dir, 'zip', backup_dir)
        shutil.rmtree(backup_dir)  # حذف پوشه اصلی

        return True, zip_path
    except Exception as e:
        return False, str(e)


def get_all_admins():
    """دریافت لیست تمام ادمین‌ها"""
    result = safe_execute_db(
        "SELECT user_id FROM admins", db_type="admin_management")
    return [row[0] for row in result] if result else []


def send_to_admins(message_type, content, file_id=None, caption=None, sender_id=None):
    """ارسال پیام به تمام ادمین‌ها"""
    admins = get_all_admins()
    success_count = 0

    for admin_id in admins:
        if admin_id == sender_id:  # به فرستنده ارسال نشود
            continue

        try:
            if message_type == 'text':
                bot.send_message(admin_id, content)
            elif message_type == 'photo':
                if caption:
                    bot.send_photo(admin_id, file_id, caption=caption)
                else:
                    bot.send_photo(admin_id, file_id)
            elif message_type == 'video':
                if caption:
                    bot.send_video(admin_id, file_id, caption=caption)
                else:
                    bot.send_video(admin_id, file_id)
            elif message_type == 'document':
                if caption:
                    bot.send_document(admin_id, file_id, caption=caption)
                else:
                    bot.send_document(admin_id, file_id)

            success_count += 1
        except Exception as e:
            print(f"خطا در ارسال به ادمین {admin_id}: {e}")

    return success_count, len(admins)

# هندلر اتوماتیک برای تشخیص نوع محتوا


@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def admin_broadcast_handler(message):
    """دریافت پیام برای ارسال به ادمین‌ها"""
    if not is_admin(message.chat.id):
        return

    # تشخیص نوع محتوا
    if message.content_type == 'text':
        send_to_admins('text', message.text, sender_id=message.chat.id)
    elif message.content_type == 'photo':
        send_to_admins(
            'photo', 'عکس', message.photo[-1].file_id, message.caption, message.chat.id)
    elif message.content_type == 'video':
        send_to_admins('video', 'ویدیو', message.video.file_id,
                       message.caption, message.chat.id)
    elif message.content_type == 'document':
        send_to_admins('document', 'فایل', message.document.file_id,
                       message.caption, message.chat.id)

    bot.send_message(message.chat.id, "✅ پیام به تمام ادمین‌ها ارسال شد")


# ==================== پنل مدیریت ربات - منوی اصلی ====================

def admin_bot_management_menu():
    """منوی اصلی مدیریت ربات"""
    markup = InlineKeyboardMarkup()

    markup.row(InlineKeyboardButton(
        "🟢 روشن کردن ربات", callback_data="botmgmt_start"))
    markup.row(InlineKeyboardButton(
        "🔴 خاموش کردن ربات", callback_data="botmgmt_stop"))
    markup.row(InlineKeyboardButton(
        "📊 وضعیت ربات", callback_data="botmgmt_status"))
    markup.row(InlineKeyboardButton("🛠️ مدیریت ادمین‌ها",
               callback_data="botmgmt_admin_management"))
    markup.row(InlineKeyboardButton(
        "💾 بکاپ‌گیری", callback_data="botmgmt_backup"))
    markup.row(InlineKeyboardButton("📩 پیام به ادمین‌ها",
               callback_data="botmgmt_message_admins"))
    markup.row(InlineKeyboardButton(
        "📋 مشاهده لاگ‌ها", callback_data="botmgmt_logs"))
    markup.row(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main"))

    return markup


@bot.callback_query_handler(func=lambda call: call.data == "admin_bot_management")
def admin_bot_management_handler(call):
    """ورود به بخش مدیریت ربات"""
    uid = call.message.chat.id

    try:
        bot.edit_message_text(
            "⚙️ **مدیریت ربات**\n\nلطفا گزینه مورد نظر را انتخاب کنید:",
            uid, call.message.message_id,
            reply_markup=admin_bot_management_menu(),
            parse_mode="Markdown"
        )
    except:
        bot.send_message(
            uid,
            "⚙️ **مدیریت ربات**\n\nلطفا گزینه مورد نظر را انتخاب کنید:",
            reply_markup=admin_bot_management_menu(),
            parse_mode="Markdown"
        )

# ==================== زیرمنوی مدیریت ادمین‌ها ====================


def botmgmt_admin_management_menu():
    """منوی مدیریت ادمین‌ها"""
    markup = InlineKeyboardMarkup()

    markup.row(InlineKeyboardButton("➕ افزودن ادمین",
               callback_data="botmgmt_admin_add"))
    markup.row(InlineKeyboardButton("🗑️ حذف ادمین",
               callback_data="botmgmt_admin_remove"))
    markup.row(InlineKeyboardButton("🔐 ویرایش دسترسی",
               callback_data="botmgmt_admin_permissions"))
    markup.row(InlineKeyboardButton("📋 لیست ادمین‌ها",
               callback_data="botmgmt_admin_list"))
    markup.row(InlineKeyboardButton(
        "🔙 بازگشت", callback_data="admin_bot_management"))

    return markup


@bot.callback_query_handler(func=lambda call: call.data == "botmgmt_admin_management")
def botmgmt_admin_management_handler(call):
    """ورود به مدیریت ادمین‌ها"""
    uid = call.message.chat.id

    try:
        bot.edit_message_text(
            "🛠️ **مدیریت ادمین‌ها**\n\nلطفا گزینه مورد نظر را انتخاب کنید:",
            uid, call.message.message_id,
            reply_markup=botmgmt_admin_management_menu(),
            parse_mode="Markdown"
        )
    except:
        bot.send_message(
            uid,
            "🛠️ **مدیریت ادمین‌ها**\n\nلطفا گزینه مورد نظر را انتخاب کنید:",
            reply_markup=botmgmt_admin_management_menu(),
            parse_mode="Markdown"
        )

# ==================== زیرمنوی بکاپ‌گیری ====================


def botmgmt_backup_menu():
    """منوی بکاپ‌گیری"""
    markup = InlineKeyboardMarkup()

    markup.row(InlineKeyboardButton("💾 بکاپ کامل",
               callback_data="botmgmt_backup_full"))
    markup.row(InlineKeyboardButton("📁 بکاپ انتخابی",
               callback_data="botmgmt_backup_select"))
    markup.row(InlineKeyboardButton("📦 دریافت بکاپ‌ها",
               callback_data="botmgmt_backup_list"))
    markup.row(InlineKeyboardButton("🗑️ مدیریت بکاپ‌ها",
               callback_data="botmgmt_backup_manage"))
    markup.row(InlineKeyboardButton(
        "🔙 بازگشت", callback_data="admin_bot_management"))

    return markup


@bot.callback_query_handler(func=lambda call: call.data == "botmgmt_backup")
def botmgmt_backup_handler(call):
    """ورود به بخش بکاپ‌گیری"""
    uid = call.message.chat.id

    try:
        bot.edit_message_text(
            "💾 **بکاپ‌گیری**\n\nلطفا گزینه مورد نظر را انتخاب کنید:",
            uid, call.message.message_id,
            reply_markup=botmgmt_backup_menu(),
            parse_mode="Markdown"
        )
    except:
        bot.send_message(
            uid,
            "💾 **بکاپ‌گیری**\n\nلطفا گزینه مورد نظر را انتخاب کنید:",
            reply_markup=botmgmt_backup_menu(),
            parse_mode="Markdown"
        )

# ==================== زیرمنوی لاگ‌ها ====================


def botmgmt_logs_menu():
    """منوی مشاهده لاگ‌ها"""
    markup = InlineKeyboardMarkup()

    markup.row(InlineKeyboardButton("📝 لاگ پیام‌ها",
               callback_data="botmgmt_logs_messages"))
    markup.row(InlineKeyboardButton("🚨 لاگ خطاها",
               callback_data="botmgmt_logs_errors"))
    markup.row(InlineKeyboardButton("👥 لاگ کاربران",
               callback_data="botmgmt_logs_users"))
    markup.row(InlineKeyboardButton("🛠️ لاگ ادمین‌ها",
               callback_data="botmgmt_logs_admins"))
    markup.row(InlineKeyboardButton(
        "🔙 بازگشت", callback_data="admin_bot_management"))

    return markup


@bot.callback_query_handler(func=lambda call: call.data == "botmgmt_logs")
def botmgmt_logs_handler(call):
    """ورود به بخش مشاهده لاگ‌ها"""
    uid = call.message.chat.id

    try:
        bot.edit_message_text(
            "📋 **مشاهده لاگ‌ها**\n\nلطفا گزینه مورد نظر را انتخاب کنید:",
            uid, call.message.message_id,
            reply_markup=botmgmt_logs_menu(),
            parse_mode="Markdown"
        )
    except:
        bot.send_message(
            uid,
            "📋 **مشاهده لاگ‌ها**\n\nلطفا گزینه مورد نظر را انتخاب کنید:",
            reply_markup=botmgmt_logs_menu(),
            parse_mode="Markdown"
        )

# ==================== هندلرهای بازگشت ====================


@bot.callback_query_handler(func=lambda call: call.data == "botmgmt_back")
def botmgmt_back_handler(call):
    """بازگشت از هر زیرمنو به منوی اصلی مدیریت ربات"""
    admin_bot_management_handler(call)

# ==================== هندلرهای وضعیت ربات ====================


@bot.callback_query_handler(func=lambda call: call.data == "botmgmt_status")
def botmgmt_status_handler(call):
    """نمایش وضعیت فعلی ربات"""
    uid = call.message.chat.id

    bot_state = get_bot_state()
    status_icon = "🟢" if bot_state == "active" else "🔴"
    status_text = "فعال" if bot_state == "active" else "خاموش"

    try:
        bot.edit_message_text(
            f"📊 **وضعیت ربات**\n\n"
            f"{status_icon} **وضعیت فعلی:** {status_text}\n"
            f"👥 **تعداد ادمین‌ها:** {len(get_all_admins())}\n"
            f"💾 **تعداد بکاپ‌ها:** {len(get_backup_files())}",
            uid, call.message.message_id,
            reply_markup=admin_bot_management_menu(),
            parse_mode="Markdown"
        )
    except:
        bot.send_message(
            uid,
            f"📊 **وضعیت ربات**\n\n"
            f"{status_icon} **وضعیت فعلی:** {status_text}\n"
            f"👥 **تعداد ادمین‌ها:** {len(get_all_admins())}\n"
            f"💾 **تعداد بکاپ‌ها:** {len(get_backup_files())}",
            reply_markup=admin_bot_management_menu(),
            parse_mode="Markdown"
        )


@bot.callback_query_handler(func=lambda call: call.data == "botmgmt_start")
def botmgmt_start_handler(call):
    """روشن کردن ربات"""
    uid = call.message.chat.id

    if set_bot_status('active', uid):
        bot.answer_callback_query(call.id, "✅ ربات روشن شد")
        botmgmt_status_handler(call)
    else:
        bot.answer_callback_query(call.id, "❌ خطا در روشن کردن ربات")


@bot.callback_query_handler(func=lambda call: call.data == "botmgmt_stop")
def botmgmt_stop_handler(call):
    """خاموش کردن ربات"""
    uid = call.message.chat.id

    if set_bot_status('stopped', uid):
        bot.answer_callback_query(call.id, "✅ ربات خاموش شد")
        botmgmt_status_handler(call)
    else:
        bot.answer_callback_query(call.id, "❌ خطا در خاموش کردن ربات")

# ==================== هندلر پیام به ادمین‌ها ====================


@bot.callback_query_handler(func=lambda call: call.data == "botmgmt_message_admins")
def botmgmt_message_admins_handler(call):
    """شروع فرآیند ارسال پیام به ادمین‌ها"""
    uid = call.message.chat.id

    user_state[uid] = "waiting_admin_message"

    try:
        bot.edit_message_text(
            "📩 **ارسال پیام به ادمین‌ها**\n\n"
            "لطفا پیام خود را ارسال کنید:\n"
            "• متن ساده\n"
            "• عکس\n"
            "• ویدیو\n"
            "• فایل\n"
            "• یا هرکدام با کپشن",
            uid, call.message.message_id
        )
    except:
        bot.send_message(
            uid,
            "📩 **ارسال پیام به ادمین‌ها**\n\n"
            "لطفا پیام خود را ارسال کنید:\n"
            "• متن ساده\n"
            "• عکس\n"
            "• ویدیو\n"
            "• فایل\n"
            "• یا هرکدام با کپشن"
        )


# ==================== راه‌اندازی دیتابیس‌های مدیریت ====================

def setup_all_admin_databases():
    """راه‌اندازی تمام دیتابیس‌های مورد نیاز برای مدیریت"""
    print("🔄 راه‌اندازی دیتابیس‌های مدیریت...")

    # دیتابیس مدیریت ربات
    try:
        conn = sqlite3.connect("bot_management.db", check_same_thread=False)
        cur = conn.cursor()

        # وضعیت ربات
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bot_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT DEFAULT 'active',
            changed_by INTEGER,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # تنظیمات ربات
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bot_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT NOT NULL,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # تاریخچه بکاپ
        cur.execute("""
        CREATE TABLE IF NOT EXISTS backup_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            backup_name TEXT NOT NULL,
            files TEXT,
            file_size INTEGER,
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # تنظیمات اولیه
        cur.execute(
            "INSERT OR IGNORE INTO bot_status (status, changed_by) VALUES ('active', 0)")
        cur.execute(
            "INSERT OR IGNORE INTO bot_settings (setting_key, setting_value, description) VALUES ('bot_state', 'active', 'وضعیت ربات')")

        conn.commit()
        conn.close()
        print("✅ دیتابیس مدیریت ربات ایجاد شد")
    except Exception as e:
        print(f"❌ خطا در ایجاد دیتابیس مدیریت ربات: {e}")

    # دیتابیس مدیریت ادمین‌ها
    try:
        conn = sqlite3.connect("admin_management.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            full_name TEXT,
            permissions TEXT DEFAULT 'all',
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # ادمین پیشفرض
        cur.execute("INSERT OR IGNORE INTO admins (user_id, username, permissions, created_by) VALUES (?, ?, ?, ?)",
                    (8000307737, "Developer", "all", 0))

        conn.commit()
        conn.close()
        print("✅ دیتابیس مدیریت ادمین‌ها ایجاد شد")
    except Exception as e:
        print(f"❌ خطا در ایجاد دیتابیس ادمین‌ها: {e}")

    # دیتابیس پیام همگانی
    try:
        setup_broadcast_db()
        print("✅ دیتابیس پیام همگانی ایجاد شد")
    except Exception as e:
        print(f"❌ خطا در ایجاد دیتابیس پیام همگانی: {e}")

# ==================== توابع کمکی با مدیریت خطا ====================


def get_bot_state():
    """دریافت وضعیت ربات با مدیریت خطا"""
    try:
        conn = sqlite3.connect("bot_management.db", check_same_thread=False)
        cur = conn.cursor()

        # بررسی وجود جدول
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='bot_status'")
        if not cur.fetchone():
            conn.close()
            return 'active'

        cur.execute("SELECT status FROM bot_status ORDER BY id DESC LIMIT 1")
        result = cur.fetchone()
        conn.close()

        return result[0] if result else 'active'
    except:
        return 'active'


def set_bot_state(new_status, admin_id):
    """تغییر وضعیت ربات با مدیریت خطا"""
    try:
        conn = sqlite3.connect("bot_management.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("INSERT INTO bot_status (status, changed_by) VALUES (?, ?)",
                    (new_status, admin_id))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ خطا در تغییر وضعیت ربات: {e}")
        return False


def is_admin(user_id):
    """بررسی ادمین بودن با مدیریت خطا"""
    try:
        conn = sqlite3.connect("admin_management.db", check_same_thread=False)
        cur = conn.cursor()

        # بررسی وجود جدول
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='admins'")
        if not cur.fetchone():
            conn.close()
            return user_id == 8000307737  # فقط ادمین پیشفرض

        cur.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
        result = cur.fetchone()
        conn.close()

        return result is not None
    except:
        return user_id == 8000307737  # فقط ادمین پیشفرض در صورت خطا


def get_all_admins():
    """دریافت لیست ادمین‌ها با مدیریت خطا"""
    try:
        conn = sqlite3.connect("admin_management.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("SELECT user_id FROM admins")
        result = cur.fetchall()
        conn.close()

        return [row[0] for row in result] if result else [8000307737]
    except:
        return [8000307737]


def get_backup_files():
    """دریافت لیست بکاپ‌ها با مدیریت خطا"""
    try:
        import os
        if not os.path.exists('backups'):
            os.makedirs('backups')
        return [f for f in os.listdir('backups') if os.path.isdir(f"backups/{f}")]
    except:
        return []

# ==================== فراخوانی راه‌اندازی در شروع ====================


# در ابتدای کد، بعد از تعریف توابع، این خط رو اضافه کن:
print("🔄 راه‌اندازی دیتابیس‌های مدیریت...")
setup_all_admin_databases()


@bot.callback_query_handler(func=lambda call: call.data == "users_stats")
def users_stats_handler(call):
    """نمایش آمار دقیق کاربران"""
    uid = call.message.chat.id

    try:
        # آمار پایه کاربران
        total_users = safe_execute_db("SELECT COUNT(*) FROM users")[0][0] or 0
        connected_users = safe_execute_db(
            "SELECT COUNT(*) FROM users WHERE connection_status = 'connected'")[0][0] or 0
        boys = safe_execute_db(
            "SELECT COUNT(*) FROM users WHERE gender = 'مرد'")[0][0] or 0
        girls = safe_execute_db(
            "SELECT COUNT(*) FROM users WHERE gender = 'زن'")[0][0] or 0
        single_users = total_users - connected_users

        # آمار دقیق حالت خلقی
        mood_stats = get_detailed_mood_stats()

        # آمار کتاب‌نویسی
        book_stats = get_detailed_book_stats()

        text = f"""
📊 **آمار دقیق کاربران**

👥 **کاربران:**
• کل کاربران: {total_users}
• متصل: {connected_users} ({get_percentage(connected_users, total_users)})
• سینگل: {single_users} ({get_percentage(single_users, total_users)})
• پسران: {boys} ({get_percentage(boys, total_users)})
• دختران: {girls} ({get_percentage(girls, total_users)})

🌙 **آمار حالت خلقی:**
{mood_stats}

📚 **آمار کتاب‌نویسی:**
{book_stats}
"""

        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton(
            "🔄 بروزرسانی", callback_data="users_stats"))
        markup.row(InlineKeyboardButton(
            "📈 جزئیات بیشتر", callback_data="detailed_stats"))
        markup.row(InlineKeyboardButton(
            "🔙 بازگشت", callback_data="admin_users_main"))

        try:
            bot.edit_message_text(text, uid, call.message.message_id,
                                  reply_markup=markup, parse_mode="Markdown")
        except:
            bot.send_message(uid, text, reply_markup=markup,
                             parse_mode="Markdown")

    except Exception as e:
        print(f"خطا در آمار کاربران: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در دریافت آمار")


def get_detailed_mood_stats():
    """آمار دقیق حالت خلقی"""
    try:
        # آمار کلی حالت خلقی
        total_mood_entries = safe_execute_db(
            "SELECT COUNT(*) FROM mood_entries", db_type="mood_tracking")[0][0] or 0
        unique_users_with_mood = safe_execute_db(
            "SELECT COUNT(DISTINCT user_id) FROM mood_entries", db_type="mood_tracking")[0][0] or 0

        # آمار حالت خلقی پسران
        boys_mood = safe_execute_db("""
            SELECT COUNT(*) FROM mood_entries me 
            JOIN users u ON me.user_id = u.user_id 
            WHERE u.gender = 'مرد'
        """, db_type="mood_tracking")[0][0] or 0

        # آمار حالت خلقی دختران
        girls_mood = safe_execute_db("""
            SELECT COUNT(*) FROM mood_entries me 
            JOIN users u ON me.user_id = u.user_id 
            WHERE u.gender = 'زن'
        """, db_type="mood_tracking")[0][0] or 0

        # پرکاربردترین حالت‌های خلقی
        top_moods = safe_execute_db("""
            SELECT mood_type, COUNT(*) as count 
            FROM mood_entries 
            GROUP BY mood_type 
            ORDER BY count DESC 
            LIMIT 3
        """, db_type="mood_tracking")

        mood_text = ""
        if top_moods:
            mood_text = "• پرکاربردترین حالت‌ها: "
            mood_text += ", ".join(
                [f"{get_mood_persian(mood)} ({count})" for mood, count in top_moods])

        return f"""• کل ثبت‌های خلقی: {total_mood_entries}
• کاربران دارای ثبت خلقی: {unique_users_with_mood}
• ثبت پسران: {boys_mood} ({get_percentage(boys_mood, total_mood_entries)})
• ثبت دختران: {girls_mood} ({get_percentage(girls_mood, total_mood_entries)})
{mood_text}"""

    except Exception as e:
        print(f"خطا در آمار خلقی: {e}")
        return "• خطا در دریافت آمار خلقی"


def get_detailed_book_stats():
    """آمار دقیق کتاب‌نویسی"""
    try:
        # تعداد کل کتاب‌ها
        total_books = safe_execute_db(
            "SELECT COUNT(*) FROM user_books", db_type="books")[0][0] or 0

        # کتاب‌های شروع شده توسط پسران
        books_by_boys = safe_execute_db("""
            SELECT COUNT(*) FROM user_books ub 
            JOIN users u ON ub.user_id = u.user_id 
            WHERE u.gender = 'مرد'
        """, db_type="books")[0][0] or 0

        # کتاب‌های شروع شده توسط دختران
        books_by_girls = safe_execute_db("""
            SELECT COUNT(*) FROM user_books ub 
            JOIN users u ON ub.user_id = u.user_id 
            WHERE u.gender = 'زن'
        """, db_type="books")[0][0] or 0

        # آمار صفحات
        total_pages = safe_execute_db(
            "SELECT COUNT(*) FROM book_pages", db_type="books")[0][0] or 0

        # صفحات نوشته شده توسط پسران
        pages_by_boys = safe_execute_db("""
            SELECT COUNT(*) FROM book_pages bp 
            JOIN users u ON bp.author_id = u.user_id 
            WHERE u.gender = 'مرد'
        """, db_type="books")[0][0] or 0

        # صفحات نوشته شده توسط دختران
        pages_by_girls = safe_execute_db("""
            SELECT COUNT(*) FROM book_pages bp 
            JOIN users u ON bp.author_id = u.user_id 
            WHERE u.gender = 'زن'
        """, db_type="books")[0][0] or 0

        # میانگین صفحات per کتاب
        avg_pages_per_book = total_pages / total_books if total_books > 0 else 0

        return f"""• کل کتاب‌ها: {total_books}
• شروع شده توسط پسران: {books_by_boys} ({get_percentage(books_by_boys, total_books)})
• شروع شده توسط دختران: {books_by_girls} ({get_percentage(books_by_girls, total_books)})
• کل صفحات: {total_pages}
• صفحات پسران: {pages_by_boys} ({get_percentage(pages_by_boys, total_pages)})
• صفحات دختران: {pages_by_girls} ({get_percentage(pages_by_girls, total_pages)})
• میانگین صفحات per کتاب: {avg_pages_per_book:.1f}"""

    except Exception as e:
        print(f"خطا در آمار کتاب‌ها: {e}")
        return "• خطا در دریافت آمار کتاب‌ها"


def get_percentage(part, total):
    """محاسبه درصد"""
    if total == 0:
        return "0%"
    return f"{(part/total*100):.1f}%"


def get_mood_persian(mood_key):
    """تبدیل کلید حالت خلقی به فارسی"""
    mood_map = {
        'happy': 'شاد',
        'romantic': 'عاشقانه',
        'calm': 'آرام',
        'sad': 'غمگین',
        'stressed': 'استرس',
        'energetic': 'پرانرژی',
        'focused': 'متمرکز',
        'thoughtful': 'فکور',
        'playful': 'شوخ',
        'sensitive': 'حساس',
        'determined': 'مصمم',
        'tired': 'خسته'
    }
    return mood_map.get(mood_key, mood_key)

# هندلر برای جزئیات بیشتر


@bot.callback_query_handler(func=lambda call: call.data == "detailed_stats")
def detailed_stats_handler(call):
    """آمار جزئی‌تر"""
    uid = call.message.chat.id

    try:
        # آمار پیشرفته کتاب‌نویسی
        book_details = get_advanced_book_stats()

        # آمار پیشرفته حالت خلقی
        mood_details = get_advanced_mood_stats()

        text = f"""
📈 **آمار جزئی‌تر**

📚 **جزئیات کتاب‌نویسی:**
{book_details}

🌙 **جزئیات حالت خلقی:**
{mood_details}
"""

        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton(
            "📊 آمار کلی", callback_data="users_stats"))
        markup.row(InlineKeyboardButton(
            "🔙 بازگشت", callback_data="admin_users_main"))

        try:
            bot.edit_message_text(text, uid, call.message.message_id,
                                  reply_markup=markup, parse_mode="Markdown")
        except:
            bot.send_message(uid, text, reply_markup=markup,
                             parse_mode="Markdown")

    except Exception as e:
        bot.answer_callback_query(call.id, "❌ خطا در دریافت آمار جزئی")


def get_advanced_book_stats():
    """آمار پیشرفته کتاب‌نویسی"""
    try:
        # کتاب‌های فعال (با بیش از 5 صفحه)
        active_books = safe_execute_db("""
            SELECT COUNT(DISTINCT book_id) FROM book_pages 
            GROUP BY book_id 
            HAVING COUNT(*) > 5
        """, db_type="books")[0][0] or 0 if safe_execute_db("SELECT COUNT(*) FROM book_pages", db_type="books") else 0

        # کاربران فعال در کتاب‌نویسی
        active_writers = safe_execute_db(
            "SELECT COUNT(DISTINCT author_id) FROM book_pages", db_type="books")[0][0] or 0

        # طولانی‌ترین کتاب
        longest_book = safe_execute_db("""
            SELECT book_id, COUNT(*) as page_count 
            FROM book_pages 
            GROUP BY book_id 
            ORDER BY page_count DESC 
            LIMIT 1
        """, db_type="books")

        longest_text = ""
        if longest_book:
            book_id, page_count = longest_book[0]
            longest_text = f"• طولانی‌ترین کتاب: {page_count} صفحه"

        return f"""• کتاب‌های فعال: {active_books}
• نویسندگان فعال: {active_writers}
{longest_text}"""

    except Exception as e:
        return "• خطا در دریافت آمار پیشرفته"


def get_advanced_mood_stats():
    """آمار پیشرفته حالت خلقی"""
    try:
        # آخرین ثبت‌های خلقی (24 ساعت گذشته)
        recent_moods = safe_execute_db("""
            SELECT COUNT(*) FROM mood_entries 
            WHERE created_at > datetime('now', '-1 day')
        """, db_type="mood_tracking")[0][0] or 0

        # کاربران فعال در ثبت خلقی
        active_mood_users = safe_execute_db("""
            SELECT COUNT(DISTINCT user_id) FROM mood_entries 
            WHERE created_at > datetime('now', '-7 days')
        """, db_type="mood_tracking")[0][0] or 0

        return f"""• ثبت‌های 24h گذشته: {recent_moods}
• کاربران فعال (7 روز): {active_mood_users}"""

    except Exception as e:
        return "• خطا در دریافت آمار پیشرفته"


# ==================== جستجوی کاربر با جزئیات کامل ====================

@bot.callback_query_handler(func=lambda call: call.data == "search_user")
def search_user_handler(call):
    """شروع جستجوی کاربر"""
    uid = call.message.chat.id

    user_state[uid] = "admin_search_user"

    try:
        bot.edit_message_text(
            "🔍 **جستجوی کاربر**\n\n"
            "لطفا آیدی عددی کاربر رو وارد کنید:",
            uid, call.message.message_id
        )
    except:
        bot.send_message(
            uid, "🔍 **جستجوی کاربر**\n\nلطفا آیدی عددی کاربر رو وارد کنید:")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "admin_search_user")
def search_user_result_handler(message):
    """نتیجه جستجوی کاربر"""
    uid = message.chat.id

    try:
        user_id = int(message.text.strip())
        show_user_management_panel(uid, user_id, message.message_id)

    except ValueError:
        bot.send_message(uid, "❌ آیدی باید عدد باشد!")
    except Exception as e:
        bot.send_message(uid, "❌ خطا در جستجوی کاربر")

# ==================== لیست کاربران با جزئیات کامل ====================


@bot.callback_query_handler(func=lambda call: call.data == "users_list_all")
def users_list_all_handler(call):
    """نمایش لیست کاربران با صفحه‌بندی"""
    uid = call.message.chat.id
    page = 1

    show_users_list(uid, page, call.message.message_id)


def show_users_list(uid, page=1, message_id=None):
    """نمایش لیست کاربران با صفحه‌بندی"""
    try:
        offset = (page - 1) * 10

        # دریافت کاربران با صفحه‌بندی
        users = safe_execute_db("""
            SELECT user_id, name, gender, connection_status, created_at 
            FROM users 
            ORDER BY created_at DESC 
            LIMIT 10 OFFSET ?
        """, (offset,))

        if not users:
            text = "📭 هیچ کاربری پیدا نشد!"
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton(
                "🔙 بازگشت", callback_data="admin_users_main"))

            if message_id:
                bot.edit_message_text(
                    text, uid, message_id, reply_markup=markup)
            else:
                bot.send_message(uid, text, reply_markup=markup)
            return

        text = f"📋 **لیست کاربران** - صفحه {page}\n\n"

        for user_id, name, gender, connection_status, created_at in users:
            status_icon = "💞" if connection_status == "connected" else "👤"
            gender_icon = "👨" if gender == "مرد" else "👩"
            created = datetime.fromisoformat(created_at).strftime("%Y/%m/%d")

            text += f"{status_icon} {gender_icon} **{name}**\n"
            text += f"🆔 `{user_id}` | 📅 {created}\n"
            text += f"🔗 وضعیت: {'متصل' if connection_status == 'connected' else 'سینگل'}\n\n"

        markup = InlineKeyboardMarkup()

        # دکمه‌های صفحه‌بندی
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(
                "⬅️ صفحه قبل", callback_data=f"users_page_{page-1}"))

        nav_buttons.append(InlineKeyboardButton(
            f"{page}", callback_data=f"users_page_{page}"))

        # بررسی وجود صفحه بعد
        next_users = safe_execute_db(
            "SELECT user_id FROM users ORDER BY created_at DESC LIMIT 1 OFFSET ?", (offset + 10,))
        if next_users:
            nav_buttons.append(InlineKeyboardButton(
                "صفحه بعد ➡️", callback_data=f"users_page_{page+1}"))

        if nav_buttons:
            markup.row(*nav_buttons)

        markup.row(InlineKeyboardButton(
            "🔍 جستجوی کاربر", callback_data="search_user"))
        markup.row(InlineKeyboardButton(
            "🔙 بازگشت", callback_data="admin_users_main"))

        if message_id:
            try:
                bot.edit_message_text(
                    text, uid, message_id, reply_markup=markup, parse_mode="Markdown")
            except:
                bot.send_message(uid, text, reply_markup=markup,
                                 parse_mode="Markdown")
        else:
            bot.send_message(uid, text, reply_markup=markup,
                             parse_mode="Markdown")

    except Exception as e:
        print(f"خطا در نمایش لیست کاربران: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در نمایش لیست")


@bot.callback_query_handler(func=lambda call: call.data.startswith("users_page_"))
def users_page_handler(call):
    """تغییر صفحه لیست کاربران"""
    uid = call.message.chat.id
    page = int(call.data.split("_")[2])

    show_users_list(uid, page, call.message.message_id)

# ==================== پنل مدیریت کاربر ====================


def show_user_management_panel(admin_id, target_user_id, message_id=None):
    """نمایش پنل مدیریت کاربر"""
    try:
        # دریافت اطلاعات کاربر
        user_info = safe_execute_db("""
            SELECT name, gender, birthdate, partner_name, partner_id, connection_status, created_at 
            FROM users WHERE user_id = ?
        """, (target_user_id,))

        if not user_info:
            if message_id:
                bot.edit_message_text(
                    "❌ کاربر پیدا نشد!", admin_id, message_id)
            else:
                bot.send_message(admin_id, "❌ کاربر پیدا نشد!")
            return

        name, gender, birthdate, partner_name, partner_id, connection_status, created_at = user_info[
            0]

        # آمار کاربر
        mood_stats = get_user_mood_stats(target_user_id)
        book_stats = get_user_book_stats(target_user_id)
        is_blocked = check_if_blocked(admin_id, target_user_id)

        # ساخت متن اطلاعات کاربر
        text = f"👤 **مدیریت کاربر**\n\n"
        text += f"**نام:** {name}\n"
        text += f"**جنسیت:** {gender}\n"
        text += f"**آیدی:** `{target_user_id}`\n"
        text += f"**وضعیت ارتباط:** {'💞 متصل' if connection_status == 'connected' else '👤 سینگل'}\n"

        if connection_status == "connected" and partner_name:
            text += f"**پارتنر:** {partner_name} (`{partner_id}`)\n"

        if birthdate:
            birth_jdate = jdatetime.date.fromgregorian(
                date=datetime.strptime(birthdate, "%Y-%m-%d").date())
            text += f"**تولد:** {birth_jdate.year}/{birth_jdate.month:02d}/{birth_jdate.day:02d}\n"

        created = datetime.fromisoformat(created_at).strftime("%Y/%m/%d")
        text += f"**عضویت از:** {created}\n\n"

        text += f"🌙 **آمار خلقی:**\n{mood_stats}\n\n"
        text += f"📚 **آمار کتاب‌نویسی:**\n{book_stats}"

        # ایجاد منوی مدیریت
        markup = InlineKeyboardMarkup()

        # ردیف 1: بلاک/آنبلاک
        if is_blocked:
            markup.row(InlineKeyboardButton("✅ آنبلاک کاربر",
                       callback_data=f"admin_unblock_{target_user_id}"))
        else:
            markup.row(InlineKeyboardButton("🚫 بلاک کاربر",
                       callback_data=f"admin_block_{target_user_id}"))

        # ردیف 2: مدیریت ارتباط
        if connection_status == "connected":
            markup.row(InlineKeyboardButton("🔗 قطع ارتباط",
                       callback_data=f"admin_disconnect_{target_user_id}"))
        else:
            markup.row(InlineKeyboardButton("💞 متصل کردن",
                       callback_data=f"admin_connect_{target_user_id}"))

        # ردیف 3: پیام و حالت خلقی
        markup.row(
            InlineKeyboardButton(
                "📝 ارسال پیام", callback_data=f"admin_message_{target_user_id}"),
            InlineKeyboardButton(
                "🌙 تنظیم حالت خلقی", callback_data=f"admin_set_mood_{target_user_id}")
        )

        # ردیف 4: بازگشت
        markup.row(InlineKeyboardButton(
            "🔙 بازگشت به لیست", callback_data="users_list_all"))

        if message_id:
            try:
                bot.edit_message_text(
                    text, admin_id, message_id, reply_markup=markup, parse_mode="Markdown")
            except:
                bot.send_message(
                    admin_id, text, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(
                admin_id, text, reply_markup=markup, parse_mode="Markdown")

    except Exception as e:
        print(f"خطا در نمایش پنل کاربر: {e}")
        bot.send_message(admin_id, "❌ خطا در نمایش اطلاعات کاربر")

# ==================== آمار کاربر ====================


def get_user_mood_stats(user_id):
    """آمار حالت خلقی کاربر"""
    try:
        # تعداد ثبت‌های خلقی
        mood_count = safe_execute_db("SELECT COUNT(*) FROM mood_entries WHERE user_id = ?",
                                     (user_id,), "mood_tracking")[0][0] or 0

        # آخرین حالت خلقی
        last_mood = safe_execute_db("""
            SELECT mood_type, created_at FROM mood_entries 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 1
        """, (user_id,), "mood_tracking")

        mood_text = f"• تعداد ثبت‌ها: {mood_count}"

        if last_mood:
            mood_type, created_at = last_mood[0]
            mood_persian = get_mood_persian(mood_type)
            created = datetime.fromisoformat(created_at).strftime("%m/%d")
            mood_text += f"\n• آخرین حالت: {mood_persian} ({created})"

        return mood_text

    except:
        return "• خطا در دریافت آمار خلقی"


def get_user_book_stats(user_id):
    """آمار کتاب‌نویسی کاربر"""
    try:
        # تعداد کتاب‌ها
        books_count = safe_execute_db("SELECT COUNT(*) FROM user_books WHERE user_id = ? OR partner_id = ?",
                                      (user_id, user_id), "books")[0][0] or 0

        # تعداد صفحات نوشته شده
        pages_count = safe_execute_db("SELECT COUNT(*) FROM book_pages WHERE author_id = ?",
                                      (user_id,), "books")[0][0] or 0

        return f"• کتاب‌ها: {books_count}\n• صفحات نوشته: {pages_count}"

    except:
        return "• خطا در دریافت آمار کتاب"

# ==================== هندلرهای مدیریت کاربر ====================


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_block_"))
def admin_block_user_handler(call):
    """بلاک کردن کاربر توسط ادمین"""
    uid = call.message.chat.id
    target_user_id = int(call.data.split("_")[2])

    try:
        # بلاک کردن
        conn = sqlite3.connect("secret_messages.db", check_same_thread=False)
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO blocked_users (user_id, blocked_user_id) VALUES (?, ?)",
                    (uid, target_user_id))
        conn.commit()
        conn.close()

        bot.answer_callback_query(call.id, "✅ کاربر بلاک شد")
        show_user_management_panel(
            uid, target_user_id, call.message.message_id)

    except Exception as e:
        bot.answer_callback_query(call.id, "❌ خطا در بلاک کردن")


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_unblock_"))
def admin_unblock_user_handler(call):
    """آنبلاک کردن کاربر توسط ادمین"""
    uid = call.message.chat.id
    target_user_id = int(call.data.split("_")[2])

    try:
        # آنبلاک کردن
        conn = sqlite3.connect("secret_messages.db", check_same_thread=False)
        cur = conn.cursor()
        cur.execute("DELETE FROM blocked_users WHERE user_id = ? AND blocked_user_id = ?",
                    (uid, target_user_id))
        conn.commit()
        conn.close()

        bot.answer_callback_query(call.id, "✅ کاربر آنبلاک شد")
        show_user_management_panel(
            uid, target_user_id, call.message.message_id)

    except Exception as e:
        bot.answer_callback_query(call.id, "❌ خطا در آنبلاک کردن")


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_connect_"))
def admin_connect_user_handler(call):
    """اتصال کاربر توسط ادمین"""
    uid = call.message.chat.id
    target_user_id = int(call.data.split("_")[2])

    user_state[uid] = f"admin_connect_{target_user_id}"

    try:
        bot.edit_message_text(
            f"💞 **اتصال کاربر**\n\n"
            f"لطفا آیدی عددی کاربری که می‌خواهید به کاربر {target_user_id} متصل شود را وارد کنید:",
            uid, call.message.message_id
        )
    except:
        bot.send_message(
            uid,
            f"💞 **اتصال کاربر**\n\n"
            f"لطفا آیدی عددی کاربری که می‌خواهید به کاربر {target_user_id} متصل شود را وارد کنید:"
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_disconnect_"))
def admin_disconnect_user_handler(call):
    """قطع ارتباط کاربر توسط ادمین"""
    uid = call.message.chat.id
    target_user_id = int(call.data.split("_")[2])

    try:
        # قطع ارتباط
        safe_execute_db("UPDATE users SET connection_status = 'single', partner_id = NULL WHERE user_id = ?",
                        (target_user_id,))

        # اطلاع به کاربر
        try:
            bot.send_message(target_user_id, "🔗 ارتباط شما توسط ادمین قطع شد.")
        except:
            pass

        bot.answer_callback_query(call.id, "✅ ارتباط قطع شد")
        show_user_management_panel(
            uid, target_user_id, call.message.message_id)

    except Exception as e:
        bot.answer_callback_query(call.id, "❌ خطا در قطع ارتباط")


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_message_"))
def admin_message_user_handler(call):
    """ارسال پیام به کاربر"""
    uid = call.message.chat.id
    target_user_id = int(call.data.split("_")[2])

    user_state[uid] = f"admin_message_{target_user_id}"

    try:
        bot.edit_message_text(
            f"📝 **ارسال پیام به کاربر**\n\n"
            f"لطفا پیام خود را ارسال کنید:\n"
            f"• متن ساده\n• عکس\n• ویدیو\n• فایل\n"
            f"• یا هرکدام با کپشن",
            uid, call.message.message_id
        )
    except:
        bot.send_message(
            uid,
            f"📝 **ارسال پیام به کاربر**\n\n"
            f"لطفا پیام خود را ارسال کنید:\n"
            f"• متن ساده\n• عکس\n• ویدیو\n• فایل\n"
            f"• یا هرکدام با کپشن"
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_set_mood_"))
def admin_set_mood_user_handler(call):
    """تنظیم حالت خلقی برای کاربر"""
    uid = call.message.chat.id
    target_user_id = int(call.data.split("_")[3])

    # نمایش منوی حالت‌های خلقی
    markup = InlineKeyboardMarkup()
    moods = list(MOOD_CATEGORIES.items())

    for i in range(0, len(moods), 3):
        row = []
        for j in range(3):
            if i + j < len(moods):
                mood_key, mood_data = moods[i + j]
                row.append(InlineKeyboardButton(
                    f"{mood_data['emoji']} {mood_data['name']}",
                    callback_data=f"admin_mood_{mood_key}_{target_user_id}"
                ))
        markup.row(*row)

    markup.row(InlineKeyboardButton(
        "🔙 بازگشت", callback_data=f"admin_back_to_user_{target_user_id}"))

    try:
        bot.edit_message_text(
            "🌙 **تنظیم حالت خلقی برای کاربر**\n\n"
            "لطفا حالت خلقی مورد نظر را انتخاب کنید:",
            uid, call.message.message_id,
            reply_markup=markup
        )
    except:
        bot.send_message(
            uid,
            "🌙 **تنظیم حالت خلقی برای کاربر**\n\n"
            "لطفا حالت خلقی مورد نظر را انتخاب کنید:",
            reply_markup=markup
        )

# ==================== هندلرهای پیام ادمین ====================


@bot.message_handler(func=lambda m: user_state.get(m.chat.id, "").startswith("admin_connect_"))
def admin_connect_handler(message):
    """اتصال دو کاربر توسط ادمین"""
    uid = message.chat.id
    state = user_state[uid]
    target_user_id = int(state.split("_")[2])

    try:
        partner_id = int(message.text.strip())

        # اتصال کاربران
        safe_execute_db("UPDATE users SET connection_status = 'connected', partner_id = ? WHERE user_id = ?",
                        (partner_id, target_user_id))
        safe_execute_db("UPDATE users SET connection_status = 'connected', partner_id = ? WHERE user_id = ?",
                        (target_user_id, partner_id))

        # اطلاع به کاربران
        try:
            bot.send_message(
                target_user_id, f"🔗 شما توسط ادمین به کاربر {partner_id} متصل شدید.")
            bot.send_message(
                partner_id, f"🔗 شما توسط ادمین به کاربر {target_user_id} متصل شدید.")
        except:
            pass

        bot.send_message(uid, "✅ کاربران با موفقیت متصل شدند")
        user_state.pop(uid, None)
        show_user_management_panel(uid, target_user_id)

    except ValueError:
        bot.send_message(uid, "❌ آیدی باید عدد باشد!")
    except Exception as e:
        bot.send_message(uid, "❌ خطا در اتصال کاربران")


@bot.message_handler(func=lambda m: user_state.get(m.chat.id, "").startswith("admin_message_"))
def admin_message_send_handler(message):
    """ارسال پیام ادمین به کاربر"""
    uid = message.chat.id
    state = user_state[uid]
    target_user_id = int(state.split("_")[2])

    try:
        # ارسال پیام بر اساس نوع محتوا
        if message.content_type == 'text':
            bot.send_message(
                target_user_id, f"📨 پیام از ادمین:\n\n{message.text}")
        elif message.content_type == 'photo':
            bot.send_photo(target_user_id, message.photo[-1].file_id,
                           caption=f"📨 از ادمین: {message.caption}" if message.caption else "📨 از ادمین")
        elif message.content_type == 'video':
            bot.send_video(target_user_id, message.video.file_id,
                           caption=f"📨 از ادمین: {message.caption}" if message.caption else "📨 از ادمین")
        elif message.content_type == 'document':
            bot.send_document(target_user_id, message.document.file_id,
                              caption=f"📨 از ادمین: {message.caption}" if message.caption else "📨 از ادمین")

        bot.send_message(uid, "✅ پیام با موفقیت ارسال شد")
        user_state.pop(uid, None)
        show_user_management_panel(uid, target_user_id)

    except Exception as e:
        bot.send_message(uid, "❌ خطا در ارسال پیام")

# ==================== هندلر تنظیم حالت خلقی ====================


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_mood_"))
def admin_set_mood_final_handler(call):
    """تنظیم نهایی حالت خلقی توسط ادمین"""
    uid = call.message.chat.id
    parts = call.data.split("_")
    mood_key = parts[2]
    target_user_id = int(parts[3])

    try:
        # ذخیره حالت خلقی
        conn = sqlite3.connect("mood_tracking.db", check_same_thread=False)
        cur = conn.cursor()
        cur.execute("INSERT INTO mood_entries (user_id, mood_type, custom_message) VALUES (?, ?, ?)",
                    (target_user_id, mood_key, "تنظیم شده توسط ادمین"))
        conn.commit()
        conn.close()

        # اطلاع به کاربر
        try:
            mood_data = MOOD_CATEGORIES[mood_key]
            bot.send_message(
                target_user_id, f"🌙 ادمین حالت خلقی شما را به '{mood_data['name']}' تغییر داد.")
        except:
            pass

        bot.answer_callback_query(call.id, "✅ حالت خلقی تنظیم شد")
        show_user_management_panel(
            uid, target_user_id, call.message.message_id)

    except Exception as e:
        bot.answer_callback_query(call.id, "❌ خطا در تنظیم حالت خلقی")

# ==================== هندلر بازگشت ====================


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_back_to_user_"))
def admin_back_to_user_handler(call):
    """بازگشت به پنل کاربر"""
    uid = call.message.chat.id
    target_user_id = int(call.data.split("_")[3])

    show_user_management_panel(uid, target_user_id, call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data == "server_stats")
def server_stats_handler(call):
    uid = call.message.chat.id

    if not is_superadmin(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی ممنوع!")
        return

    try:
        db_files = [
            "relation_agent.db",
            "notifications.db",
            "secret_messages.db",
            "mood_tracking.db",
            "books.db",
            "special_messages.db"
        ]

        db_stats = []
        total_db_size = 0

        for db_file in db_files:
            if os.path.exists(db_file):
                size = os.path.getsize(db_file)
                total_db_size += size

                conn = sqlite3.connect(db_file)
                cur = conn.cursor()

                table_counts = {}
                cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")
                tables = cur.fetchall()

                for table in tables:
                    table_name = table[0]
                    try:
                        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                        count = cur.fetchone()[0]
                        table_counts[table_name] = count
                    except:
                        table_counts[table_name] = 0

                conn.close()

                db_stats.append({
                    'name': db_file,
                    'size': size,
                    'tables': table_counts
                })

        system_info = get_system_info()

        text = "🖥️ **آمار سرور و دیتابیس**\n\n"
        text += f"💾 **حجم کل دیتابیس‌ها:** {format_size(total_db_size)}\n\n"

        text += "📊 **جزئیات دیتابیس‌ها:**\n"
        for db in db_stats:
            text += f"\n📁 **{db['name']}**\n"
            text += f"📏 حجم: {format_size(db['size'])}\n"
            text += "📋 تعداد رکوردها:\n"
            for table, count in db['tables'].items():
                text += f"  • {table}: {count:,}\n"

        text += f"\n🖥️ **وضعیت سرور:**\n"
        text += f"⚙️ سیستم عامل: {system_info['os']}\n"
        text += f"🔢 معماری: {system_info['architecture']}\n"
        text += f"⏰ آپ‌تایم: {system_info['uptime']}\n"
        text += f"🧠 CPU: {system_info['cpu_usage']}%\n"
        text += f"💿 RAM: {system_info['ram_usage']}%\n"
        text += f"📊 حافظه RAM: {system_info['ram_details']}\n"
        text += f"💽 دیسک: {system_info['disk_usage']}\n"

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("💾 بکاپ گیری", callback_data="server_backup"),
            InlineKeyboardButton("📥 دریافت دیتابیس‌ها",
                                 callback_data="server_download")
        )
        markup.row(InlineKeyboardButton(
            "🔄 بروزرسانی آمار", callback_data="server_stats"))
        markup.row(InlineKeyboardButton(
            "🏠 منوی اصلی", callback_data="back_to_main"))

        try:
            bot.edit_message_text(
                text,
                uid, call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except:
            bot.send_message(uid, text, reply_markup=markup,
                             parse_mode="Markdown")

    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ خطا: {str(e)}")


def get_system_info():
    try:
        cpu_usage = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time

        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        return {
            'os': f"{platform.system()} {platform.release()}",
            'architecture': platform.architecture()[0],
            'uptime': uptime_str,
            'cpu_usage': round(cpu_usage, 1),
            'ram_usage': round(ram.percent, 1),
            'ram_details': f"{format_size(ram.used)} / {format_size(ram.total)}",
            'disk_usage': f"{round(disk.percent, 1)}% ({format_size(disk.used)} / {format_size(disk.total)})"
        }
    except:
        return {
            'os': 'نامشخص',
            'architecture': 'نامشخص',
            'uptime': 'نامشخص',
            'cpu_usage': 0,
            'ram_usage': 0,
            'ram_details': 'نامشخص',
            'disk_usage': 'نامشخص'
        }


def format_size(size_bytes):
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names)-1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.2f} {size_names[i]}"


def is_superadmin(user_id):
    try:
        superadmins = {
            "8000307737": {
                "level": "superadmin",
                "name": "Developer"
            }
        }
        return str(user_id) in superadmins
    except:
        return False


@bot.callback_query_handler(func=lambda call: call.data == "server_backup")
def server_backup_handler(call):
    uid = call.message.chat.id

    if not is_superadmin(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی ممنوع!")
        return

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"backup_{timestamp}"
        os.makedirs(backup_dir, exist_ok=True)

        db_files = [
            "relation_agent.db",
            "notifications.db",
            "secret_messages.db",
            "mood_tracking.db",
            "books.db",
            "special_messages.db"
        ]

        backed_up_files = []

        for db_file in db_files:
            if os.path.exists(db_file):
                shutil.copy2(db_file, os.path.join(backup_dir, db_file))
                backed_up_files.append(db_file)

        shutil.make_archive(backup_dir, 'zip', backup_dir)
        shutil.rmtree(backup_dir)

        with open(f"{backup_dir}.zip", "rb") as backup_file:
            bot.send_document(
                uid,
                backup_file,
                caption=f"💾 بکاپ کامل سرور\n🕒 تاریخ: {timestamp}\n📁 فایل‌های پشتیبان شده: {', '.join(backed_up_files)}"
            )

        os.remove(f"{backup_dir}.zip")
        bot.answer_callback_query(call.id, "✅ بکاپ با موفقیت ایجاد شد!")

    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ خطا در بکاپ: {str(e)}")


@bot.callback_query_handler(func=lambda call: call.data == "server_download")
def server_download_handler(call):
    uid = call.message.chat.id

    if not is_superadmin(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی ممنوع!")
        return

    try:
        db_files = [
            "relation_agent.db",
            "notifications.db",
            "secret_messages.db",
            "mood_tracking.db",
            "books.db",
            "special_messages.db"
        ]

        sent_count = 0
        for db_file in db_files:
            if os.path.exists(db_file):
                file_size = os.path.getsize(db_file)

                conn = sqlite3.connect(db_file)
                cur = conn.cursor()
                cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")
                tables = cur.fetchall()
                table_count = len(tables)
                conn.close()

                with open(db_file, "rb") as file:
                    bot.send_document(
                        uid,
                        file,
                        caption=f"📁 {db_file}\n📏 حجم: {format_size(file_size)}\n📋 تعداد جداول: {table_count}"
                    )
                sent_count += 1

        if sent_count == 0:
            bot.answer_callback_query(call.id, "❌ هیچ فایل دیتابیسی یافت نشد!")
        else:
            bot.answer_callback_query(
                call.id, f"✅ {sent_count} فایل ارسال شد!")

    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ خطا در ارسال فایل‌ها: {str(e)}")


# ?SEC CHAT
#!SEC CHAT


######## START#######
######## START#######
######## START#######
######## START#######
######## START#######
######## START#######
######## START#######
######## START#######
######## START#######
######## START#######
######## START#######
######## START#######
######## START#######
######## START#######
######## START#######
######## START#######


@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
def back_to_main_handler(call):

    uid = call.message.chat.id
    bot.edit_message_text("👋 به منوی اصلی خوش اومدی!",
                          uid, call.message.message_id, reply_markup=main_menu())


setup_special_messages_db()


def start_special_messages_monitor():

    try:
        monitor_thread = threading.Thread(
            target=special_messages_monitor, daemon=True)
        monitor_thread.start()
        print(Fore.YELLOW + "✅ Messages Monitoring Started")
    except Exception as e:
        print(Fore.RED + f"❌ ERROR IN MESSAGES MONITORING: {e}")


start_special_messages_monitor()


def setup_mood_database():

    try:
        conn = sqlite3.connect("mood_tracking.db", check_same_thread=False)
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS mood_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                mood_type TEXT NOT NULL,
                custom_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS mood_reminders (
                user_id INTEGER PRIMARY KEY,
                last_reminder_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        try:
            cur.execute(
                "SELECT last_reminder_time FROM mood_reminders LIMIT 1")
        except sqlite3.OperationalError:

            cur.execute(
                "ALTER TABLE mood_reminders ADD COLUMN last_reminder_time TIMESTAMP")

        conn.commit()
        conn.close()
        print(Fore.GREEN + "✅ Mood state database updated")
        return True

    except Exception as e:
        print(Fore.RED + f"❌ ERROR IN CREATING DATABASE MOOD: {e}")
        return False


setup_mood_database()


conn_users = sqlite3.connect(
    "relation_agent.db", check_same_thread=False, isolation_level=None)
cur_users = conn_users.cursor()
cur_users.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    gender TEXT,
    name TEXT,
    birthdate TEXT,
    region TEXT DEFAULT 'ایران',
    partner_name TEXT,
    partner_birthdate TEXT,
    partner_age INTEGER,
    partner_nick TEXT,
    relation_type TEXT,
    start_date TEXT,
    partner_id INTEGER,
    connection_status TEXT DEFAULT 'single',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn_users.commit()


def update_database_structure():
    try:

        cur_users.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cur_users.fetchall()]

        if 'partner_id' not in columns:
            cur_users.execute(
                "ALTER TABLE users ADD COLUMN partner_id INTEGER")
            print(Fore.GREEN + "✅ Column partner_id added")

        if 'connection_status' not in columns:
            cur_users.execute(
                "ALTER TABLE users ADD COLUMN connection_status TEXT DEFAULT 'single'")
            print(Fore.YELLOW + "✅ Column connection_status added to " +
                  Fore.CYAN + "single")

        conn_users.commit()
        print(Fore.YELLOW + "Database updated ✅")
    except Exception as e:
        print(Fore.RED + f"❌ ERROR IN UPDATING DATABASE {e}")


update_database_structure()

if __name__ == "__main__":
    print(Back.WHITE + Fore.LIGHTGREEN_EX + "🤖 Started ...")
    print(Fore.GREEN + "💾 Database Setup Done")
    print(Fore.LIGHTYELLOW_EX + "🔔")

    any()

    setup_special_messages_db()
    start_special_messages_monitor()

    notification_thread = threading.Thread(
        target=notification_loop, daemon=True)
    notification_thread.start()

    try:
        bot.infinity_polling()
    except Exception as e:
        print(Fore.RED + f"ERROR: {e}")
    finally:
        print(Back.YELLOW + Fore.BLACK + "🔴 Bot Has Been STOPED !!!")
