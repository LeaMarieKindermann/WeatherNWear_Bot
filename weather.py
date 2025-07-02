import requests
import spacy

from reminder import normalize_time_string
from wnw_bot_api_token import weather_API_TOKEN
# from reminder import parse_time_expression
from datetime import datetime, timedelta

# Load the language models for German and English
nlp_de = spacy.load("de_core_news_sm") # python -m spacy download de_core_news_sm to install the German model
nlp_en = spacy.load("en_core_web_sm") # python -m spacy download en_core_web_sm to install the English model

WEATHER_API_KEY = weather_API_TOKEN

def extract_forecast_day(text, language):
    """
    Extracts relative day index from user text.
    Returns:
        - 0 = heute/today
        - 1 = morgen/tomorrow
        - 2 = übermorgen/the day after tomorrow
        - None = keine Angabe/no information
    """

    text = text.lower()

    if language == "de":
        if "übermorgen" in text:
            return 2
        elif "morgen" in text:
            return 1
        elif "heute" in text:
            return 0
    elif language == "en":
        if "day after tomorrow" in text:
            return 2
        elif "tomorrow" in text:
            return 1
        elif "today" in text:
            return 0

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
    if forecast_day is None:
        # Current
        url = "https://api.weatherapi.com/v1/current.json"
        params = {
            'key': WEATHER_API_KEY,
            'q': city,
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
            'q': city,
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
    forecast_texts = []
    intro = f"📍 {location} \n 3-Tage-Wettervorhersage:\n\n"

    labels = {
        0: "🌤 Heute",
        1: "🌥 Morgen",
        2: "🌧 Übermorgen"
    }

    for day in range(3):
        weather = get_weather(location, "de", day)
        if weather:
            forecast_texts.append(f"{labels.get(day)}:\n{weather['text'].split(':', 1)[1].strip()}")
        else:
            forecast_texts.append(f"{labels.get(day)}: ⚠️ Leider keine Wetterdaten verfügbar.")

    outro = "\n\n❗ Hinweis: Wetterdaten können sich kurzfristig ändern."
    full_forecast = intro + "\n\n".join(forecast_texts) + outro

    return full_forecast
