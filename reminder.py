# Use spaCy for language processing https://spacy.io/
import spacy 
# Load the language models for German and English
nlp_de = spacy.load("de_core_news_sm") # python -m spacy download de_core_news_sm to install the German model
nlp_en = spacy.load("en_core_web_sm") # python -m spacy download en_core_web_sm to install the English model

'''
Extracts reminder information from the given text.
This function uses spaCy to identify time expressions and the reason for the reminder.

----

Args:
    text (str): The input text containing the reminder information.
    language (str): The language of the input text, either "de" for German or "en" for English.
'''
def extract_reminder_info(text, language):
    # Choose the right model
    nlp = nlp_de if language == "de" else nlp_en
    doc = nlp(text)

    # Find time expressions (entities of type TIME or DATE)
    times = [ent.text for ent in doc.ents if ent.label_ in ("TIME", "DATE")]

    # Try to find the "reminder reason" (everything after "an", "daran", "remind me to", etc.)
    if language == "de":
        # Simple heuristic: everything after "an" or "daran"
        import re
        match = re.search(r"(?:an|daran|erinnere mich an)\s+(.+)", text, re.IGNORECASE)
        what = match.group(1) if match else text
    else:
        # Everything after "remind me to/about"
        import re
        match = re.search(r"(?:remind me to|remind me about)\s+(.+)", text, re.IGNORECASE)
        what = match.group(1) if match else text

    # Use the first found time, if any
    time_str = times[0] if times else None
    return time_str, what

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
    if not what or what.strip() == "":
        if language == "de":
            bot.reply_to(message, "Bitte gib an, woran ich dich erinnern soll.")
        else:
            bot.reply_to(message, "Please specify what I should remind you about.")
        return
    if time_str:
        if language == "de":
            bot.reply_to(message, f"Okay, ich werde dich um {time_str} daran erinnern, {what}")
        else:
            bot.reply_to(message, f"Okay, I will remind you at {time_str} to {what}")
    else:
        if language == "de":
            bot.reply_to(message, "Bitte gib eine Uhrzeit an, wann ich dich erinnern soll.")
        else:
            bot.reply_to(message, "Please specify a time when I should remind you.")