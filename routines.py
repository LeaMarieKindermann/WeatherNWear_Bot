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
    with open(USER_INFORMATION_FILE, "w") as f:
        json.dump(info, f)

user_info = load_user_information()

def get_time_of_day(hour):
    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 15:
        return "noon"
    elif 15 <= hour < 18:
        return "afternoon"
    else:
        return "night"


def convert_to_24h_format(time_input):
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
    nlp = nlp_de if language == "de" else nlp_en
    text = text.strip().lower()

    # Ignoriere das Wort "erstelle" am Anfang der Nachricht
    if text.startswith("erstelle"):
        text = text[len("erstelle"):].strip()  # Entfernt "erstelle" und führt die Verarbeitung fort

    doc = nlp(text)

    city = None
    time_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)?', text, re.IGNORECASE)
    print(time_match)

    for ent in doc.ents:
        print(ent)
        if ent.label_ in ("GPE", "LOC") and ent.text.lower() not in ["erstelle"]:
            city = ent.text
            break
    print(city)

    if time_match:
        time_str = time_match.group(0)
        hour, minute = convert_to_24h_format(time_str)

        # Überprüfe, ob die Zeit erfolgreich konvertiert wurde
        if hour is None or minute is None:
            print("Fehler: Ungültiges Zeitformat")
            return None, None, None  # Rückgabe von None, wenn die Zeitumwandlung fehlschlägt

        print(city, hour, minute)
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

    if language == "de":
        if temp < 5:
            return "Zieh dich warm an – Mütze und Schal könnten helfen!"
        elif temp < 15:
            return "Eine wärmere Jacke oder ein Hoodie zum drüberziehen ist eine gute Idee."
        elif temp < 25:
            return "Leichte Kleidung reicht aus."
        else:
            return "Perfektes T-Shirt-Wetter!"
    else:
        if temp < 5:
            return "Bundle up – a hat and scarf might help!"
        elif temp < 15:
            return "A warm jacket or hoodie is a smart choice."
        elif temp < 25:
            return "Light clothing is fine."
        else:
            return "Perfect t-shirt weather!"

def schedule_daily_message(bot, chat_id, city, hour, minute, language):
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
    # Hole das Wetter für die Stadt
    weather = get_weather(city, language, forecast_day=0)

    # Überprüfe, ob das Wetter erfolgreich abgerufen wurde
    if weather is None:
        bot.send_message(
            chat_id,
            "Leider konnte das Wetter nicht abgerufen werden. Bitte versuche es später noch einmal."
        )
        return

    # Generiere Kleidungstipps basierend auf den Wetterdaten
    clothing_tip = generate_clothing_tip(weather["text"], language)
    mood = random.choice(MOOD_MESSAGES.get(language, MOOD_MESSAGES["en"]))

    # Bestimme die Tageszeit
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

    # Erstelle die Nachricht
    msg = (
        f"{greeting}\n\n"
        f"{t['location']}: {weather['location']}\n\n"
        f"{weather['text']}\n\n"
        f"{t['clothing']}: {clothing_tip}\n"
    )

    if time_of_day == "morning":
        msg += f"{t['mood']}: {mood}"

    # Sende die Nachricht
    bot.send_message(chat_id, msg)


def handle_routine(bot, message, text, language):
    chat_id = str(message.chat.id)
    text_lower = text.strip().lower()

    print(text_lower)
    # 📌 Command: /routinen anzeigen
    if text_lower.startswith("/routines"):
        routines = user_info.get(chat_id, [])
        if not routines:
            msg = {
                "de": "Du hast aktuell keine Routinen gespeichert.",
                "en": "You don't have any saved routines yet."
            }.get(language, "No routines found.")
            return msg

        lines = []
        for i, r in enumerate(routines, 1):
            lines.append(f"{i}. {r['city']} – {r['hour']:02d}:{r['minute']:02d}")

        msg = {
            "de": "🗓️ Deine gespeicherten Routinen:\n\n" + "\n".join(lines) + "\n\nZum Löschen: /routine_löschen <Nummer>",
            "en": "🗓️ Your saved routines:\n\n" + "\n".join(lines) + "\n\nTo delete: /routine_löschen <number>"
        }.get(language, "\n".join(lines))

        return msg

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