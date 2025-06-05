# Use spaCy for language processing https://spacy.io/
import spacy 
# Load the language models for German and English
nlp_de = spacy.load("de_core_news_sm") # python -m spacy download de_core_news_sm to install the German model
nlp_en = spacy.load("en_core_web_sm") # python -m spacy download en_core_web_sm to install the English model

# To safe the reminder information, we use a JSON file
import json
import os

import time
from datetime import datetime, timedelta
import re
from rapidfuzz import fuzz

'''
A helper function to normalize the time string.
This function ensures that the time string is in a consistent format (HH:MM).

----
Args:
    time_str (str): The time string to normalize.
'''
def normalize_time_string(time_str):
    # Entferne "Uhr", Leerzeichen und mache alles klein
    s = time_str.lower().replace("uhr", "").replace(" ", "")
    # 12-Stunden-Format mit am/pm
    match = re.match(r"(\d{1,2}):?(\d{2})?(am|pm)", s)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        ampm = match.group(3)
        if ampm == "pm" and hour != 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute:02d}"
    # 24-Stunden-Format (z.B. 14:47)
    match = re.match(r"(\d{1,2}):(\d{2})", s)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        return f"{hour:02d}:{minute:02d}"
    # Nur Stunde (z.B. 14 oder 2pm)
    match = re.match(r"(\d{1,2})(am|pm)?", s)
    if match:
        hour = int(match.group(1))
        ampm = match.group(2)
        if ampm == "pm" and hour != 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
        return f"{hour:02d}:00"
    return None

"""
Parse a time expression from the text.
This function extracts time expressions from the text and returns them in a normalized format.

----

Args:
    text (str): The input text containing time expressions.
    language (str): The language of the input text ('de' for German, 'en' for English).
"""
def parse_time_expression(text, language):
    """
    Extracts and normalizes time expressions from the text.
    Returns a string in 'YYYY-MM-DD HH:MM' (24h) format.
    """
    now = datetime.now()
    text = text.lower()

    # 0. Relative day expressions
    day_offset = 0
    # German
    if re.search(r"\bübermorgen\b", text):
        day_offset = 2
    elif re.search(r"\bmorgen\b", text):
        day_offset = 1
    # English
    elif re.search(r"\bthe day after tomorrow\b", text):
        day_offset = 2
    elif re.search(r"\btomorrow\b", text):
        day_offset = 1

    # 1. Relative time expressions: "in 10 minutes", "in einer Stunde", "in 2 hours"
    rel_patterns = [
        (r"in\s+(\d+)\s*min",  lambda m: now + timedelta(minutes=int(m.group(1)))),
        (r"in\s+(\d+)\s*stunden?", lambda m: now + timedelta(hours=int(m.group(1)))),
        (r"in\s+(\d+)\s*hours?", lambda m: now + timedelta(hours=int(m.group(1)))),
        (r"in\s+(\d+)\s*minutes?", lambda m: now + timedelta(minutes=int(m.group(1)))),
        (r"in\s+einer\s*stunde", lambda m: now + timedelta(hours=1)),
        (r"in\s+an\s*hour", lambda m: now + timedelta(hours=1)),
    ]
    for pattern, func in rel_patterns:
        match = re.search(pattern, text)
        if match:
            t = func(match)
            return t.strftime("%Y-%m-%d %H:%M")

    # 2. Absolute time expressions (German/English mixed)
    abs_patterns = [
        r"(\d{1,2}):(\d{2})\s*(uhr)?",         # 14:47, 14:47 Uhr
        r"(\d{1,2})\s*uhr",                    # 14 Uhr
        r"(\d{1,2}):(\d{2})\s*(am|pm)",        # 2:47 pm
        r"(\d{1,2})\s*(am|pm)",                # 2 pm
    ]
    for pattern in abs_patterns:
        match = re.search(pattern, text)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.lastindex >= 2 and match.group(2) and match.group(2).isdigit() else 0
            ampm = match.group(match.lastindex) if match.lastindex and match.group(match.lastindex) in ("am", "pm") else None
            if ampm:
                if ampm == "pm" and hour != 12:
                    hour += 12
                if ampm == "am" and hour == 12:
                    hour = 0
            # Use day offset if present
            date = (now + timedelta(days=day_offset)).strftime("%Y-%m-%d")
            return f"{date} {hour:02d}:{minute:02d}"

    # 3. spaCy fallback (TIME/DATE)
    nlp = nlp_de if language == "de" else nlp_en
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ in ("TIME", "DATE"):
            # Try to parse with dateparser if available, else fallback to today
            try:
                import dateparser
                dt = dateparser.parse(ent.text, languages=[language])
                if dt:
                    return dt.strftime("%Y-%m-%d %H:%M")
            except ImportError:
                pass
            norm = normalize_time_string(ent.text)
            if norm:
                date = (now + timedelta(days=day_offset)).strftime("%Y-%m-%d")
                return f"{date} {norm}"

    return None

