# Use spaCy for language processing https://spacy.io/
import spacy
# Load the language models for German and English
nlp_de = spacy.load("de_core_news_sm") # python -m spacy download de_core_news_sm to install the German model
nlp_en = spacy.load("en_core_web_sm") # python -m spacy download en_core_web_sm to install the English model

from apscheduler.schedulers.background import BackgroundScheduler
import random
import requests

# To safe the reminder information, we use a JSON file
import json
import os
import datetime
import wardrobe
import weather

# Helper to extract temp and weather_type from weather.get_weather

def get_weather_forecast_compat(location, dt, language):
    """
    Compatibility wrapper for weather.get_weather to extract temp and weather_type.
    Returns dict with 'temp' and 'weather_type' or None if not available.
    """
    import re
    # Determine forecast_day (0=today, 1=tomorrow, 2=overmorrow)
    today = datetime.datetime.now().date()
    day_diff = (dt.date() - today).days
    forecast_day = day_diff if 0 <= day_diff <= 2 else None
    result = weather.get_weather(location, language, forecast_day)
    if not result or 'text' not in result:
        return None
    text = result['text']
    # Try to extract temperature (°C)
    temp_match = re.search(r'(?:ca\.|avg|Ø)?\s*(-?\d+)[,.]?\d*°C', text)
    temp = int(temp_match.group(1)) if temp_match else None
    # Try to extract weather type (first word/phrase before comma or after colon)
    weather_type = None
    if ':' in text:
        after_colon = text.split(':',1)[1].strip()
        weather_type = after_colon.split(',')[0].strip()
    elif ',' in text:
        weather_type = text.split(',')[0].strip()
    return {'temp': temp, 'weather_type': weather_type}

def get_outfit_suggestion(chat_id, location, dt, language="de"):
    """
    Suggests an outfit for a given user, location, and datetime.
    Args:
        chat_id: Telegram user id
        location: string (city or place)
        dt: datetime.datetime (when the outfit is needed)
        language: 'de' or 'en'
    Returns:
        str: Outfit suggestion
    """
    # Get weather for location and time
    forecast = get_weather_forecast_compat(location, dt, language)
    if not forecast or 'temp' not in forecast:
        return "Wetterdaten konnten nicht abgerufen werden." if language.startswith("de") else "Could not retrieve weather data."
    temp = forecast['temp']
    weather_type = map_weather_type(forecast.get('weather_type', 'any'), language)
    weather_type_disp = translate_weather_type(weather_type, language)
    _, user_wardrobe = wardrobe.get_or_create_user_wardrobe(chat_id, language)
    suggestion = []
    for cat, items in user_wardrobe.items():
        filtered = [i for i in items if isinstance(i, dict) and i['min_temp'] <= temp <= i['max_temp'] and (i.get('weather', 'any') == 'any' or i.get('weather', 'any') == weather_type)]
        if filtered:
            # Sort by priority (lower is better)
            filtered.sort(key=lambda x: x['prio'])
            suggestion.append(f"{cat}: {filtered[0]['name']}")
        else:
            if language.startswith("de"):
                suggestion.append(f"{cat}: Keine passende {cat.lower()} gefunden.")
            else:
                suggestion.append(f"{cat}: No suitable {cat.lower()} found.")
    if language.startswith("de"):
        return f"Für {location} am {dt.strftime('%d.%m.%Y')} (ca. {temp}°C, Wetter: {weather_type_disp}) schlage ich vor:\n" + "\n".join(suggestion)
    else:
        return f"For {location} on {dt.strftime('%Y-%m-%d')} (about {temp}°C, weather: {weather_type_disp}) I suggest:\n" + "\n".join(suggestion)

