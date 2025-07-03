import os
import json
import spacy
from rapidfuzz import fuzz

# Load both spaCy models for NLP (German and English supported)
nlp_de = spacy.load("de_core_news_sm")  # python -m spacy download de_core_news_sm to install the German model
nlp_en = spacy.load("en_core_web_sm")   # python -m spacy download en_core_web_sm to install the English model

WARDROBE_PATH = "wardrobe.json"

# Default wardrobe for German users
# Priority scale is 1 (highest) to 5 (lowest)

def get_default_wardrobe_de():
    return {
        "Oberteile": [
            {"name": "Pullover", "min_temp": -20, "max_temp": 18, "prio": 1, "weather": ["any"]},
            {"name": "Sweatshirt", "min_temp": -10, "max_temp": 20, "prio": 2, "weather": ["any"]},
            {"name": "Hoodie", "min_temp": -5, "max_temp": 22, "prio": 3, "weather": ["any"]},
            {"name": "Hemd", "min_temp": 5, "max_temp": 25, "prio": 4, "weather": ["any"]},
            {"name": "T-Shirt", "min_temp": 10, "max_temp": 40, "prio": 5, "weather": ["sunny", "cloudy"]},
            {"name": "Langarmshirt", "min_temp": 0, "max_temp": 20, "prio": 6, "weather": ["any"]},
            {"name": "Polo-Shirt", "min_temp": 12, "max_temp": 30, "prio": 7, "weather": ["sunny"]},
            {"name": "Tank Top", "min_temp": 20, "max_temp": 45, "prio": 8, "weather": ["sunny"]},
            {"name": "Bluse", "min_temp": 8, "max_temp": 28, "prio": 9, "weather": ["any"]},
            {"name": "Cardigan", "min_temp": -5, "max_temp": 15, "prio": 10, "weather": ["any"]}
        ],
        "Hosen": [
            {"name": "Jeans", "min_temp": -20, "max_temp": 25, "prio": 1, "weather": ["any"]},
            {"name": "Jogginghose", "min_temp": -5, "max_temp": 20, "prio": 2, "weather": ["cloudy"]},
            {"name": "Shorts", "min_temp": 18, "max_temp": 40, "prio": 3, "weather": ["sunny"]},
            {"name": "Chinos", "min_temp": 0, "max_temp": 30, "prio": 4, "weather": ["any"]},
            {"name": "Leggings", "min_temp": -10, "max_temp": 25, "prio": 5, "weather": ["any"]},
            {"name": "Cargo Hose", "min_temp": -5, "max_temp": 25, "prio": 6, "weather": ["any"]},
            {"name": "Stoffhose", "min_temp": 5, "max_temp": 28, "prio": 7, "weather": ["any"]},
            {"name": "Bermuda Shorts", "min_temp": 15, "max_temp": 35, "prio": 8, "weather": ["sunny"]},
            {"name": "Thermohose", "min_temp": -25, "max_temp": 5, "prio": 9, "weather": ["snow"]},
            {"name": "Rock", "min_temp": 10, "max_temp": 35, "prio": 10, "weather": ["sunny", "cloudy"]}
        ],
        "Jacken": [
            {"name": "Winterjacke", "min_temp": -25, "max_temp": 5, "prio": 1, "weather": ["snow", "cloudy"]},
            {"name": "Mantel", "min_temp": -20, "max_temp": 10, "prio": 2, "weather": ["cloudy", "rain"]},
            {"name": "Regenjacke", "min_temp": 0, "max_temp": 20, "prio": 3, "weather": ["rain"]},
            {"name": "Übergangsjacke", "min_temp": -5, "max_temp": 15, "prio": 4, "weather": ["cloudy"]},
            {"name": "Lederjacke", "min_temp": 5, "max_temp": 20, "prio": 5, "weather": ["any"]},
            {"name": "Jeansjacke", "min_temp": 8, "max_temp": 22, "prio": 6, "weather": ["any"]},
            {"name": "Bomberjacke", "min_temp": 3, "max_temp": 18, "prio": 7, "weather": ["any"]},
            {"name": "Weste", "min_temp": 0, "max_temp": 12, "prio": 8, "weather": ["any"]},
            {"name": "Fleecejacke", "min_temp": -10, "max_temp": 10, "prio": 9, "weather": ["any"]},
            {"name": "Softshell", "min_temp": -5, "max_temp": 15, "prio": 10, "weather": ["cloudy", "rain"]}
        ],
        "Schuhe": [
            {"name": "Winterstiefel", "min_temp": -25, "max_temp": 5, "prio": 1, "weather": ["snow"]},
            {"name": "Sneaker", "min_temp": 5, "max_temp": 30, "prio": 2, "weather": ["any"]},
            {"name": "Halbschuhe", "min_temp": 0, "max_temp": 25, "prio": 3, "weather": ["any"]},
            {"name": "Sandalen", "min_temp": 18, "max_temp": 40, "prio": 4, "weather": ["sunny"]},
            {"name": "Gummistiefel", "min_temp": -5, "max_temp": 20, "prio": 5, "weather": ["rain"]},
            {"name": "Laufschuhe", "min_temp": -5, "max_temp": 35, "prio": 6, "weather": ["any"]},
            {"name": "Boots", "min_temp": -15, "max_temp": 15, "prio": 7, "weather": ["any"]},
            {"name": "Flip-Flops", "min_temp": 22, "max_temp": 45, "prio": 8, "weather": ["sunny"]},
            {"name": "Businessschuhe", "min_temp": -5, "max_temp": 30, "prio": 9, "weather": ["any"]},
            {"name": "Hausschuhe", "min_temp": -10, "max_temp": 25, "prio": 10, "weather": ["any"]}
        ],
        "Accessoires": [
            {"name": "Wintermütze", "min_temp": -25, "max_temp": 5, "prio": 1, "weather": ["snow", "cloudy"]},
            {"name": "Schal", "min_temp": -20, "max_temp": 10, "prio": 2, "weather": ["snow", "cloudy"]},
            {"name": "Handschuhe", "min_temp": -20, "max_temp": 8, "prio": 3, "weather": ["snow", "cloudy"]},
            {"name": "Sonnenbrille", "min_temp": 10, "max_temp": 45, "prio": 4, "weather": ["sunny"]},
            {"name": "Gürtel", "min_temp": -20, "max_temp": 40, "prio": 5, "weather": ["any"]},
            {"name": "Regenschirm", "min_temp": -5, "max_temp": 30, "prio": 6, "weather": ["rain"]},
            {"name": "Baseballcap", "min_temp": 8, "max_temp": 35, "prio": 7, "weather": ["sunny"]},
            {"name": "Stirnband", "min_temp": -10, "max_temp": 15, "prio": 8, "weather": ["any"]},
            {"name": "Uhr", "min_temp": -20, "max_temp": 40, "prio": 9, "weather": ["any"]},
            {"name": "Rucksack", "min_temp": -20, "max_temp": 40, "prio": 10, "weather": ["any"]}
        ]
    }

