import json
import os
import re
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from weather import get_weather
import random
import spacy
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import packing

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
    """
        Loads user routine data from the JSON file (user_information.json).
        If the file is missing, empty, or invalid, returns an empty dictionary.

        Returns:
            dict: User routine information, keyed by chat_id.
    """
    if os.path.exists(USER_INFORMATION_FILE):
        with open(USER_INFORMATION_FILE, "r") as f:
            content = f.read().strip()
            if not content:  # Wenn der Inhalt der Datei leer ist
                print("Die Datei ist leer, initialisiere mit einem leeren Dictionary.")
                return {}  # Rückgabe eines leeren Dictionaries
            try:
                data = json.loads(content)
                return data
            except json.JSONDecodeError:
                print("Fehler: Ungültiges JSON-Format in der Datei.")
                return {}  # Rückgabe eines leeren Dictionaries im Fehlerfall
    else:
        print("Fehler: Datei existiert nicht.")
        return {}  # Rückgabe eines leeren Dictionaries, wenn die Datei nicht existiert

def save_user_information(info):
    """
        Saves user routine information to a JSON file (user_information.json).

        Args:
            info (dict): Dictionary containing routine data to be saved.
    """
    with open(USER_INFORMATION_FILE, "w") as f:
        json.dump(info, f)

user_info = load_user_information()

def get_time_of_day(hour):
    """
        Determines the time of day based on the given hour.

        Args:
            hour (int): Hour in 24-hour format.

        Returns:
            str: One of 'morning', 'noon', 'afternoon', or 'night'.
    """
    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 15:
        return "noon"
    elif 15 <= hour < 18:
        return "afternoon"
    else:
        return "night"

def convert_to_24h_format(time_input):
    """
        Converts a time string (e.g. '7:30', '0730PM', '18') to 24-hour hour and minute values.

        Args:
            time_input (str): Input time string (supports formats like '7:00', '7pm', '19').

        Returns:
            tuple: (hour, minute) as integers, or (None, None) if conversion fails.
    """
    try:
        # Wenn es bereits im 24h-Format ist, z.B. 18 oder 6
        if time_input.isdigit():
            hour = int(time_input)
            minute = 0
        # Versuche, die Zeit im 12h-Format zu parsen, z.B. 6am, 3pm
        elif 'am' in time_input.lower() or 'pm' in time_input.lower():
            time_obj = datetime.strptime(time_input.strip(), '%I%M%p')
            hour = time_obj.hour
            minute = time_obj.minute
        else:
            # Fallback für alles andere im Format HH:MM
            time_obj = datetime.strptime(time_input.strip(), '%H:%M')
            hour = time_obj.hour
            minute = time_obj.minute

        return hour, minute
    except Exception as e:
        print(f"Fehler bei der Zeitumwandlung: {e}")
        return None, None  # Rückgabe von None, None im Fehlerfall

def extract_routine_details(text, language):
    """
    Extracts the city and time (hour and minute) from user input text to define a routine.

    Args:
        text (str): User input containing routine creation request.
        language (str): Language code ('de' or 'en') for proper NLP parsing.

    Returns:
        tuple: (city, hour, minute) or (None, None, None) if extraction fails.
    """
    print("Original Text:", text)

    # Nutze korrektes spaCy-Modell
    nlp = nlp_de if language == "de" else nlp_en

    # Original-Text an spaCy geben (keine Kleinschreibung!)
    text_cleaned = text.strip()
    doc = nlp(text_cleaned)

    city = None

    # Zeit (z. B. 7:00, 8pm, 0730AM) mit Regex erkennen (Kleinschreibung hier okay)
    time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text.lower(), re.IGNORECASE)
    print("Zeit erkannt:", time_match)

    # Ort aus spaCy-Entitäten extrahieren
    for ent in doc.ents:
        print(f"Entität erkannt: {ent.text} – {ent.label_}")
        if ent.label_ in ("GPE", "LOC") and ent.text.lower() not in ["erstelle", "routine", "für", "um", "eine"]:
            city = ent.text
            print("Ort erkannt:", city)
            break

    # Optionaler Fallback: letztes sinnvolles Wort im Text verwenden, wenn keine Entität erkannt wurde
    if not city:
        words = text_cleaned.split()
        for word in reversed(words):
            word_clean = word.strip(".,!?").lower()
            if word_clean not in ["erstelle", "routine", "für", "um", "eine", "routinen"]:
                city = word.strip(".,!?")
                print("[Fallback] Ort manuell erkannt:", city)
                break

    # Zeit verarbeiten
    if time_match:
        time_str = time_match.group(0)
        hour, minute = convert_to_24h_format(time_str)

        if hour is None or minute is None:
            print("Fehlerhafte Uhrzeit:", time_str)
            return None, None, None

        return city, hour, minute

    return None, None, None


def schedule_daily_message(bot, chat_id, city, hour, minute, language):
    """
        Schedules a daily message at a specified time using APScheduler.

        Args:
            bot: Telegram bot instance.
            chat_id (int or str): Telegram chat ID of the user.
            city (str): The city for which the routine is set.
            hour (int): Hour of the scheduled message.
            minute (int): Minute of the scheduled message.
            language (str): Language for the message content.
    """
    job_id = f"routine_{chat_id}_{city}_{hour:02d}_{minute:02d}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    scheduler.add_job(
        send_daily_routine,
        'cron',
        hour=hour,
        minute=minute,
        args=[bot, chat_id, city, language, hour, minute],
        id=job_id
    )

