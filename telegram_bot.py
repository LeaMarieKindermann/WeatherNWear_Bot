# Modules to import
import telebot
import os

# Custom modules to import
from wnw_bot_api_token import token as api_token
import packing
import routines
import wardrobe
import reminder
import weather
import requests

import speech_to_text
import intent_detection
import text_to_speech
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# For asynchronous operations
import threading

# Initialize the bot with the API token
bot = telebot.TeleBot(api_token, parse_mode=None)  # You can set parse_mode by default. HTML or MARKDOWN

## Define a function to send a welcome message
def send_welcome(message):
    first_name = message.from_user.first_name if message.from_user.first_name else ""
    last_name = message.from_user.last_name if message.from_user.last_name else ""
    bot.reply_to(message, f"Welcome, {first_name} {last_name}!")

def send_reply_with_tts_button(message, reply_text, lang):
    """
    Sendet eine Antwort mit Inline-Button zum Vorlesen.
    """
    keyboard = InlineKeyboardMarkup()
    button = InlineKeyboardButton("🔊 Vorlesen", callback_data=f"tts|{lang}")
    keyboard.add(button)
    bot.send_message(message.chat.id, reply_text, reply_markup=keyboard)

# Basic messge handler
@bot.message_handler(commands=['start'])
def handle_command(message):
    # Debugging output
    print(f"Message id: {message.message_id}, " + 
          f"chat id: {message.chat.id}, " + 
          f"username: {message.from_user.username}, " +
          f"({message.from_user.first_name} {message.from_user.last_name}), " +
          f"text: {message.text}"
          )
    # Call the function to send a welcome message
    if message.text == "/start":
        send_welcome(message)        
        wardrobe.get_or_create_user_wardrobe(message.chat.id)
        # get the user's Telegram interface language
        user_lang = getattr(message.from_user, "language_code", None)
        # Create wardrobe for the user in the correct language
        wardrobe.get_or_create_user_wardrobe(message.chat.id, user_lang)
        print(f"User Telegram language_code: {user_lang}")

# Handler for /kleiderschrank, /Kleiderschrank, /wardrobe, /Wardrobe
@bot.message_handler(commands=["kleiderschrank", "Kleiderschrank", "wardrobe", "Wardrobe"])
def handle_wardrobe_menu(message):
    language = getattr(message.from_user, "language_code", "de")
    keyboard = InlineKeyboardMarkup()
    if language.startswith("de"):
        keyboard.add(InlineKeyboardButton("Anzeigen", callback_data="wardrobe_show"))
        keyboard.add(InlineKeyboardButton("Hinzufügen", callback_data="wardrobe_add"))
        keyboard.add(InlineKeyboardButton("Löschen", callback_data="wardrobe_remove"))
        bot.send_message(message.chat.id, "Was willst du tun?", reply_markup=keyboard)
    else:
        keyboard.add(InlineKeyboardButton("Show", callback_data="wardrobe_show"))
        keyboard.add(InlineKeyboardButton("Add", callback_data="wardrobe_add"))
        keyboard.add(InlineKeyboardButton("Remove", callback_data="wardrobe_remove"))
        bot.send_message(message.chat.id, "What do you want to do?", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("wardrobe_cat_add|"))
def handle_wardrobe_cat_add(call):
    # callback_data: wardrobe_cat_add|category|item|language
    _, category, item, language = call.data.split("|", 3)
    chat_id = call.message.chat.id
    added, match_name = wardrobe.add_clothing(chat_id, category, item, fuzzy_threshold=100)
    # Remove the inline keyboard so the user can't click again
    try:
        bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=None)
    except Exception:
        pass  # Ignore if already edited or not possible
    if added:
        response = f"{item} wurde zu {category} hinzugefügt." if language.startswith("de") else f"{item} was added to {category}."
        bot.send_message(chat_id, response)
        bot.answer_callback_query(call.id)
    else:
        response = f"{match_name} ist bereits in deiner Kategorie {category}." if language.startswith("de") else f"{match_name} is already in your {category}."
        bot.send_message(chat_id, response)
        bot.answer_callback_query(call.id, text=response, show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("wardrobe_"))