# Default wardrobe for English users
# Priority scale is 1 (highest) to 5 (lowest)

def get_default_wardrobe_en():
    return {
        "Tops": [
            {"name": "Sweater", "min_temp": -20, "max_temp": 18, "prio": 1, "weather": ["any"]},
            {"name": "Hoodie", "min_temp": -10, "max_temp": 20, "prio": 2, "weather": ["any"]},
            {"name": "Sweatshirt", "min_temp": -5, "max_temp": 22, "prio": 3, "weather": ["any"]},
            {"name": "Shirt", "min_temp": 5, "max_temp": 25, "prio": 4, "weather": ["any"]},
            {"name": "T-shirt", "min_temp": 10, "max_temp": 40, "prio": 5, "weather": ["sunny", "cloudy"]},
            {"name": "Long sleeve", "min_temp": 0, "max_temp": 20, "prio": 6, "weather": ["any"]},
            {"name": "Polo shirt", "min_temp": 12, "max_temp": 30, "prio": 7, "weather": ["sunny"]},
            {"name": "Tank top", "min_temp": 20, "max_temp": 45, "prio": 8, "weather": ["sunny"]},
            {"name": "Blouse", "min_temp": 8, "max_temp": 28, "prio": 9, "weather": ["any"]},
            {"name": "Cardigan", "min_temp": -5, "max_temp": 15, "prio": 10, "weather": ["any"]}
        ],
        "Pants": [
            {"name": "Jeans", "min_temp": -20, "max_temp": 25, "prio": 1, "weather": ["any"]},
            {"name": "Sweatpants", "min_temp": -5, "max_temp": 20, "prio": 2, "weather": ["cloudy"]},
            {"name": "Shorts", "min_temp": 18, "max_temp": 40, "prio": 3, "weather": ["sunny"]},
            {"name": "Chinos", "min_temp": 0, "max_temp": 30, "prio": 4, "weather": ["any"]},
            {"name": "Leggings", "min_temp": -10, "max_temp": 25, "prio": 5, "weather": ["any"]},
            {"name": "Cargo pants", "min_temp": -5, "max_temp": 25, "prio": 6, "weather": ["any"]},
            {"name": "Dress pants", "min_temp": 5, "max_temp": 28, "prio": 7, "weather": ["any"]},
            {"name": "Bermuda shorts", "min_temp": 15, "max_temp": 35, "prio": 8, "weather": ["sunny"]},
            {"name": "Thermal pants", "min_temp": -25, "max_temp": 5, "prio": 9, "weather": ["snow"]},
            {"name": "Skirt", "min_temp": 10, "max_temp": 35, "prio": 10, "weather": ["sunny", "cloudy"]}
        ],
        "Jackets": [
            {"name": "Winter jacket", "min_temp": -25, "max_temp": 5, "prio": 1, "weather": ["snow", "cloudy"]},
            {"name": "Coat", "min_temp": -20, "max_temp": 10, "prio": 2, "weather": ["cloudy", "rain"]},
            {"name": "Rain jacket", "min_temp": 0, "max_temp": 20, "prio": 3, "weather": ["rain"]},
            {"name": "Spring jacket", "min_temp": -5, "max_temp": 15, "prio": 4, "weather": ["cloudy"]},
            {"name": "Leather jacket", "min_temp": 5, "max_temp": 20, "prio": 5, "weather": ["any"]},
            {"name": "Denim jacket", "min_temp": 8, "max_temp": 22, "prio": 6, "weather": ["any"]},
            {"name": "Bomber jacket", "min_temp": 3, "max_temp": 18, "prio": 7, "weather": ["any"]},
            {"name": "Vest", "min_temp": 0, "max_temp": 12, "prio": 8, "weather": ["any"]},
            {"name": "Fleece jacket", "min_temp": -10, "max_temp": 10, "prio": 9, "weather": ["any"]},
            {"name": "Softshell", "min_temp": -5, "max_temp": 15, "prio": 10, "weather": ["cloudy", "rain"]}
        ],
        "Shoes": [
            {"name": "Winter boots", "min_temp": -25, "max_temp": 5, "prio": 1, "weather": ["snow"]},
            {"name": "Sneakers", "min_temp": 5, "max_temp": 30, "prio": 2, "weather": ["any"]},
            {"name": "Dress shoes", "min_temp": 0, "max_temp": 25, "prio": 3, "weather": ["any"]},
            {"name": "Sandals", "min_temp": 18, "max_temp": 40, "prio": 4, "weather": ["sunny"]},
            {"name": "Rain boots", "min_temp": -5, "max_temp": 20, "prio": 5, "weather": ["rain"]},
            {"name": "Running shoes", "min_temp": -5, "max_temp": 35, "prio": 6, "weather": ["any"]},
            {"name": "Boots", "min_temp": -15, "max_temp": 15, "prio": 7, "weather": ["any"]},
            {"name": "Flip-flops", "min_temp": 22, "max_temp": 45, "prio": 8, "weather": ["sunny"]},
            {"name": "Loafers", "min_temp": -5, "max_temp": 30, "prio": 9, "weather": ["any"]},
            {"name": "Slippers", "min_temp": -10, "max_temp": 25, "prio": 10, "weather": ["any"]}
        ],
        "Accessories": [
            {"name": "Winter hat", "min_temp": -25, "max_temp": 5, "prio": 1, "weather": ["snow", "cloudy"]},
            {"name": "Scarf", "min_temp": -20, "max_temp": 10, "prio": 2, "weather": ["snow", "cloudy"]},
            {"name": "Gloves", "min_temp": -20, "max_temp": 8, "prio": 3, "weather": ["snow", "cloudy"]},
            {"name": "Sunglasses", "min_temp": 10, "max_temp": 45, "prio": 4, "weather": ["sunny"]},
            {"name": "Belt", "min_temp": -20, "max_temp": 40, "prio": 5, "weather": ["any"]},
            {"name": "Umbrella", "min_temp": -5, "max_temp": 30, "prio": 6, "weather": ["rain"]},
            {"name": "Baseball cap", "min_temp": 8, "max_temp": 35, "prio": 7, "weather": ["sunny"]},
            {"name": "Headband", "min_temp": -10, "max_temp": 15, "prio": 8, "weather": ["any"]},
            {"name": "Watch", "min_temp": -20, "max_temp": 40, "prio": 9, "weather": ["any"]},
            {"name": "Backpack", "min_temp": -20, "max_temp": 40, "prio": 10, "weather": ["any"]}
        ]
    }