def send_daily_routine(bot, chat_id, city, language, hour, minute):
    """
        Sends the daily weather routine message to the user, including weather info,
        clothing tip, and mood message, adjusted for time of day.

        Args:
            bot: Telegram bot instance.
            chat_id (int): User's Telegram chat ID.
            city (str): City for which weather is fetched.
            language (str): 'de' or 'en' for message content.
            hour (int): Scheduled hour.
            minute (int): Scheduled minute.
    """
    weather = get_weather(city, language, forecast_day=0)
    print(weather)
    if weather is None:
        bot.send_message(chat_id,
                         "Leider konnte das Wetter nicht abgerufen werden. Bitte versuche es später noch einmal."
                         if language == "de" else
                         "Couldn't retrieve the weather. Please try again later."
                         )
        return

    dt = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    clothing_tip = packing.get_outfit_suggestion(chat_id, weather['location'], dt, language)

    mood = random.choice(MOOD_MESSAGES.get(language, MOOD_MESSAGES["en"]))
    time_of_day = get_time_of_day(hour)

    greetings = {
        "morning": {"de": "🌞 Guten Morgen!", "en": "🌞 Good morning!"},
        "noon": {"de": "🌞 Guten Mittag!", "en": "🌞 Good afternoon!"},
        "afternoon": {"de": "🌆 Guten Nachmittag!", "en": "🌆 Good afternoon!"},
        "night": {"de": "🌙 Guten Abend!", "en": "🌙 Good evening!"}
    }

    translations = {
        "de": {"location": "📍 Ort", "clothing": "👕 Kleidungstipp", "mood": "💬 Stimmung"},
        "en": {"location": "📍 Location", "clothing": "👕 Clothing tip", "mood": "💬 Mood"}
    }

    greeting = greetings.get(time_of_day, greetings["morning"]).get(language, "Hello!")
    t = translations.get(language, translations["en"])

    msg = (
        f"{greeting}\n\n"
        f"{t['location']}: {weather['location']}\n\n"
        f"{weather['text']}\n\n"
        f"{t['clothing']}: {clothing_tip}\n"
    )

    if time_of_day == "morning":
        msg += f"{t['mood']}: {mood}"

    bot.send_message(chat_id, msg)

def handle_routine(bot, message, text, language):
    """
        Handles all routine-related commands and messages:
        - Show all routines
        - Delete routine
        - Create a new routine (by parsing city + time)

        Args:
            bot: Telegram bot instance.
            message: The original Telegram message object.
            text (str): User message.
            language (str): 'de' or 'en'.

        Returns:
            str or None: Optional message to be sent back to the user.
    """
    chat_id = str(message.chat.id)
    text_lower = text.strip().lower()

    print(text_lower)
    # 📌 Command: /routinen anzeigen
    if text_lower.startswith("/routines") or "show all routines" in text_lower:
        routines = user_info.get(chat_id, [])
        if not routines:
            msg = {
                "de": "Du hast aktuell keine Routinen gespeichert.",
                "en": "You don't have any saved routines yet."
            }.get(language, "No routines found.")
            return msg

        # Routinen-Buttons mit Uhrzeit + Stadt
        markup = InlineKeyboardMarkup()
        for i, r in enumerate(routines):
            routine_text = f"{r['city']} – {r['hour']:02d}:{r['minute']:02d}"
            button_text = f"❌ {routine_text}"
            callback_data = f"delete_routine|{chat_id}|{i}|{language}"
            markup.add(InlineKeyboardButton(button_text, callback_data=callback_data))

        header = {
            "de": "🗓️ Deine gespeicherten Routinen:\n\nWähle eine Routine zum Löschen:",
            "en": "🗓️ Your saved routines:\n\nSelect a routine to delete:"
        }.get(language, "Your routines:")

        bot.send_message(chat_id, header, reply_markup=markup)
        return None

    # 📌 Command: /routine_löschen <nummer>
    if text_lower.startswith("/delete_routine"):
        parts = text_lower.split()
        routines = user_info.get(chat_id, [])

        if len(parts) != 2 or not parts[1].isdigit():
            return "Bitte gib die Nummer der Routine an. Beispiel: /routine_löschen 1" if language == "de" else "Please provide the routine number, e.g., /routine_löschen 1"

        index = int(parts[1]) - 1

        if 0 <= index < len(routines):
            routine = routines.pop(index)
            save_user_information(user_info)

            job_id = f"routine_{chat_id}_{routine['city']}_{routine['hour']:02d}_{routine['minute']:02d}"
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)

            return f"Routine {index+1} gelöscht." if language == "de" else f"Routine {index+1} deleted."
        else:
            return "Ungültige Routinenummer." if language == "de" else "Invalid routine number."

    # ⏰ Standard: Routine erstellen (bestehender Code)
    city, hour, minute = extract_routine_details(text, language)

    responses = {
        "de": {
            "missing_info": "Bitte gib eine Stadt und Uhrzeit an (z. B. „Routine um 7:00 in Berlin“)",
            "confirmed": "Routine gespeichert! Tägliche Nachricht um {time} für {city}."
        },
        "en": {
            "missing_info": "Please provide a city and time (e.g., 'Routine at 7:00 in Berlin')",
            "confirmed": "Routine saved! You’ll get a daily message at {time} for {city}."
        }
    }

    t = responses.get(language, responses["en"])

    if not city or hour is None:
        return t["missing_info"]

    routine = {
        "city": city,
        "hour": hour,
        "minute": minute,
        "language": language
    }

    user_info.setdefault(chat_id, []).append(routine)
    save_user_information(user_info)

    schedule_daily_message(bot, int(chat_id), city, hour, minute, language)

    time_str = f"{hour:02d}:{minute:02d}"
    return t["confirmed"].format(time=time_str, city=city)