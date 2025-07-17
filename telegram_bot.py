# Modules to import
import re

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
import matplotlib
from PIL import Image, ImageDraw, ImageFont

import speech_to_text
import intent_detection
import text_to_speech
import help_loader
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
    
# Handler for /help command
@bot.message_handler(commands=["help", "hilfe"])
def handle_help(message):
    language = getattr(message.from_user, "language_code", "de")
    lang_key = "de" if language.startswith("de") else "en"
    keyboard = InlineKeyboardMarkup()
    
    # Get main help text from external file
    help_text = help_loader.get_main_help_text(lang_key)
    
    if lang_key == "de":
        keyboard.add(InlineKeyboardButton("👔 Outfit-Empfehlungen", callback_data="help_packing"))
        keyboard.add(InlineKeyboardButton("🗓️ Routinen", callback_data="help_routines"))
        keyboard.add(InlineKeyboardButton("👗 Kleiderschrank", callback_data="help_wardrobe"))
        keyboard.add(InlineKeyboardButton("⏰ Erinnerungen", callback_data="help_reminders"))
        keyboard.add(InlineKeyboardButton("⏰ Wetter", callback_data="help_weather"))
    else:
        keyboard.add(InlineKeyboardButton("👔 Outfit Suggestions", callback_data="help_packing"))
        keyboard.add(InlineKeyboardButton("🗓️ Routines", callback_data="help_routines"))
        keyboard.add(InlineKeyboardButton("👗 Wardrobe", callback_data="help_wardrobe"))
        keyboard.add(InlineKeyboardButton("⏰ Reminders", callback_data="help_reminders"))
        keyboard.add(InlineKeyboardButton("⏰ Weather", callback_data="help_weather"))
    
    bot.send_message(message.chat.id, help_text, reply_markup=keyboard, parse_mode="Markdown")
    
# Function to interpret the user's intent if it is not a command
@bot.message_handler(content_types=['text'])
def handle_text(message):
    text = message.text
    language = speech_to_text.detect_language(text)
    if language is None:
        bot.reply_to(message, "Es tut mir leid, ich kann nur Deutsch oder Englisch verstehen. Bitte versuche es erneut.\n Sorry I can only understand German or English. Please try again.")
        return
    intent = intent_detection.detect_intent(text, language)
    print("Intent: " + str(intent))
    response = None
    if intent == "packing":
        response = packing.handle_packing(bot, message, text, language)
    elif intent == "preference":
        response = packing.handle_preference_feedback(message.chat.id, text, language)
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
    elif intent == "help":
        # Trigger help command
        handle_help(message)
        return
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
        elif intent == "preference":
            response = packing.handle_preference_feedback(message.chat.id, text, language)
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
        elif intent == "help":
            # Trigger help command
            handle_help(message)
            return
        elif intent == "weather":
            response = weather.handle_weather(bot, message, text, language)
        else:
            if language == "de":
                response = f"Es tut mir leid, ich habe dich nicht verstanden. Ich habe nur verstanden: {text}."
            else:
                response = f"Sorry, I didn't understand your intent, I understood {text}."
        if response:
            send_reply_with_tts_button(message, response, language)
    else:
        bot.reply_to(message, "Sorry, I couldn't understand your voice message.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("help_"))
def handle_help_callback(call):
    feature = call.data.split("_")[1]
    language = getattr(call.from_user, "language_code", "de")
    lang_key = "de" if language.startswith("de") else "en"
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    # Get help text from external file
    help_text = help_loader.format_help_text(feature, lang_key)
    
    # Edit the message to show the specific help text
    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=help_text,
            parse_mode="Markdown"
        )
    except Exception as e:
        # If editing fails, send a new message
        bot.send_message(chat_id, help_text, parse_mode="Markdown")
    
    bot.answer_callback_query(call.id)


def get_weather_icon_path(description):
    """
        Gibt den Pfad zum passenden Wettersymbol zurück
    """
    description = description.lower()
    if "sunny" in description or "clear" in description or "sonnig" in description:
        return "assets/icons/sun.png"
    elif "cloudy" in description or "bewölkt" in description:
        return "assets/icons/cloud.png"
    elif "rain" in description or "regenfall" in description:
        return "assets/icons/rain.png"
    elif "snow" in description or "schneefall" in description:
        return "assets/icons/snow.png"
    elif "fog" in description or "nebel" in description:
        return "assets/icons/fog.png"
    elif "drizzle" in description or "nieselregen" in description:
        return "assets/icons/drizzle.png"
    elif "ice pellets" in description or "hagel" in description:
        return "assets/icons/hail.png"
    elif "sleet shower" in description or "graupelschauer" in description:
        return "assets/icons/sleet.png"
    elif "thunder" in description or "gewitter" in description:
        return "assets/icons/thunder.png"
    else:
        return "assets/icons/unknown.png"


