from rapidfuzz import fuzz

"""
Detects the intent of the given text.

Args:
    text (str): The input text to analyze.
    language (str): The language of the input text.
    
Returns:
    str: The detected intent.
"""
def detect_intent(text, language):
    text = text.lower()
    # Define keywords for each intent and language
    packing_de = ["packen", "einpacken", "reise", "koffer", "mitnehmen", "urlaub", "was soll ich mitnehmen"]
    routine_de = ["erstelle eine routine", "jeden morgen", "täglich", "immer um", "zeitplan", "morgens", "erstelle mir eine Routine", "erstelle"]
    routine_show_de = ["meine routinen", "zeige meine routinen", "welche routinen", "routine anzeigen", "zeig mir alle Routinen"]
    routine_delete_de = ["routine löschen", "routine entfernen", "lösche routine"]
    wardrobe_de = ["anziehen", "kleidung", "outfit", "was soll ich anziehen", "kleiderwahl"]
    reminder_de = ["erinnerung", "erinnere", "nicht vergessen", "denk daran", "benachrichtige"]
    weather_de = ["wetter", "wie ist das wetter", "regen", "sonnig", "vorhersage", "wie wird das wetter", "sag mir das wetter"]

    packing_en = ["pack", "packing", "trip", "suitcase", "take with me", "travel", "what should I pack"]
    routine_en = ["create a routine", "every morning", "daily", "always at", "schedule", "morning"]
    routine_show_en = ["my routines", "show routines", "what routines", "list routines", "show me all routines", "show all routines", "can you show me my routines", "show me my routines"]
    routine_delete_en = ["delete routine", "remove routine", "clear routine"]
    wardrobe_en = ["wear", "clothes", "outfit", "what should I wear", "wardrobe"]
    reminder_en = ["reminder", "remind", "don't forget", "remember", "notify"]
    weather_en = ["weather", "how is the weather", "forecast", "raining", "sunny", "what is the weather like", "Whats the weather like"]

    # Helper function: fuzzy match for similar words
    def fuzzy_match(text, keywords, threshold=90):
        return any(fuzz.partial_ratio(text, word) > threshold for word in keywords)

    # Dictionary for all intents and their keywords per language
    intent_keywords = {
        "packing": {"de": packing_de, "en": packing_en},
        "routine": {"de": routine_de, "en": routine_en},
        "routine_list": {"de": routine_show_de, "en": routine_show_en},
        "routine_delete": {"de": routine_delete_de, "en": routine_delete_en},
        "wardrobe": {"de": wardrobe_de, "en": wardrobe_en},
        "reminder": {"de": reminder_de, "en": reminder_en},
        "weather": {"de": weather_de, "en": weather_en},
    }

    # Try to match intent using the detected language
    def match_intent(text, language):
        for intent, langs in intent_keywords.items():
            keywords = langs.get(language)
            if keywords and fuzzy_match(text, keywords):
                return intent
        return None

    detected_intent = match_intent(text, language)
    if detected_intent:
        return detected_intent

    # Fallback: try to match using all keywords (both languages)
    for intent, langs in intent_keywords.items():
        keywords = langs["de"] + langs["en"]
        if fuzzy_match(text, keywords):
            return intent

    # If nothing matches, return None
    return None