import requests
import spacy
from word2number import w2n
import re
from datetime import datetime, timedelta

from reminder import normalize_time_string
from wnw_bot_api_token import weather_API_TOKEN, open_API_TOKEN
# from reminder import parse_time_expression
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Load the language models for German and English
nlp_de = spacy.load("de_core_news_sm")
nlp_en = spacy.load("en_core_web_sm")

WEATHER_API_KEY = weather_API_TOKEN
OPEN_API_KEY = open_API_TOKEN

def get_day_index_from_weekday_name(name, language):
    """
        Calculates the index (offset from today) for a given weekday name.

        Example: If today is Monday and 'Thursday' is given, the function returns 3.

        Args:
            name (str): Name of the weekday (e.g., "Thursday" or "Donnerstag")
            language (str): Language code ('en' or 'de')

        Returns:
            int or None: Number of days from today to the target weekday
                         (0 = today, 1 = tomorrow, etc.), or None if not found.
    """
    weekdays = {
        "de": ["montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag"],
        "en": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    }
    today_idx = datetime.today().weekday()
    try:
        target_idx = weekdays[language].index(name.lower())
        return (target_idx - today_idx + 7) % 7
    except (ValueError, KeyError):
        return None

    delta = (target_idx - today_idx + 7) % 7
    return delta

def extract_forecast_day(text, language):
    """
    Extracts relative day index from text (heute, morgen, in 3 Tagen, am Donnerstag, etc.)
    """
    text = text.lower()

    GERMAN_NUMBERS = {
        "eins": 1, "ein": 1, "eine": 1,
        "zwei": 2, "drei": 3, "vier": 4, "fünf": 5,
        "sechs": 6, "sieben": 7, "acht": 8, "neun": 9, "zehn": 10
    }

    keywords = {
        "de": {"today": "heute", "tomorrow": "morgen", "day_after": "übermorgen"},
        "en": {"today": "today", "tomorrow": "tomorrow", "day_after": "day after tomorrow"}
    }

    numbers_pattern = {
        "de": r"in\s+(\d+|eins|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn)\s+tagen?",
        "en": r"in\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+days?"
    }

    weekdays = {
        "de": ["montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag"],
        "en": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    }

    match = re.search(numbers_pattern[language], text)
    if match:
        num_str = match.group(1)
        try:
            return int(num_str)
        except ValueError:
            if language == "de":
                return GERMAN_NUMBERS.get(num_str)
            else:
                return w2n.word_to_num(num_str)

    if keywords[language]["day_after"] in text:
        return 2
    if keywords[language]["tomorrow"] in text:
        return 1
    if keywords[language]["today"] in text:
        return 0

    for day in weekdays[language]:
        if f"am {day}" in text or f"on {day}" in text or day in text:
            return get_day_index_from_weekday_name(day, language)

    match = re.search(numbers_pattern[language], text)
    if match:
        num_str = match.group(1)
        try:
            return int(num_str)
        except ValueError:
            try:
                return w2n.word_to_num(num_str)
            except:
                return None

    return None

def extract_location(text, language):
    """
    Extracts a location (city/region) from the given input text using spaCy NER.
    Accepts both LOC and GPE labels for better coverage.
    """
    nlp = nlp_de if language == "de" else nlp_en
    doc = nlp(text)

    for ent in doc.ents:
        if ent.label_ in ("LOC", "GPE"):  # 🔧 <-- Hier der Fix
            print(ent.text)
            return ent.text

    return None