@bot.callback_query_handler(func=lambda call: call.data.startswith("weather_chart|"))
def handle_weather_chart_callback(call):
    """
        Handles the callback to generate and send a 3-day weather forecast image for the selected location.

        This function:
        - Fetches weather data for the next 3 days from the API
        - Extracts average temperature and weather description
        - Selects the appropriate weather icons
        - Draws the weather data onto a predefined image template (forecast card)
        - Sends the generated forecast image back to the Telegram chat

        Steps:
        1. Reads the location from callback data
        2. Retrieves weather forecast data for 3 days
        3. Draws temperatures, descriptions, and icons on the image template
        4. Sends the completed image as a photo message
        5. Deletes the temporary image file afterwards

        Args:
            call: The callback query object from the Telegram bot (contains chat/user info)
        """
    location = call.data.split("|", 1)[1]
    try:
        user_lang = call.from_user.language_code
        lang = "de" if user_lang.startswith("de") else "en"

        if lang == "de":
            background_path = "assets/Forecast_de.png"
            days = ["Heute", "Morgen", "Übermorgen"]
            temp_marker = "Ø"
            regex_marker = "Ø"
        else:
            background_path = "assets/Forecast_en.png"
            days = ["Today", "Tomorrow", "Day After Tomorrow"]
            temp_marker = "avg"
            regex_marker = "avg"

        forecast_data = []
        for day in range(3):
            data = weather.get_weather(location, lang, day)
            print(data)
            if data and "text" in data:
                if temp_marker in data['text']:
                    try:
                        parts = data['text'].split(temp_marker)[1].split("°C")[0].strip()
                        avg_temp = float(parts)
                    except:
                        avg_temp = 0.0
                else:
                    avg_temp = 0.0

                pattern = r":\s*(.*?)\,\s*" + re.escape(regex_marker)
                match = re.search(pattern, data['text'])
                if match:
                    desc = match.group(1)
                else:
                    desc = "No data" if lang == "en" else "Keine Daten"

                forecast_data.append({
                    "day": days[day],
                    "temp": avg_temp,
                    "desc": desc
                })
            else:
                forecast_data.append({
                    "day": days[day],
                    "temp": 0,
                    "desc": "No data" if lang == "en" else "Keine Daten"
                })

        # Load the forecast image template
        base_image = Image.open(background_path).convert("RGBA")
        draw = ImageDraw.Draw(base_image)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        font_path_regular = os.path.join(base_dir, "assets", "fonts", "Roboto-Regular.ttf")
        font_path_bold = os.path.join(base_dir, "assets", "fonts", "Roboto-Bold.ttf")

        # Load fonts with desired sizes
        font_large = ImageFont.truetype(font_path_bold, 40)
        font_small = ImageFont.truetype(font_path_regular, 25)

        # Draw weather data onto the template
        card_width = base_image.width // 3
        draw.text((card_width + 70, 50), f"{location}", font=font_large, fill="black")
        for i, forecast in enumerate(forecast_data):
            x_offset = [80, 45, 15]
            icon_offset = [45, 40, 45]
            x = i * card_width + x_offset[i]
            y = 800

            icon_path = get_weather_icon_path(forecast["desc"])
            print("ICON PATH:", icon_path)
            if os.path.exists(icon_path):
                icon = Image.open(icon_path).convert("RGBA").resize((340, 340))
                base_image.paste(icon, (x - icon_offset[i], 340), icon)

            draw.text((x, y), f"{forecast['temp']}°C", font=font_large, fill="black")
            draw.text((x, y + 60), forecast["desc"], font=font_small, fill="black")

        # Save and send the image
        image_path = f"{location}_forecast.png"
        base_image.save(image_path)

        caption = f"📊 Weather Forecast for {location}" if lang == "en" else f"📊 Wetterkarte für {location}"
        with open(image_path, "rb") as photo:
            bot.send_photo(call.message.chat.id, photo, caption=caption)

        os.remove(image_path)
        bot.answer_callback_query(call.id)

    except Exception as e:
        print(f"Fehler beim Generieren der Wettergrafik: {e}")
        bot.answer_callback_query(call.id, text="Fehler beim Erzeugen der Grafik.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_routine|"))
def handle_delete_routine_callback(call):
    try:
        _, chat_id, index, language = call.data.split("|")
        index = int(index)
        user_routines = routines.user_info.get(chat_id, [])

        if 0 <= index < len(user_routines):
            routine = user_routines.pop(index)
            routines.save_user_information(routines.user_info)

            # Scheduler-Job entfernen
            job_id = f"routine_{chat_id}_{routine['city']}_{routine['hour']:02d}_{routine['minute']:02d}"
            if routines.scheduler.get_job(job_id):
                routines.scheduler.remove_job(job_id)

            # Ausgabe
            city = routine["city"]
            time_str = f"{routine['hour']:02d}:{routine['minute']:02d}"

            if language.startswith("de"):
                msg = f"✅ Routine gelöscht: {time_str} Uhr in {city}."
            else:
                msg = f"✅ Routine deleted: {time_str} in {city}."

            bot.edit_message_text(
                msg,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
        else:
            bot.answer_callback_query(call.id, text="Invalid routine number." if language == "en" else "Ungültige Routinenummer.")
    except Exception as e:
        print("Fehler beim Löschen:", e)
        bot.answer_callback_query(call.id, text="Error while deleting." if "en" in call.data else "Fehler beim Löschen.")

# Set the bot commands    
bot.set_my_commands([
    telebot.types.BotCommand("start", "Greetings"),
    telebot.types.BotCommand("help", "Show bot features and examples"),
    telebot.types.BotCommand("routines", "Show all saved routines"),
    telebot.types.BotCommand("kleiderschrank", "Bearbeiten des Kleiderschranks"),
    telebot.types.BotCommand("wardrobe", "Manage your wardrobe")
])

# Start the check_reminders thread
threading.Thread(target=reminder.check_reminders, args=(bot,), daemon=True).start()

# Start the bot
bot.infinity_polling()