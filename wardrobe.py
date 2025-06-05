import os
import json
import spacy

# Load both spaCy models for NLP (German and English supported)
nlp_de = spacy.load("de_core_news_sm")  # python -m spacy download de_core_news_sm to install the German model
nlp_en = spacy.load("en_core_web_sm")   # python -m spacy download en_core_web_sm to install the English model

WARDROBE_PATH = "wardrobe.json"

# Default wardrobe (gender-neutral)
DEFAULT_WARDROBE = {
    "Oberteile": ["T-Shirt", "Pullover", "Hemd", "Sweatshirt"],
    "Hosen": ["Jeans", "Jogginghose", "Shorts"],
    "Jacken": ["Jacke", "Mantel", "Regenjacke"],
    "Schuhe": ["Sneaker", "Stiefel"],
    "Accessoires": ["Mütze", "Schal"]
}

"""
Load the wardrobe.json file or create it if it does not exist.
Returns the wardrobe data as a dictionary.
"""
def load_wardrobe():
    if not os.path.exists(WARDROBE_PATH):
        with open(WARDROBE_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f)
    with open(WARDROBE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

"""
Save the wardrobe data to wardrobe.json.

----

Args:
    data: The complete wardrobe dictionary to save.
"""
def save_wardrobe(data):
    with open(WARDROBE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


"""
Get the wardrobe for a user or create a new one with the default wardrobe.
Returns the wardrobe data for all users and the user's wardrobe (dict).

----

Args:
    chat_id: The chat id of the user.
"""
def get_or_create_user_wardrobe(chat_id):
    data = load_wardrobe()
    chat_id_str = str(chat_id)
    # Create a new wardrobe for the user if not present
    if chat_id_str not in data:
        data[chat_id_str] = [DEFAULT_WARDROBE.copy()]
        save_wardrobe(data)
    return data, data[chat_id_str][0]

"""
Add a clothing item to the user's wardrobe.

----

Args:
    chat_id: The chat id of the user.
    category: The category to which the item should be added.
    item: The clothing item to add.
Returns:
    True if the item was added, False if it already exists.
"""
def add_clothing(chat_id, category, item):
    data, user_wardrobe = get_or_create_user_wardrobe(chat_id)
    if item not in user_wardrobe.get(category, []):
        user_wardrobe.setdefault(category, []).append(item)
        data[str(chat_id)] = [user_wardrobe]
        save_wardrobe(data)
        return True
    return False


"""
Remove a clothing item from the user's wardrobe.

----

Args:
    chat_id: The chat id of the user.
    category: The category from which the item should be removed.
    item: The clothing item to remove.
Returns:
    True if the item was removed, False if it was not found.
"""
def remove_clothing(chat_id, category, item):
    data, user_wardrobe = get_or_create_user_wardrobe(chat_id)
    if item in user_wardrobe.get(category, []):
        user_wardrobe[category].remove(item)
        data[str(chat_id)] = [user_wardrobe]
        save_wardrobe(data)
        return True
    return False

"""
Suggest alternative clothing items from the same category.

----

Args:
    chat_id: The chat id of the user.
    category: The category to search for alternatives.
    exclude_item: The item to exclude from suggestions.
Returns:
    A list of alternative items, or None if none are available.
"""
def suggest_alternative(chat_id, category, exclude_item):
    _, user_wardrobe = get_or_create_user_wardrobe(chat_id)
    alternatives = [i for i in user_wardrobe.get(category, []) if i != exclude_item]
    return alternatives if alternatives else None


"""
Use spaCy to extract intent and entities (category, item) from the user's message.
Returns a dict: {'intent': ..., 'category': ..., 'item': ...}

----

Args:
    text: The user's message as a string.
    language: The language code ("de" or "en").
"""
def extract_intent_and_entities(text, language="de"):
    # Select the appropriate spaCy model based on language
    if language.lower().startswith("de"):
        nlp = nlp_de
    else:
        nlp = nlp_en
    doc = nlp(text)
    text_lower = text.lower()
    # Detect intent based on keywords
    if language.lower().startswith("de"):
        if any(kw in text_lower for kw in ["habe kein", "habe nicht", "besitze nicht"]):
            intent = "missing"
        elif any(kw in text_lower for kw in ["hinzufügen"]):
            intent = "add"
        elif any(kw in text_lower for kw in ["entfernen", "löschen"]):
            intent = "remove"
        else:
            intent = "show"
    else:
        if any(kw in text_lower for kw in ["don't have", "do not have"]):
            intent = "missing"
        elif any(kw in text_lower for kw in ["add"]):
            intent = "add"
        elif any(kw in text_lower for kw in ["remove"]):
            intent = "remove"
        else:
            intent = "show"

    # Try to extract item and category using noun chunks and known lists
    item = None
    category = None
    for chunk in doc.noun_chunks:
        for cat in DEFAULT_WARDROBE.keys():
            if cat.lower() in chunk.text.lower():
                category = cat
        # If not a category, maybe it's an item
        if not category:
            for items in DEFAULT_WARDROBE.values():
                for i in items:
                    if i.lower() in chunk.text.lower():
                        item = i
    # Fallback: look for known items/categories in the text
    if not category:
        for cat in DEFAULT_WARDROBE.keys():
            if cat.lower() in text_lower:
                category = cat
    if not item:
        for items in DEFAULT_WARDROBE.values():
            for i in items:
                if i.lower() in text_lower:
                    item = i
    # Try to extract new items (not in default) for add/remove
    if intent in ["add", "remove"] and not item:
        # Assume the first noun not matching a category is the item
        for token in doc:
            if token.pos_ == "NOUN" and token.text.lower() not in [c.lower() for c in DEFAULT_WARDROBE.keys()]:
                item = token.text
                break
    return {"intent": intent, "category": category, "item": item}


"""
Handle the wardrobe command.
This function is called when the intent of the user is found to be wardrobe.
It sends a message providing a list of clothing items and their details.
It adjusts the recommended clothing based on the weather and occasion, as well as on available clothing items.

----

Args:
    bot: The telebot instance.
    message: The message object containing user input.
    text: The user's message as a string.
    language: The language code ("de" or "en").
"""
def handle_wardrobe(bot, message, text, language):
    chat_id = message.chat.id
    parsed = extract_intent_and_entities(text, language)
    intent = parsed["intent"]
    category = parsed["category"]
    item = parsed["item"]
    print(f"Intent: {intent}, Category: {category}, Item: {item}")

    # Message templates for English and German (comments in English only)
    if language.lower().startswith("de"):
        msg_no_item = f"Du hast {item} nicht."
        msg_suggest = "Wie wäre es stattdessen mit: {alts}?"
        msg_no_alts = f"Du hast {item} nicht und es gibt keine Alternativen in {category}. Möchtest du ein neues Kleidungsstück hinzufügen?"
        msg_not_found = f"{item} wurde nicht in deinem Kleiderschrank gefunden."
        msg_added = f"{item} wurde zu {category} hinzugefügt."
        msg_already = f"{item} ist bereits in deiner Kategorie {category}."
        msg_removed = f"{item} wurde aus {category} entfernt."
        msg_not_in_cat = f"{item} wurde nicht in deiner Kategorie {category} gefunden."
        msg_wardrobe = "Dein Kleiderschrank enthält:\n"
    else:
        msg_no_item = f"You don't have {item}."
        msg_suggest = "How about: {alts}?"
        msg_no_alts = f"You don't have {item} and there are no alternatives in {category}. Would you like to add a new item?"
        msg_not_found = f"{item} was not found in your wardrobe."
        msg_added = f"{item} was added to {category}."
        msg_already = f"{item} is already in your {category}."
        msg_removed = f"{item} was removed from {category}."
        msg_not_in_cat = f"{item} was not found in your {category}."
        msg_wardrobe = "Your wardrobe contains:\n"

    # Handle the case where the user does not have a suggested item
    if intent == "missing" and item:
        if not category:
            _, user_wardrobe = get_or_create_user_wardrobe(chat_id)
            for cat, items in user_wardrobe.items():
                if item in items:
                    category = cat
                    break
        if category:
            remove_clothing(chat_id, category, item)
            alternatives = suggest_alternative(chat_id, category, item)
            if alternatives:
                alternatives_str = ", ".join(alternatives)
                reply = f"{msg_no_item} {msg_suggest.format(alts=alternatives_str)}"
                bot.reply_to(message, reply)
            else:
                bot.reply_to(message, msg_no_alts)
        else:
            bot.reply_to(message, msg_not_found)

    # Handle the case where the user wants to add a new item
    elif intent == "add" and category and item:
        if add_clothing(chat_id, category, item):
            bot.reply_to(message, msg_added)
        else:
            bot.reply_to(message, msg_already)

    # Handle the case where the user wants to remove an item
    elif intent == "remove" and category and item:
        if remove_clothing(chat_id, category, item):
            bot.reply_to(message, msg_removed)
        else:
            bot.reply_to(message, msg_not_in_cat)

    # Show the current wardrobe if no specific action is detected
    else:
        _, user_wardrobe = get_or_create_user_wardrobe(chat_id)
        response = msg_wardrobe
        for cat, items in user_wardrobe.items():
            response += f"{cat}: {', '.join(items)}\n"
        bot.reply_to(message, response)