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
    Handles the packing command. This function is called when the intent of the user is packing.
    It should return a packing list and weather forecast for the destination and date.

    Args:
        bot: The telebot instance.
        message: The message object containing user input.
        text (str): The user's message text.
        language (str): The detected language code ('de' or 'en').
    Returns:
        str: The packing list or a placeholder message.
    """
    print(f"handle_packing called with text: {text}, language: {language}")
    # TODO: Implement packing logic here in the future
    return "What to Pack? Feature is coming soon."