"""
Remove fuzzy phrases from the text.
This function removes phrases that are similar to the specified phrases using fuzzy matching.

-----

Args:
    text (str): The input text from which to remove phrases.
    phrases (list): A list of phrases to remove from the text.
    threshold (int): The similarity threshold for fuzzy matching (default is 80).
"""
def remove_fuzzy_phrases(text, phrases, threshold=80):
    for phrase in phrases:
        # Slide over the text and remove similar phrases
        words = text.split()
        n = len(phrase.split())
        i = 0
        while i <= len(words) - n:
            window = " ".join(words[i:i+n])
            if fuzz.ratio(window.lower(), phrase.lower()) >= threshold:
                del words[i:i+n]
                # Don't increment i, as the list has shifted
            else:
                i += 1
        text = " ".join(words)
    return text

'''
Extracts the time and the actual reminder content ("what") from the input text.
Uses spaCy to remove time/date entities and strips common reminder phrases.

----

Args:
    text (str): The input text containing the reminder information.
    language (str): The language of the input text, either "de" for German or "en" for English.
'''
def extract_reminder_info(text, language):
    time_str = parse_time_expression(text, language)
    nlp = nlp_de if language == "de" else nlp_en
    doc = nlp(text)
    what = text
    for ent in doc.ents:
        if ent.label_ in ("TIME", "DATE"):
            what = what.replace(ent.text, "")

    if language == "de":
        phrases = [
            "erinnere mich", "erinner mich", "erinnere", "bitte", "daran", "an"
        ]
        what = remove_fuzzy_phrases(what, phrases)
        # Remove all relative time expressions (short and long forms)
        what = re.sub(r"\bin \d+\s*(minuten?|min|stunden?|std|h)\b", "", what, flags=re.IGNORECASE)
        what = re.sub(r"\bin einer stunde\b", "", what, flags=re.IGNORECASE)
        what = re.sub(r"\bum \d{1,2}(:\d{2})?\s*uhr\b", "", what, flags=re.IGNORECASE)
    else:
        phrases = [
            "remind me", "please", "about", "to"
        ]
        what = remove_fuzzy_phrases(what, phrases)
        # Remove all relative time expressions (short and long forms)
        what = re.sub(r"\bin \d+\s*(minutes?|min|hours?|h)\b", "", what, flags=re.IGNORECASE)
        what = re.sub(r"\bin an hour\b", "", what, flags=re.IGNORECASE)
        # Remove absolute time expressions like "at 3:15pm", "at 3pm", "at 15:15", "at 3:15pm for"
        what = re.sub(r"\bat \d{1,2}(:\d{2})?\s*(am|pm)?(\s*for)?\b", "", what, flags=re.IGNORECASE)

    what = what.strip(" ,.:;-").strip()
    if not what and time_str:
        what = text.replace(time_str, "").strip(" ,.:;-")
    if not what:
        what = text.strip()
    return time_str, what

"""
Save the reminder information to a JSON file.

----

Args:
    chat_id (int): The ID of the chat where the reminder is set.
    time_str (str): The time when the reminder should be sent.
    what (str): The content of the reminder.
    language (str): The language of the reminder.
"""
def save_reminder(chat_id, time_str, what, language):
    reminders_file = "reminders.json"
    reminders = {}

    # Parse time_str to datetime object (today by default)
    now = datetime.now()
    try:
        # Try to parse full datetime if already in that format
        reminder_dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        norm_time = reminder_dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        # Otherwise, assume only time is given, use today
        norm_time = now.strftime("%Y-%m-%d") + " " + normalize_time_string(time_str)

    if not norm_time:
        print("Invalid time format. Reminder not saved.")
        return 1

    # Load existing reminders if the file exists
    if os.path.exists(reminders_file):
        try:
            with open(reminders_file, "r") as f:
                reminders = json.load(f)
        except json.JSONDecodeError:
            reminders = {}
    else:
        reminders = {}

    # Add the new reminder to the list for this chat_id
    if str(chat_id) not in reminders:
        reminders[str(chat_id)] = []
    reminders[str(chat_id)].append({
        "time": norm_time,
        "what": what,
        "language": language
    })

    # Save the updated reminders back to the file
    with open(reminders_file, "w") as f:
        json.dump(reminders, f, indent=4)

    return 0  # Return 0 to indicate success