def get_weather(city, language, forecast_day):
    """
    Fetches weather data (current or forecast) for a given city.
    Depending on whether a forecast day index is provided, the function retrieves the current weather or the forecast.

    Args:
        city (str): The name of the city to get weather data for
        language (str): The language code ('de' for German, 'en' for English)
        forecast_day (int or None): The forecast day index (0 = today, 1 = tomorrow, 2 = overmorrow), or None for current weather

    Returns:
        dict or None: A dictionary with formatted weather text and location info, or None if the API request failed
    """

    # Step 1: Get lat/lon from city name
    geo_url = "http://api.openweathermap.org/geo/1.0/direct"
    geo_params = {
        "q": city,
        "limit": 1,
        "appid": OPEN_API_KEY
    }

    geo_response = requests.get(geo_url, params=geo_params)
    if geo_response.status_code != 200 or not geo_response.json():
        return None

    print(geo_response.json())

    location = geo_response.json()[0]
    lat = location['lat']
    lon = location['lon']
    city_name = location['name']

    if forecast_day is None:
        # Current
        url = "https://api.weatherapi.com/v1/current.json"
        params = {
            'key': WEATHER_API_KEY,
            'q': f"{lat},{lon}",
            'lang': language
        }
        response = requests.get(url, params=params)
        if response.status_code != 200:
            return None

        data = response.json()

        if language == "de":
            return {
                'location': data['location']['name'],
                'text': f"🌤 Aktuelles Wetter in {data['location']['name']}:\n"
                        f"{data['current']['condition']['text']}, {data['current']['temp_c']}°C\n"
                        f"💨 Wind: {data['current']['wind_kph']} km/h\n"
                        f"💧 Luftfeuchtigkeit: {data['current']['humidity']}%"
            }
        else:
            return {
                'location': data['location']['name'],
                'text': f"🌤 Current weather in {data['location']['name']}:\n"
                        f"{data['current']['condition']['text']}, {data['current']['temp_c']}°C\n"
                        f"💨 Wind: {data['current']['wind_kph']} km/h\n"
                        f"💧 Humidity: {data['current']['humidity']}%"
            }

    else:
        # Forecast
        url = "https://api.weatherapi.com/v1/forecast.json"
        params = {
            'key': WEATHER_API_KEY,
            'q': f"{lat},{lon}",
            'lang': language,
            'days': forecast_day + 1
        }
        response = requests.get(url, params=params)
        if response.status_code != 200:
            return None

        data = response.json()
        forecast = data['forecast']['forecastday'][forecast_day]['day']
        condition = forecast['condition']['text']
        avg_temp = forecast['avgtemp_c']
        min_temp = forecast['mintemp_c']
        max_temp = forecast['maxtemp_c']
        date = data['forecast']['forecastday'][forecast_day]['date']

        if language == "de":
            label = {
                0: "Heute",
                1: "Morgen",
                2: "Übermorgen"
            }.get(forecast_day, f"am {date}")

            return {
                'location': data['location']['name'],
                'text': f"📅 {label} in {data['location']['name']}:\n"
                        f"{condition}, Ø {avg_temp}°C (⤵ {min_temp}°C / ⤴ {max_temp}°C)"
            }

        else:
            label = {
                0: "Today",
                1: "Tomorrow",
                2: "The day after tomorrow"
            }.get(forecast_day, f"on {date}")

            return {
                'location': data['location']['name'],
                'text': f"📅 {label} in {data['location']['name']}:\n"
                        f"{condition}, avg {avg_temp}°C (min {min_temp}°C / max {max_temp}°C)"
            }

def handle_weather(bot, message, text, language):
    """
        Handle the weather command.
        This function is called when the intent of the user is found to be a weather forecast.
        It sends a message with the specified weather forecast for the given location.

        Args:
            bot: The bot instance
            message: The incoming message object
            text (str): The user's message text
            language (str): The detected language code ('de' or 'en')
    """
    print(f"handle_weather called with text: {text}, language: {language}")
    location = extract_location(text, language)
    forecast_day = extract_forecast_day(text, language)

    if forecast_day is not None and forecast_day > 2:
        return (
            "⚠️ Die Wettervorhersage ist nur für bis zu 3 Tage im Voraus verfügbar."
            if language == "de"
            else "⚠️ Forecast is only available for up to 3 days ahead."
        )

    if not location:
        if language == "de":
            return "❌ I could not detect a location. Please try again."
        else:
            return "❌ I couldn't detect a location. Please try again."
    weather = get_weather(location, language, forecast_day)
    if weather:
        return weather['text']
    else:
        return f"⚠️ Weather data for '{location}' could not be loaded."

def handle_weather_location(bot, message, location):
    """
        Sends a weather forecast up to 3 days for a given location

        This function:
        - Retrieves weather data for the next 3 days (today, tomorrow, day after tomorrow)
        - Formats the forecast as a message with clear labels and icons
        - Adds buttons for text-to-speech and a weather chart image

        Args:
            bot: The Telegram bot instance
            message: The original Telegram message object
            location (str): Name of the city or location to show the forecast for
    """
    forecast_texts = []
    intro = f"📍 {location} \n 3-Tage-Wettervorhersage:\n\n"

    labels = {
        0: "🌤 Heute",
        1: "🌥 Morgen",
        2: "🌧 Übermorgen"
    }

    for day in range(3):
        weather_data = get_weather(location, "de", day)
        if weather_data:
            forecast_texts.append(f"{labels.get(day)}:\n{weather_data['text'].split(':', 1)[1].strip()}")
        else:
            forecast_texts.append(f"{labels.get(day)}: ⚠️ Leider keine Wetterdaten verfügbar.")

    outro = "\n\n❗ Hinweis: Wetterdaten können sich kurzfristig ändern."
    full_forecast = intro + "\n\n".join(forecast_texts) + outro

    # Inline-Buttons: Vorlesen & Wettergrafik
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("🔊 Vorlesen", callback_data=f"tts|de"),
        InlineKeyboardButton("📊 Wettergrafik anzeigen", callback_data=f"weather_chart|{location}")
    )

    bot.send_message(message.chat.id, full_forecast, reply_markup=keyboard)