def get_packing_list(chat_id, location, start_date, end_date, language="de"):
    """
    Suggests a packing list for a trip to a location over a date range.
    Args:
        chat_id: Telegram user id
        location: string
        start_date: datetime.date
        end_date: datetime.date
        language: 'de' or 'en'
    Returns:
        str: Packing list
    """
    # Get weather for each day
    days = [(start_date + datetime.timedelta(days=i)) for i in range((end_date-start_date).days+1)]
    temps = []
    weather_types = set()
    for day in days:
        forecast = get_weather_forecast_compat(location, datetime.datetime.combine(day, datetime.time(12,0)), language)
        if forecast and 'temp' in forecast:
            temps.append(forecast['temp'])
            if 'weather_type' in forecast:
                weather_types.add(map_weather_type(forecast['weather_type'], language))
    if not temps:
        return "Wetterdaten konnten nicht abgerufen werden." if language.startswith("de") else "Could not retrieve weather data."
    min_temp = min(temps)
    max_temp = max(temps)
    _, user_wardrobe = wardrobe.get_or_create_user_wardrobe(chat_id, language)
    packing = []
    for cat, items in user_wardrobe.items():
        filtered = [i for i in items if isinstance(i, dict) and i['min_temp'] <= max_temp and i['max_temp'] >= min_temp and (i.get('weather', 'any') == 'any' or i.get('weather', 'any') in weather_types)]
        if filtered:
            filtered.sort(key=lambda x: x['prio'])
            packing.append(f"{cat}: {filtered[0]['name']}")
        else:
            if language.startswith("de"):
                packing.append(f"{cat}: Keine passende {cat.lower()} gefunden.")
            else:
                packing.append(f"{cat}: No suitable {cat.lower()} found.")
    if language.startswith("de"):
        return f"Für {location} ({start_date.strftime('%d.%m.%Y')} bis {end_date.strftime('%d.%m.%Y')}, {min_temp}°C bis {max_temp}°C, Wetter: {', '.join(weather_types)}) solltest du einpacken:\n" + "\n".join(packing)
    else:
        return f"For {location} ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}, {min_temp}°C to {max_temp}°C, weather: {', '.join(weather_types)}) you should pack:\n" + "\n".join(packing)

def needs_outfit_change(chat_id, location, date, language="de"):
    """
    Checks if the user needs to change outfit during the day due to weather changes.
    Args:
        chat_id: Telegram user id
        location: string
        date: datetime.date
        language: 'de' or 'en'
    Returns:
        str: Recommendation
    """
    # Get weather for morning, noon, evening
    times = [datetime.time(8,0), datetime.time(14,0), datetime.time(20,0)]
    temps = []
    weather_types = set()
    for t in times:
        forecast = get_weather_forecast_compat(location, datetime.datetime.combine(date, t), language)
        if forecast and 'temp' in forecast:
            temps.append(forecast['temp'])
            if 'weather_type' in forecast:
                weather_types.add(map_weather_type(forecast['weather_type'], language))
    if len(temps) < 2:
        return "Wetterdaten konnten nicht abgerufen werden." if language.startswith("de") else "Could not retrieve weather data."
    temp_diff = max(temps) - min(temps)
    if temp_diff >= 8 or len(weather_types) > 1:
        if language.startswith("de"):
            return f"Die Temperatur/Wetter schwankt am {date.strftime('%d.%m.%Y')} in {location} ({', '.join(weather_types)}) um {temp_diff}°C. Du solltest Wechselkleidung mitnehmen."
        else:
            return f"The temperature/weather in {location} on {date.strftime('%Y-%m-%d')} ({', '.join(weather_types)}) varies by {temp_diff}°C. You should bring a change of clothes."
    else:
        if language.startswith("de"):
            return f"Die Temperatur und das Wetter bleibt am {date.strftime('%d.%m.%Y')} in {location} relativ konstant. Wechselkleidung ist nicht nötig."
        else:
            return f"The temperature and weather in {location} on {date.strftime('%Y-%m-%d')} is relatively stable. No change of clothes needed."

