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

def handle_packing(bot, message, text, language):
    """
    Handle the packing command.
    This function is called when the intend of the user is found to be packing.
    It sends a message providing the forecast at the destination & date AND 
    provides a travel packing list.
    
    -----
    
    Args:
        bot: The telebot instance.
        message: The message object containing user input.
    """
    bot.reply_to(message, "What to Pack? Feature is coming soon.\n")