from rapidfuzz import fuzz
import re

class IntentDetector:
    """
    Advanced intent detection system with improved accuracy and maintainability.
    Supports multiple detection methods: fuzzy matching, regex patterns, and exact phrases.
    """
    
    def __init__(self):
        self.threshold = 80
        self.intent_config = {
            "de": {
                "preference": {
                    "keywords": ["lieber", "bevorzuge", "anstatt", "statt", "will", "möchte", "hätte gerne"],
                    "patterns": [
                        r"\b(ich\s+)?(möchte|will|würde|hätte)\s+(lieber|gerne)\b",
                        r"\b(anstatt|statt)\s+\w+\b",
                        r"\b(bevorzuge|präferiere)\b",
                        r"\b(lieber\s+\w+)\b"
                    ],
                    "exact_phrases": []
                },
                "packing": {
                    "keywords": ["einpacken", "packen", "mitnehmen", "anziehen", "outfit", "kleidung", 
                               "was soll ich", "empfehlung", "vorschlag", "tragen", "ziehe", "morgen an", "heute an"],
                    "patterns": [
                        r"\b(was\s+soll\s+ich\s+(an)?ziehen|anziehen)\b",
                        r"\b(was\s+zieh(e|st)\s+ich\s+(morgen|heute|übermorgen))\b",
                        r"\b(outfit\s+(für|empfehlung))\b",
                        r"\b(kleider?\s+(empfehlung|vorschlag))\b",
                        r"\b(pack(en?|liste)|mitnehmen)\b",
                        r"\b(reise|urlaub|ausflug)\b.*\b(packen|kleidung|anziehen)\b"
                    ],
                    "exact_phrases": ["outfit", "anziehen"]
                },
                "wardrobe": {
                    "keywords": ["kleiderschrank", "kleidung", "oberteile", "hosen", "jacken", 
                               "schuhe", "accessoires", "zeige", "hinzufügen", "löschen", "entfernen", "füge", "hinzu"],
                    "patterns": [
                        r"\b(zeige?\s+(meinen?\s+)?kleiderschrank)\b",
                        r"\b(füge?\s+(hinzu|dazu|ein))\b",
                        r"\b(hinzufügen|dazufügen)\b",
                        r"\b(lösch(e|en)|entfern(e|en))\b.*\b(kleidung|item)\b",
                        r"\b(mein(e|en)?\s+(oberteile?|hosen?|jacken?|schuhe?))\b",
                        r"\b(was\s+habe\s+ich\s+(für|an))\b"
                    ],
                    "exact_phrases": ["kleiderschrank", "wardrobe"]
                },
                "routine": {
                    "keywords": ["routine", "tagesablauf", "erstelle", "mache", "erstellen", "täglich", "jeden tag", "morgens", "ablauf"],
                    "patterns": [
                        r"\b(mache|erstelle|erstellen)\s+(eine\s+)?routine(\s+für)?\b",
                        r"\broutine\s+(für|um)\s+\w+\s+\d{1,2}[:.]?\d{0,2}",
                        r"\b(jeden\s+tag\s+um\s+\d{1,2}[:.]?\d{0,2})\b",
                        r"\btäglich(e|en)?\s+(nachricht|empfehlung)\b",
                        r"\bmorgens?\s+um\s+\d{1,2}[:.]?\d{0,2}\b.*\b(routine|nachricht)\b",
                    ],
                    "exact_phrases": ["routine"]
                },
                "routine_list": {
                    "keywords": ["alle routinen", "zeige routinen", "liste routinen", "meine routinen", "zeige mir alle routinen", "zeige mir meine routinen"],
                    "patterns": [
                        r"\b(alle\s+routinen|zeige?\s+routinen|liste\s+routinen)\b",
                        r"\b(meine?\s+routinen?)\b"
                    ],
                    "exact_phrases": ["/routines", "routinen liste"]
                },
                "routine_delete": {
                    "keywords": ["routine löschen", "routine entfernen", "lösche routine"],
                    "patterns": [
                        r"\b(lösch(e|en)?\s+routine)\b",
                        r"\b(entfern(e|en)?\s+routine)\b",
                        r"\b(routine\s+(löschen|entfernen))\b"
                    ],
                    "exact_phrases": ["/delete_routine", "routine löschen"]
                },
                "reminder": {
                    "keywords": ["erinnerung", "erinnere", "reminder", "benachrichtigung", "vergessen"],
                    "patterns": [
                        r"\b(erinner(e|ung))\b",
                        r"\b(in\s+\d+\s+(minuten?|stunden?))\b",
                        r"\b(um\s+\d{1,2}:\d{2})\b",
                        r"\b(nicht\s+vergessen)\b",
                        r"\b(benachricht(ige|igung))\b"
                    ],
                    "exact_phrases": ["reminder", "erinnerung"]
                },
                "weather": {
                    "keywords": ["wetter", "regen", "sonne", "schnee", "bewölkt", "temperatur", "grad"],
                    "patterns": [
                        r"\b(wie\s+(ist|wird)\s+das\s+wetter(.*?)?)\b",
                        r"\b(wetter\s+(in|für)\s+\w+)\b",
                        r"\b(wie\s+(wird|ist)\s+das\s+wetter\s+(heute|morgen|übermorgen|am\s+\w+|in\s+\d+\s+tagen?))\b",
                        r"\b(regnet\s+es|schneit\s+es|scheint\s+die\s+sonne)\b",
                        r"\b(grad\s+(celsius|fahrenheit))\b"
                    ],
                    "exact_phrases": ["wetter"]
                },
                "help": {
                    "keywords": ["hilfe", "help", "anleitung", "unterstützung", "erklärung"],
                    "patterns": [
                        r"\b(wie\s+funktioniert|was\s+kann|erkläre|hilf\s+mir)\b",
                        r"\b(bot\s+(hilfe|funktionen|features))\b",
                        r"\b(was\s+kannst\s+du)\b"
                    ],
                    "exact_phrases": ["hilfe", "help", "?", "info"]
                }
            },
            "en": {
                "preference": {
                    "keywords": ["rather", "prefer", "instead", "would like", "want to wear"],
                    "patterns": [
                        r"\b(i\s+)?(would\s+)?(rather|prefer)\b",
                        r"\b(instead\s+of)\b",
                        r"\b(i\s+(want|would\s+like)\s+to\s+wear)\b",
                        r"\b(i\s+prefer)\b"
                    ],
                    "exact_phrases": []
                },
                "packing": {
                    "keywords": ["pack", "packing", "what should i wear", "outfit", "clothes", 
                               "suggestion", "recommendation", "wear"],
                    "patterns": [
                        r"\b(what\s+should\s+i\s+wear)\b",
                        r"\b(outfit\s+(for|recommendation))\b",
                        r"\b(cloth(es|ing)\s+(suggestion|recommendation))\b",
                        r"\b(pack(ing)?|bring|take\s+with)\b",
                        r"\b(trip|travel|vacation)\b.*\b(pack|cloth|wear)\b"
                    ],
                    "exact_phrases": ["outfit", "wear", "clothes"]
                },
                "wardrobe": {
                    "keywords": ["wardrobe", "clothes", "tops", "pants", "jackets", "shoes", 
                               "accessories", "show", "add", "remove", "delete"],
                    "patterns": [
                        r"\b(show\s+(my\s+)?wardrobe)\b",
                        r"\b(add\s+to\s+wardrobe)\b",
                        r"\b(remove|delete)\b.*\b(from\s+wardrobe|cloth)\b",
                        r"\b(my\s+(tops?|pants?|jackets?|shoes?))\b",
                        r"\b(what\s+do\s+i\s+have)\b"
                    ],
                    "exact_phrases": ["wardrobe", "my clothes"]
                },
                "routine": {
                    "keywords": ["routine", "schedule", "create", "daily", "every day", "morning"],
                    "patterns": [
                        r"\b(create\s+(a\s+)?routine)\b",
                        r"\b(daily\s+(message|recommendation))\b",
                        r"\b(every\s+day\s+at)\b",
                        r"\b(routine\s+(at|for))\b",
                        r"\b(morning\s+at)\b.*\b(routine|message)\b"
                    ],
                    "exact_phrases": ["routine", "schedule"]
                },
                "routine_list": {
                    "keywords": ["all routines", "show routines", "list routines", "my routines"],
                    "patterns": [
                        r"\b(all\s+routines|show\s+routines|list\s+routines)\b",
                        r"\b(my\s+routines?)\b"
                    ],
                    "exact_phrases": ["/routines", "routines list"]
                },
                "routine_delete": {
                    "keywords": ["delete routine", "remove routine"],
                    "patterns": [
                        r"\b(delete\s+routine)\b",
                        r"\b(remove\s+routine)\b",
                        r"\b(routine\s+(delete|remove))\b"
                    ],
                    "exact_phrases": ["/delete_routine", "delete routine"]
                },
                "reminder": {
                    "keywords": ["reminder", "remind", "notification", "don't forget"],
                    "patterns": [
                        r"\b(remind(er)?)\b",
                        r"\b(in\s+\d+\s+(minute|hour)s?)\b",
                        r"\b(at\s+\d{1,2}:\d{2})\b",
                        r"\b(don't\s+forget)\b",
                        r"\b(notif(y|ication))\b"
                    ],
                    "exact_phrases": ["reminder", "remind me"]
                },
                "weather": {
                    "keywords": ["weather", "rain", "sun", "snow", "cloudy", "temperature", "degrees"],
                    "patterns": [
                        r"\b(what's\s+the\s+weather)\b",
                        r"\b(whats\s+the\s+weather)\b",
                        r"\b(weather\s+(in|for))\b",
                        r"\b(degrees?\s+(celsius|fahrenheit))\b",
                        r"\b(temperature|degrees?\s+(celsius|fahrenheit)?)\b",
                        r"\b(is\s+it\s+(raining|snowing|sunny))\b",
                        r"\b(will\s+it\s+(rain|snow|be\s+sunny|be\s+cloudy))\b",
                        r"\b(how\s+(is|will)\s+the\s+weather(\s+(be)?)?)\b",
                    ],
                    "exact_phrases": ["weather"]
                },
                "help": {
                    "keywords": ["help", "how", "what can", "explain", "guide", "info"],
                    "patterns": [
                        r"\b(how\s+(do|does|can)|what\s+can\s+you)\b",
                        r"\b(help\s+me)\b",
                        r"\b(bot\s+(help|features|functions))\b",
                        r"\b(explain|guide|info)\b"
                    ],
                    "exact_phrases": ["help", "?", "info"]
                }
            }
        }
    
    def detect_intent(self, text, language):
        """
        Detect user intent using multiple detection methods with priority ordering.
        
        Args:
            text (str): The input text to analyze
            language (str): Language code (e.g., 'de', 'en')
            
        Returns:
            str: Detected intent or None if no match found
        """
        if not text or not text.strip():
            return None
            
        text_lower = text.lower().strip()
        lang_key = "de" if language.startswith("de") else "en"
        
        if lang_key not in self.intent_config:
            return None
        
        # Priority order for intent detection
        intent_priority = [
            "preference",     # Check preferences before packing/wardrobe
            "routine_list",   # Check specific routines before general routine
            "routine_delete", 
            "packing",        # Main functionality
            "wardrobe",
            "routine", 
            "reminder",
            "weather",
            "help"
        ]
        
        # Method 1: Exact phrase matching (highest priority)
        for intent in intent_priority:
            if self._check_exact_phrases(text_lower, intent, lang_key):
                print(f"Exact match found for intent: {intent}")
                return intent
        
        # Method 2: Fuzzy keyword matching (medium priority)
        for intent in intent_priority:
            if self._check_keywords(text_lower, intent, lang_key):
                print(f"Keyword match found for intent: {intent}")
                return intent

        # Method 2: Regex pattern matching (lowest priority)  
        for intent in intent_priority:
            if self._check_patterns(text_lower, intent, lang_key):
                print(f"Pattern match found for intent: {intent}")
                return intent
                
        
        
        return None
    
    def _check_exact_phrases(self, text_lower, intent, lang_key):
        """Check if text matches exact phrases for the given intent."""
        config = self.intent_config[lang_key].get(intent, {})
        exact_phrases = config.get("exact_phrases", [])
        
        return any(phrase.lower() == text_lower for phrase in exact_phrases)
    
    def _check_patterns(self, text_lower, intent, lang_key):
        """Check if text matches regex patterns for the given intent."""
        config = self.intent_config[lang_key].get(intent, {})
        patterns = config.get("patterns", [])
        
        return any(re.search(pattern, text_lower, re.IGNORECASE) for pattern in patterns)
    
    def _check_keywords(self, text_lower, intent, lang_key):
        """Check if text matches keywords using fuzzy matching."""
        config = self.intent_config[lang_key].get(intent, {})
        keywords = config.get("keywords", [])
        
        return any(fuzz.partial_ratio(kw.lower(), text_lower) >= self.threshold for kw in keywords)
    
    def get_intent_confidence(self, text, language):
        """
        Get the confidence score for the detected intent.
        
        Args:
            text (str): The input text
            language (str): Language code
            
        Returns:
            tuple: (intent, confidence_score)
        """
        intent = self.detect_intent(text, language)
        if not intent:
            return None, 0
            
        text_lower = text.lower().strip()
        lang_key = "de" if language.startswith("de") else "en"
        
        # Calculate confidence based on detection method
        if self._check_exact_phrases(text_lower, intent, lang_key):
            return intent, 100
        elif self._check_patterns(text_lower, intent, lang_key):
            return intent, 90
        elif self._check_keywords(text_lower, intent, lang_key):
            # Find best keyword match score
            config = self.intent_config[lang_key].get(intent, {})
            keywords = config.get("keywords", [])
            best_score = max(fuzz.partial_ratio(kw.lower(), text_lower) for kw in keywords)
            return intent, best_score
        
        return intent, 0

# Global instance
_detector = IntentDetector()

def detect_intent(text, language):
    """
    Legacy function for backward compatibility.
    Detects the intent of the given text.

    Args:
        text (str): The input text to analyze.
        language (str): The language of the input text.
        
    Returns:
        str: The detected intent.
    """
    return _detector.detect_intent(text, language)

def get_intent_confidence(text, language):
    """
    Get the confidence score for the detected intent.
    
    Args:
        text (str): The input text
        language (str): Language code
        
    Returns:
        tuple: (intent, confidence_score)
    """
    return _detector.get_intent_confidence(text, language)