def handle_packing(bot, message, text, language):
    """
    Interprets the user's packing-related input and calls the appropriate packing function.
    Uses spaCy for fast entity extraction (location, date).
    Args:
        bot: The telebot instance (not used here, but for compatibility)
        message: The message object (for chat_id)
        text (str): The user's message text.
        language (str): The detected language code ('de' or 'en').
    Returns:
        str: The packing/outfit recommendation or error message.
    """
    import re
    chat_id = message.chat.id
    text_lower = text.lower()
    nlp = nlp_de if language.startswith("de") else nlp_en
    doc = nlp(text)

    # --- Location Extraction ---
    location = next((ent.text for ent in doc.ents if ent.label_ in ("GPE", "LOC", "ORG")), None)
    if not location:
        match = re.search(r"\b(?:in|nach|to)\s+([A-ZÄÖÜA-Za-zäöüß\- ]+)", text)
        if match:
            location = match.group(1).strip()
    if not location:
        if language.startswith("de"):
            return "Ich konnte keinen Ort erkennen. Bitte gib den Zielort genauer an (z.B. 'in München')."
        else:
            return "I could not detect a location. Please specify your destination (e.g. 'in Munich')."

    # --- Date Extraction ---
    dt = None
    for ent in doc.ents:
        if ent.label_ == "DATE":
            ent_text = ent.text.lower()
            if any(w in ent_text for w in ["übermorgen", "the day after tomorrow"]):
                dt = datetime.datetime.now() + datetime.timedelta(days=2)
            elif any(w in ent_text for w in ["morgen", "tomorrow"]):
                dt = datetime.datetime.now() + datetime.timedelta(days=1)
            elif any(w in ent_text for w in ["heute", "today"]):
                dt = datetime.datetime.now()
            # TODO: smarter date parsing (z.B. mit dateparser)
            break
    if not dt:
        if any(w in text_lower for w in ["übermorgen", "the day after tomorrow"]):
            dt = datetime.datetime.now() + datetime.timedelta(days=2)
        elif any(w in text_lower for w in ["morgen", "tomorrow"]):
            dt = datetime.datetime.now() + datetime.timedelta(days=1)
        elif any(w in text_lower for w in ["heute", "today"]):
            dt = datetime.datetime.now()

    # --- Intent/Type Extraction ---
    trip_keywords = ["reise", "ausflug", "trip", "urlaub", "weekend"]
    change_keywords = ["wechsel", "wechselkleidung", "change", "outfit change"]
    is_trip = any(w in text_lower for w in trip_keywords)
    is_change = any(w in text_lower for w in change_keywords)

    # --- Decision Logic ---
    if is_trip:
        start_date = (datetime.datetime.now() + datetime.timedelta(days=1)).date()
        end_date = start_date + datetime.timedelta(days=2)
        return get_packing_list(chat_id, location, start_date, end_date, language)
    if is_change:
        if not dt:
            dt = datetime.datetime.now()
        return needs_outfit_change(chat_id, location, dt.date(), language)
    if not dt:
        dt = datetime.datetime.now()
    return get_outfit_suggestion(chat_id, location, dt, language)

def map_weather_type(raw_weather_type, language="de"):
    """
    Maps raw weather description to wardrobe categories: sunny, rain, snow, cloudy, any.
    """
    if not raw_weather_type:
        return 'any'
    w = raw_weather_type.lower()
    # German mapping
    if language.startswith("de"):
        if any(x in w for x in ["sonne", "sonnig", "klar"]):
            return "sunny"
        if any(x in w for x in ["regen", "regenschauer", "nass", "schauer", "niesel"]):
            return "rain"
        if any(x in w for x in ["schnee", "schneefall", "schneeschauer"]):
            return "snow"
        if any(x in w for x in ["bewölkt", "wolkig", "bedeckt", "trüb", "nebel"]):
            return "cloudy"
    # English mapping
    else:
        if any(x in w for x in ["sun", "sunny", "clear"]):
            return "sunny"
        if any(x in w for x in ["rain", "shower", "drizzle", "wet"]):
            return "rain"
        if any(x in w for x in ["snow", "sleet", "blizzard"]):
            return "snow"
        if any(x in w for x in ["cloud", "overcast", "fog", "mist", "haze"]):
            return "cloudy"
    return 'any'

def translate_weather_type(weather_type, language):
    """
    Translates wardrobe weather_type to display string in the correct language.
    """
    mapping = {
        "de": {
            "sunny": "Sonnig",
            "rain": "Regen",
            "snow": "Schnee",
            "cloudy": "Bewölkt",
            "any": "Beliebig"
        },
        "en": {
            "sunny": "sunny",
            "rain": "rain",
            "snow": "snow",
            "cloudy": "cloudy",
            "any": "any"
        }
    }
    lang = "de" if language.startswith("de") else "en"
    return mapping[lang].get(weather_type, weather_type)