# Returns the default wardrobe for the given language ("de" or "en")
def get_default_wardrobe(language="de"):
    if language.lower().startswith("en"):
        return get_default_wardrobe_en()
    else:
        return get_default_wardrobe_de()

"""
Load the wardrobe.json file or create it if it does not exist.
Returns the wardrobe data as a dictionary.
"""
def load_wardrobe():
    if not os.path.exists(WARDROBE_PATH):
        with open(WARDROBE_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f)
    with open(WARDROBE_PATH, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            return {}
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {}

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
def get_or_create_user_wardrobe(chat_id, language="de"):
    data = load_wardrobe()
    chat_id_str = str(chat_id)
    # Create a new wardrobe for the user if not present
    if chat_id_str not in data:
        data[chat_id_str] = [get_default_wardrobe(language)]
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

def add_clothing(chat_id, category, item, fuzzy_threshold=90, min_temp=10, max_temp=25, prio=3, weather="any"):
    if not category:
        return False, None  # Category is required
    data, user_wardrobe = get_or_create_user_wardrobe(chat_id)
    existing_items = user_wardrobe.get(category, [])
    for i in existing_items:
        name = i["name"] if isinstance(i, dict) else i
        if fuzzy_threshold >= 100:
            # Exact match (case-insensitive)
            if item.lower() == name.lower():
                return False, name  # Already exists (exact match)
        else:
            score = fuzz.partial_ratio(item.lower(), name.lower())
            if score >= fuzzy_threshold:
                return False, name  # Already exists (fuzzy match)
    # Add as dict if default wardrobe uses dicts
    if existing_items and isinstance(existing_items[0], dict):
        user_wardrobe.setdefault(category, []).append({"name": item, "min_temp": min_temp, "max_temp": max_temp, "prio": prio, "weather": weather})
    else:
        user_wardrobe.setdefault(category, []).append(item)
    data[str(chat_id)] = [user_wardrobe]
    save_wardrobe(data)
    return True, item

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
def remove_clothing(chat_id, category, item, fuzzy_threshold=90):
    if not category:
        return False, None  # Category is required
    data, user_wardrobe = get_or_create_user_wardrobe(chat_id)
    found = False
    found_name = None
    for i in user_wardrobe.get(category, [])[:]:
        name = i["name"] if isinstance(i, dict) else i
        if fuzzy_threshold >= 100:
            # Exact match (case-insensitive)
            if item.lower() == name.lower():
                user_wardrobe[category].remove(i)
                found = True
                found_name = name
                break
        else:
            score = fuzz.partial_ratio(item.lower(), name.lower())
            if score >= fuzzy_threshold:
                user_wardrobe[category].remove(i)
                found = True
                found_name = name
                break
    if found:
        data[str(chat_id)] = [user_wardrobe]
        save_wardrobe(data)
        return True, found_name
    return False, None

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
    # Get the current default wardrobe structure for categories and items
    default_wardrobe = get_default_wardrobe(language)
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

    # Fuzzy matching helpers
    def fuzzy_find_best(query, choices, threshold=90):
        best = None
        best_score = threshold
        for c in choices:
            score = fuzz.partial_ratio(query, c.lower())
            if score > best_score:
                best = c
                best_score = score
        return best

    # Try to extract item and category using fuzzy matching
    item = None
    category = None
    # Fuzzy match for category
    category = fuzzy_find_best(text_lower, [cat.lower() for cat in default_wardrobe.keys()])
    if category:
        for cat in default_wardrobe.keys():
            if cat.lower() == category:
                category = cat
                break
    # Fuzzy match for item
    all_items = []
    for items in default_wardrobe.values():
        for i in items:
            name = i["name"] if isinstance(i, dict) else i
            all_items.append(name)
    item = fuzzy_find_best(text_lower, [i.lower() for i in all_items])
    if item:
        for i in all_items:
            if i.lower() == item:
                item = i
                break
    # If category is still None but item is found, try to infer category by best fuzzy match of item in all categories
    if not category and item:
        best_cat = None
        best_score = 85
        for cat, items in default_wardrobe.items():
            for i in items:
                name = i["name"] if isinstance(i, dict) else i
                score = fuzz.partial_ratio(item.lower(), name.lower())
                if score > best_score:
                    best_cat = cat
                    best_score = score
        if best_cat:
            category = best_cat
    # Try to extract new items (not in default) for add/remove
    if intent in ["add", "remove"] and not item:
        for token in doc:
            if token.pos_ == "NOUN" and fuzzy_find_best(token.text.lower(), [c.lower() for c in default_wardrobe.keys()]) is None:
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

    # Message templates for English and German
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

    # Full decision structure for all intents
    if intent == "add":
        if not category or not item:
            return msg_not_found
        added, match_name = add_clothing(chat_id, category, item)
        if added:
            return msg_added
        else:
            return f"{match_name} ist bereits in deiner Kategorie {category}." if language.lower().startswith("de") else f"{match_name} is already in your {category}."
    elif intent == "remove":
        if not category or not item:
            return msg_not_in_cat
        removed, match_name = remove_clothing(chat_id, category, item)
        if removed:
            return msg_removed.replace(item, match_name)
        else:
            return f"{item} wurde nicht in deiner Kategorie {category} gefunden." if language.lower().startswith("de") else f"{item} was not found in your {category}."
    elif intent == "missing":
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
                return msg_suggest.format(alts=", ".join(alternatives))
            else:
                return msg_no_alts
        else:
            return msg_no_item
    elif intent == "show":
        _, user_wardrobe = get_or_create_user_wardrobe(chat_id)
        lines = []
        for cat, items in user_wardrobe.items():
            lines.append(f"{cat}: {', '.join(i['name'] if isinstance(i, dict) else i for i in items)}")
        return msg_wardrobe + "\n".join(lines)
    else:
        return f"Wardrobe-Feature: Anfrage erhalten. (Intent: {intent}, Kategorie: {category}, Item: {item})"

def find_item_in_wardrobe(user_wardrobe, item):
    """
    Returns (category, name) if item exists in any category, else (None, None).
    """
    for cat, items in user_wardrobe.items():
        for i in items:
            name = i["name"] if isinstance(i, dict) else i
            if item.lower() == name.lower():
                return cat, name
    return None, None

def remove_item_from_all_categories(chat_id, item):
    """
    Removes the item from all categories for the user. Returns (True, category) if found and removed, else (False, None).
    """
    data, user_wardrobe = get_or_create_user_wardrobe(chat_id)
    for cat, items in user_wardrobe.items():
        for i in items:
            name = i["name"] if isinstance(i, dict) else i
            if item.lower() == name.lower():
                remove_clothing(chat_id, cat, item, fuzzy_threshold=100)
                return True, cat
    return False, None