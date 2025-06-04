import telebot
import requests
from telebot import types
from apscheduler.schedulers.background import BackgroundScheduler
import random
import json
import os

# Config-information - API_Key, Bot_Token
BOT_TOKEN = ''
WEATHER_API_KEY = ''
bot = telebot.TeleBot(BOT_TOKEN)

# JSON-File for saving the reminder-information
USER_INFORMATION_FILE = "user_information.json"

# Loading/opening the JSON-File
def load_user_information():
    if os.path.exists(USER_INFORMATION_FILE):
        with open(USER_INFORMATION_FILE, "r") as f:
            return json.load(f)
    return {}

# Saving the user information
def save_user_information(info):
    with open(USER_INFORMATION_FILE, "w") as f:
        json.dump(info, f)

user_info = load_user_information()

# Function to fetch the weather from the API
def get_weather(city):
    url = "https://api.weatherapi.com/v1/current.json"
    params = {
        'key': WEATHER_API_KEY,
        'q': city,
        'lang': 'en'
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return None

    # extract data
    data = response.json()
    condition = data['current']['condition']['text']
    temp = data['current']['temp_c']
    feels_like = data['current']['feelslike_c']
    wind = data['current']['wind_kph']
    humidity = data['current']['humidity']

    return {
        'text': f"🌤 Weather in {data['location']['name']}:\n"
                f"{condition}, {temp}°C (feels like {feels_like}°C)\n"
                f"💨 Wind: {wind} km/h\n"
                f"💧 Humidity: {humidity}%",
        'temp': temp
    }

# First solution for the clothing tips, if conditions for different temps
def get_clothing_tip(temp):
    if temp < 5:
        return "🧥 It's very cold. Put on a thick jacket!"
    elif temp < 15:
        return "🧣 A bit chilly - a jacket would be good."
    elif temp < 25:
        return "👕 A light outfit is enough."
    else:
        return "🩳 Very warm! Summer clothes are perfect."

# Mood Quotes (will be replaced with an API-Call)
MOOD_MESSAGES = [
    "Don't stress yourself, everything is gonna work out 😊",
    "Take a deep breath. You've got this! 🌟",
    "New day, new chance 💪",
    "Trust the process. Everything will be okay 🧘"
]

# /weather LOCATION - Weather command (created for testing the API)
@bot.message_handler(commands=['weather'])
def weather_command(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "Please enter a city. Example: /weather Berlin")
        return
    city = parts[1]
    result = get_weather(city)
    if result:
        bot.send_message(message.chat.id, result['text'])
    else:
        bot.send_message(message.chat.id, "❌ Weather could not be retrieved. Please check the city.")

# /setroutine – Set a reminder with a certain time and location
@bot.message_handler(commands=['setroutine'])
def set_routine(message):
    msg = bot.send_message(message.chat.id, "Please enter your city and time (HH:MM, 24h format).\nExample: `Berlin 06:30`", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_routine_input)

# Processes user input to set a daily reminder - expects a message in a specific format, stores the user-info and schedules a notification
def process_routine_input(message):
    try:
        user_id = str(message.chat.id)
        parts = message.text.strip().split()

        if len(parts) != 2:
            bot.send_message(message.chat.id, "❌ Invalid format. Example: `Berlin 06:30`")
            return

        city, time = parts
        hour, minute = map(int, time.split(":"))

        # save the information
        user_info[user_id] = {
            "city": city,
            "hour": hour,
            "minute": minute,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name or ""
        }
        save_user_information(user_info)

        # reschedule a job (for now, old jobs will just be deleted - TODO: later more reminders should be possible)
        if scheduler.get_job(job_id=user_id):
            scheduler.remove_job(job_id=user_id)

        scheduler.add_job(
            func=lambda chat_id=message.chat.id: send_custom_routine(chat_id),
            trigger='cron',
            hour=hour,
            minute=minute,
            id=user_id
        )

        bot.send_message(message.chat.id, f"✅ Reminder set: {city} at {hour:02d}:{minute:02d}.")

    except ValueError:
        bot.send_message(message.chat.id, "❌ Time format invalid. Use HH:MM (z. B. 07:00).")

# Sending the reminder-message
def send_custom_routine(chat_id):
    user_id = str(chat_id)
    settings = user_info.get(user_id)
    if not settings:
        return

    # Inforamtion about the user
    city = settings['city']
    first_name = settings.get('first_name', '')
    last_name = settings.get('last_name', '')

    # fetching the data
    weather_data = get_weather(city)
    if not weather_data:
        bot.send_message(chat_id, f"⚠️ Weather data for {city} could not be loaded.")
        return

    # setting the clothing advice and random quote
    temp = weather_data['temp']
    clothing_tip = get_clothing_tip(temp)
    mood = random.choice(MOOD_MESSAGES)

    message = f"🌅 **Hello {first_name} {last_name}!**\n\n{weather_data['text']}\n\n{clothing_tip}\n\n💬 *{mood}*"
    bot.send_message(chat_id, message, parse_mode="Markdown")

# Scheduler setup
scheduler = BackgroundScheduler()
scheduler.start()

# Load already saved reminder
for user_id, config in user_info.items():
    scheduler.add_job(
        func=lambda chat_id=int(user_id): send_custom_routine(chat_id),
        trigger='cron',
        hour=config['hour'],
        minute=config['minute'],
        id=user_id
    )

# Start the Bot (Testing purpose)
bot.infinity_polling()


# Ich aender die File noch ab zu diesem Style damit wir es einheitlich haben, habs nur erstmal zum Verstaendnis so gelassen hihi :)
"""
def handle_routine(bot, message, language):
    
    Handle the routine command.
    This function is called to handle routine-related requests from the user.
    It provides an opporunity for the user to set up daily routines.
    It sends a message providing a list of daily routines.
    It automatically sends messages to the user at the scheduled times.

    -----

    Args:
        bot: The telebot instance.
        message: The message object containing user input.

    bot.reply_to(message, "Routine Feature is coming soon.\n")    
"""