def handle_wardrobe_action(call):
    action = call.data.split("_")[1]
    language = getattr(call.from_user, "language_code", "de")
    chat_id = call.message.chat.id
    if action == "show":
        response = wardrobe.handle_wardrobe(bot, call.message, "zeige meinen Kleiderschrank", language)
        bot.send_message(chat_id, response)
        bot.answer_callback_query(call.id)
        return
    elif action == "add":
        # Start add dialog: ask for item, then ask for category, then add
        def ask_item(msg):
            item = msg.text.strip()
            if not item:
                response = "No clothing item recognized." if not language.startswith("de") else "Kein Kleidungsstück erkannt."
                bot.send_message(msg.chat.id, response)
                return
            user_wardrobe = wardrobe.get_or_create_user_wardrobe(msg.chat.id)[1]
            cat, name = wardrobe.find_item_in_wardrobe(user_wardrobe, item)
            if cat:
                response = f"{item} ist bereits in deiner Kategorie {cat}." if language.startswith("de") else f"{item} is already in your {cat}."
                bot.send_message(msg.chat.id, response)
                return
            # Ask for category
            default_wardrobe = wardrobe.get_default_wardrobe(language)
            keyboard = InlineKeyboardMarkup()
            for cat in default_wardrobe.keys():
                keyboard.add(InlineKeyboardButton(cat, callback_data=f"wardrobe_cat_add|{cat}|{item}|{language}"))
            if language.startswith("de"):
                prompt = f"In welche Kategorie soll '{item}'?"
            else:
                prompt = f"Which category for '{item}'?"
            bot.send_message(msg.chat.id, prompt, reply_markup=keyboard)
        if language.startswith("de"):
            prompt = "Welches Kleidungsstück möchtest du hinzufügen?"
        else:
            prompt = "Which clothing item do you want to add?"
        msg = bot.send_message(call.message.chat.id, prompt)
        bot.register_next_step_handler(msg, ask_item)
        bot.answer_callback_query(call.id)
        return
    elif action == "remove":
        # Start remove dialog: ask for item, then remove from all categories
        def ask_item(msg):
            item = msg.text.strip()
            if not item:
                response = "No clothing item recognized." if not language.startswith("de") else "Kein Kleidungsstück erkannt."
                bot.send_message(msg.chat.id, response)
                return
            found, found_cat = wardrobe.remove_item_from_all_categories(msg.chat.id, item)
            if found:
                response = f"{item} wurde aus {found_cat} entfernt." if language.startswith("de") else f"{item} was removed from {found_cat}."
            else:
                response = f"{item} wurde nicht gefunden." if language.startswith("de") else f"{item} was not found."
            bot.send_message(msg.chat.id, response)
        if language.startswith("de"):
            prompt = "Welches Kleidungsstück möchtest du löschen?"
        else:
            prompt = "Which clothing item do you want to remove?"
        msg = bot.send_message(call.message.chat.id, prompt)
        bot.register_next_step_handler(msg, ask_item)
        bot.answer_callback_query(call.id)
        return
    
# Function to interpret the user's intent if it is not a command
@bot.message_handler(content_types=['text'])
def handle_text(message):
    text = message.text
    language = speech_to_text.detect_language(text)
    intent = intent_detection.detect_intent(text, language)
    print("Intent: " + str(intent))
    response = None
    if intent == "packing":
        response = packing.handle_packing(bot, message, text, language)
    elif intent == "routine":
        response = routines.handle_routine(bot, message, text, language)
    elif intent == "routine_list":
        response = routines.handle_routine(bot, message, "/routines", language)
    elif intent == "routine_delete":
        response = routines.handle_routine(bot, message, "/delete_routine", language)
    elif intent == "wardrobe":
        response = wardrobe.handle_wardrobe(bot, message, text, language)
    elif intent == "reminder":
        response = reminder.handle_reminder(bot, message, text, language)
    elif intent == "weather":
        response = weather.handle_weather(bot, message, text, language)
    else:
        if language == "de":
            response = "Es tut mir leid, ich habe dich nicht verstanden. Bitte versuche es erneut."
        elif language == "en":
            response = "Sorry, I didn't understand. Please try again."
    if response:
        send_reply_with_tts_button(message, response, language)