"""
Helper function to format the reminder time in the response message.

----

Args:
    time_str (str): The time string to format.
    language (str): The language of the response ('de' for German, 'en' for English).
"""
def format_reminder_time(timestr, language):
    """
    Formats the reminder time for user-friendly output.
    """
    try:
        dt = datetime.strptime(timestr, "%Y-%m-%d %H:%M")
    except Exception:
        return timestr  # fallback

    now = datetime.now()
    today = now.date()
    reminder_date = dt.date()
    time_part = dt.strftime("%H:%M")

    if language == "de":
        if reminder_date == today:
            return f"um {time_part}"
        elif reminder_date == today + timedelta(days=1):
            return f"morgen um {time_part}"
        elif reminder_date == today + timedelta(days=2):
            return f"übermorgen um {time_part}"
        else:
            return f"am {dt.strftime('%d.%m.')} um {time_part}"
    else:
        if reminder_date == today:
            return f"at {time_part}"
        elif reminder_date == today + timedelta(days=1):
            return f"tomorrow at {time_part}"
        elif reminder_date == today + timedelta(days=2):
            return f"the day after tomorrow at {time_part}"
        else:
            return f"on {dt.strftime('%b %d')} at {time_part}"

"""
Handle the reminder command.
This function is called when the intent of the user is found to be reminder.
It sends a message at a specified time to remind the user of an event or task.

-----

Args:
    bot: The telebot instance.
    message: The message object containing user input.
    text: The text of the message.
    language: The language of the message.
"""
def handle_reminder(bot, message, text, language):
    time_str, what = extract_reminder_info(text, language)
    print(f"Extracted time: {time_str}, what: {what}")
    if not what or what.strip() == "":
        if language == "de":
            bot.reply_to(message, "Bitte gib an, woran ich dich erinnern soll.")
        else:
            bot.reply_to(message, "Please specify what I should remind you about.")
        return
    if time_str:
        errorcode = save_reminder(message.chat.id, time_str, what, language)
        if errorcode == 1:
            if language == "de":
                bot.reply_to(message, "Die Uhrzeit ist nicht im richtigen Format. Bitte versuche es erneut.")
            else:
                bot.reply_to(message, "The time is not in the correct format. Please try again.")
        else:
            if language == "de":
                bot.reply_to(message, f"Okay, ich werde dich {format_reminder_time(time_str, language)} daran erinnern, {what}")
            else:
                bot.reply_to(message, f"Okay, I will remind you {format_reminder_time(time_str, language)} to {what}")
    else:
        if language == "de":
            bot.reply_to(message, "Bitte gib eine Uhrzeit an, wann ich dich erinnern soll.")
        else:
            bot.reply_to(message, "Please specify a time when I should remind you.")

"""
Check reminders periodically and send notifications.
This function runs in a separate thread to avoid blocking the main bot loop.
"""
def check_reminders(bot):
    while True:
        try:
            with open("reminders.json", "r", encoding="utf-8") as f:
                reminders = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            reminders = {}

        changed = False
        for chat_id, reminder_list in list(reminders.items()):
            for reminder in reminder_list[:]:  # copy the list to avoid modifying it while iterating
                reminder_time = reminder["time"]
                try:
                    now_dt = datetime.now()
                    reminder_dt = datetime.strptime(reminder_time, "%Y-%m-%d %H:%M")
                    if now_dt >= reminder_dt:
                        # Only send if is now (±1 minute)
                        if 0 <= (now_dt - reminder_dt).total_seconds() < 60:
                            if reminder["language"] == "de":
                                bot.send_message(chat_id, f"Erinnerung: {reminder['what']}")
                            else:
                                bot.send_message(chat_id, f"Reminder: {reminder['what']}")
                        # delete the reminder after sending
                        print(f"Removing reminder for chat {chat_id}: {reminder['what']} at {reminder_time}")
                        reminder_list.remove(reminder)
                        changed = True
                except Exception as e:
                    print(e)
            if not reminder_list:
                del reminders[chat_id]
        if changed:
            with open("reminders.json", "w", encoding="utf-8") as f:
                json.dump(reminders, f, ensure_ascii=False, indent=4)
        now = datetime.now()
        seconds_to_next_minute = 60 - now.second
        time.sleep(max(0.01, seconds_to_next_minute))
