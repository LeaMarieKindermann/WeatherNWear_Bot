# Modules to import
import telebot

# Custom modules to import
from wnw_bot_api_token import token as api_token
import packing
import routines
import wardrobe
import reminder
import weather

import speech_to_text
import intent_detection

# For asynchronous operations
import threading

# Initialize the bot with the API token
bot = telebot.TeleBot(api_token, parse_mode=None)  # You can set parse_mode by default. HTML or MARKDOWN

## Define a function to send a welcome message
def send_welcome(message):
    first_name = message.from_user.first_name if message.from_user.first_name else ""
    last_name = message.from_user.last_name if message.from_user.last_name else ""
    bot.reply_to(message, f"Welcome, {first_name} {last_name}!")

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
        print(f"User Telegram language_code: {user_lang}")

# Function to interpret the user's intent if it is not a command
@bot.message_handler(content_types=['text'])
def handle_text(message):
    text = message.text
    language = speech_to_text.detect_language(text)
    intent = intent_detection.detect_intent(text, language)
    if intent == "packing":
        packing.handle_packing(bot, message, text, language)
    elif intent == "routine":
        routines.handle_routine(bot, message, text, language)
    elif intent == "wardrobe":
        wardrobe.handle_wardrobe(bot, message, text, language)
    elif intent == "reminder":
        reminder.handle_reminder(bot, message, text, language)
    elif intent == "weather":
        weather.handle_weather(bot, message, text, language)
    else:
        if language == "de":
            bot.reply_to(message, "Es tut mir leid, ich habe dich nicht verstanden. Bitte versuche es erneut.")
        elif language == "en":
            bot.reply_to(message, "Sorry, I didn't understand. Please try again.")

# Function to handle voice messages
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    text, language = speech_to_text.transcribe_voice(bot, message)
    
    if text:
        print(f"Input: {text}, Language: {language}")
        match language:
            case "de":
                intent = intent_detection.detect_intent(text, language)
                # Optional: bot.reply_to(message, f"You said: {text}")
                if intent == "packing":
                    packing.handle_packing(bot, message, text, language)
                elif intent == "routine":
                    routines.handle_routine(bot, message, text, language)
                elif intent == "wardrobe":
                    wardrobe.handle_wardrobe(bot, message, text, language)
                elif intent == "reminder":
                    reminder.handle_reminder(bot, message, text, language)
                else:
                    bot.reply_to(message, f"Es tut mir leid, ich habe dich nicht verstanden. Ich habe nur verstanden: {text}.")
            case "en":
                intent = intent_detection.detect_intent(text, language)
                # Optional: bot.reply_to(message, f"You said: {text}")
                if intent == "packing":
                    packing.handle_packing(bot, message, text, language)
                elif intent == "routine":
                    routines.handle_routine(bot, message, text, language)
                elif intent == "wardrobe":
                    wardrobe.handle_wardrobe(bot, message, text, language)
                elif intent == "reminder":
                    reminder.handle_reminder(bot, message, text, language)
                else:
                    bot.reply_to(message, f"Sorry, I didn't understand your intent, I understood {text}.")
    else:
        bot.reply_to(message, "Sorry, I couldn't understand your voice message.")


# Set the bot commands    
bot.set_my_commands([
    telebot.types.BotCommand("start", "Greetings")
])

# Start the check_reminders thread
threading.Thread(target=reminder.check_reminders, args=(bot,), daemon=True).start()

# Start the bot
bot.infinity_polling()