@bot.callback_query_handler(func=lambda call: call.data.startswith("tts|"))
def handle_tts_callback(call):
    lang = call.data.split("|", 1)[1]
    # Hole die letzte Bot-Nachricht im Chat (optional: oder speichere Text im Callback)
    # Hier nehmen wir an, dass der Callback auf die letzte Bot-Nachricht folgt
    reply_text = call.message.text
    ogg_path = text_to_speech.text_to_speech(reply_text, lang=lang)
    with open(ogg_path, "rb") as audio:
        bot.send_voice(call.message.chat.id, audio)
    os.remove(ogg_path)
    bot.answer_callback_query(call.id)

def get_location_from_coordinates(latitude, longitude):
    """
        Function to get location from coordinates
    """
    api_key = "308c9d73d642a0eb49da31de1fefd3ed"
    url = f"http://api.openweathermap.org/geo/1.0/reverse?lat={latitude}&lon={longitude}&limit=1&appid={api_key}"

    try:
        response = requests.get(url)
        response.raise_for_status()

        # parse answer as JSON
        data = response.json()

        # If data is returned, then extract the location
        if data:
            location = data[0]
            city = location.get('name', 'Unbekannt')
            country = location.get('country', 'Unbekannt')
            return f"{city}, {country}"
        else:
            return "Ort konnte nicht gefunden werden."
    except requests.exceptions.RequestException as e:
        print(f"Fehler bei der Anfrage: {e}")
        return "Fehler bei der Abfrage der Geolocation."

@bot.message_handler(content_types=['location', 'venue'])
def handle_location_or_venue(message):
    """
        Function to get location from venue
    """
    if message.content_type == 'venue':
        latitude = message.venue.location.latitude
        longitude = message.venue.location.longitude
    else:
        latitude = message.location.latitude
        longitude = message.location.longitude

    location = get_location_from_coordinates(latitude, longitude)
    response = weather.handle_weather_location(bot, message, location)
    # Standardmäßig Deutsch für Standortantworten
    send_reply_with_tts_button(message, response, "de")

# Function to handle voice messages
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    text, language = speech_to_text.transcribe_voice(bot, message)
    
    if text:
        print(f"Input: {text}, Language: {language}")
        intent = intent_detection.detect_intent(text, language)
        response = None
        if intent == "packing":
            response = packing.handle_packing(bot, message, text, language)
        elif intent == "routine":
            response = routines.handle_routine(bot, message, text, language)
        elif intent == "wardrobe":
            response = wardrobe.handle_wardrobe(bot, message, text, language)
        elif intent == "reminder":
            response = reminder.handle_reminder(bot, message, text, language)
        else:
            if language == "de":
                response = f"Es tut mir leid, ich habe dich nicht verstanden. Ich habe nur verstanden: {text}."
            else:
                response = f"Sorry, I didn't understand your intent, I understood {text}."
        if response:
            send_reply_with_tts_button(message, response, language)
    else:
        bot.reply_to(message, "Sorry, I couldn't understand your voice message.")


# Set the bot commands    
bot.set_my_commands([
    telebot.types.BotCommand("start", "Greetings"),
    telebot.types.BotCommand("routines", "Set Routine"),
    telebot.types.BotCommand("delete_routine", "Delete a Routine"),
    telebot.types.BotCommand("Kleiderschrank", "Bearbeiten des Kleiderschranks"),
    telebot.types.BotCommand("wardrobe", "Manage your wardrobe")
])

# Start the check_reminders thread
threading.Thread(target=reminder.check_reminders, args=(bot,), daemon=True).start()

# Start the bot
bot.infinity_polling()