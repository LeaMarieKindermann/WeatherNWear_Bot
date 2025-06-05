import json
import os
import re
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from weather import get_weather
import random
import spacy

USER_INFORMATION_FILE = "user_information.json"

scheduler = BackgroundScheduler()
scheduler.start()

nlp_de = spacy.load("de_core_news_sm")
nlp_en = spacy.load("en_core_web_sm")

MOOD_MESSAGES = {
    "en": [
        "Don't stress yourself, everything is gonna work out 😊",
        "Take a deep breath. You've got this! 🌟",
        "New day, new chance 💪",
        "Trust the process. Everything will be okay 🧘"
    ],
    "de": [
        "Mach dir keinen Stress, alles wird gut 😊",
        "Tief durchatmen. Du schaffst das! 🌟",
        "Neuer Tag, neue Chance 💪",
        "Vertrau dem Prozess. Es wird alles gut 🧘"
    ]
}

def load_user_information():
    if os.path.exists(USER_INFORMATION_FILE):
        with open(USER_INFORMATION_FILE, "r") as f:
            return json.load(f)
    return {}

def save_user_information(info):
    with open(USER_INFORMATION_FILE, "w") as f:
        json.dump(info, f)

user_info = load_user_information()

def extract_routine_details(text, language):
    """
    Extracts city and time from the user's input text.
    """
    nlp = nlp_de if language == "de" else nlp_en
    doc = nlp(text)

    city = None
    time_match = re.search(r'(\d{1,2}):(\d{2})', text)

    for ent in doc.ents:
        if ent.label_ in ("LOC", "GPE"):
            city = ent.text
            break

    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
        return city, hour, minute

    return None, None, None


def generate_clothing_tip(weather_text, language):
    match = re.search(r'Ø\s*(-?\d+(?:[.,]\d+)?)\s*°C', weather_text)
    if not match:
        return {
            "de": "Check das Wetter vorsichtshalber nochmal!",
            "en": "Better double-check the weather just in case!"
        }.get(language, "Check the weather!")

    temp_str = match.group(1).replace(',', '.')
    try:
        temp = float(temp_str)
    except ValueError:
        return {
            "de": "Check das Wetter vorsichtshalber nochmal!",
            "en": "Better double-check the weather just in case!"
        }.get(language, "Check the weather!")

    # Rückgabe basierend auf Sprache und Temperatur
    if language == "de":
        if temp < 5:
            return "Zieh dich warm an – Mütze und Schal könnten helfen!"
        elif temp < 15:
            return "Eine wärmere Jacke oder ein Hoodie zum drüberziehen ist eine gute Idee."
        elif temp < 25:
            return "Leichte Kleidung reicht aus."
        else:
            return "Perfektes T-Shirt-Wetter!"
    else:  # default = English
        if temp < 5:
            return "Bundle up – a hat and scarf might help!"
        elif temp < 15:
            return "A warm jacket or hoodie is a smart choice."
        elif temp < 25:
            return "Light clothing is fine."
        else:
            return "Perfect t-shirt weather!"

def schedule_daily_message(bot, chat_id, city, hour, minute, language):
    job_id = f"routine_{chat_id}"
    scheduler.remove_job(job_id, jobstore=None) if scheduler.get_job(job_id) else None

    scheduler.add_job(
        send_morning_routine,
        'cron',
        hour=hour,
        minute=minute,
        args=[bot, chat_id, city, language],
        id=job_id
    )

def send_morning_routine(bot, chat_id, city, language):
    weather = get_weather(city, language, forecast_day=0)
    clothing_tip = generate_clothing_tip(weather["text"], language)
    mood = random.choice(MOOD_MESSAGES.get(language, MOOD_MESSAGES["en"]))

    # Übersetzungen je nach Sprache
    translations = {
        "de": {
            "greeting": "🌞 Guten Morgen!",
            "location": "📍 Ort",
            "clothing": "👕 Kleidungstipp",
            "mood": "💬 Stimmung"
        },
        "en": {
            "greeting": "🌞 Good morning!",
            "location": "📍 Location",
            "clothing": "👕 Clothing tip",
            "mood": "💬 Mood"
        }
    }

    t = translations.get(language, translations["en"])  # fallback zu Englisch

    msg = (
        f"{t['greeting']}\n\n"
        f"{t['location']}: {weather['location']}\n\n"
        f"{weather['text']}\n\n"
        f"{t['clothing']}: {clothing_tip}\n"
        f"{t['mood']}: {mood}"
    )
    bot.send_message(chat_id, msg)

def handle_routine(bot, message, text, language):
    chat_id = message.chat.id
    city, hour, minute = extract_routine_details(text, language)

    # Übersetzungen
    responses = {
        "de": {
            "missing_info": "Bitte gib eine Stadt und Uhrzeit an (z. B. „Routine um 7:00 in Berlin“)",
            "confirmed": f"Routine gespeichert! Tägliche Nachricht um {hour:02d}:{minute:02d} für {city}."
        },
        "en": {
            "missing_info": "Please provide a city and time (e.g., 'Routine at 7:00 in Berlin')",
            "confirmed": f"Routine saved! You’ll get a daily message at {hour:02d}:{minute:02d} for {city}."
        }
    }

    t = responses.get(language, responses["en"])

    if not city or hour is None:
        bot.reply_to(message, t["missing_info"])
        return

    user_info[str(chat_id)] = {
        "city": city,
        "hour": hour,
        "minute": minute,
        "language": language
    }
    save_user_information(user_info)

    schedule_daily_message(bot, chat_id, city, hour, minute, language)
    bot.reply_to(message, t["confirmed"])