def detect_intent(text, language):
    """
    Detects the intent of the given text.
    
    Args:
        text (str): The input text to analyze.
        
    Returns:
        str: The detected intent.
    """
    # Placeholder for actual intent detection logic
    # Simple keyword-based detection for demonstration purposes
    if "routine" in text.lower():
        return "routine"
    elif "packing" in text.lower():
        return "packing"
    elif "reminder" in text.lower():
        return "reminder"
    elif "wardrobe" in text.lower():
        return "wardrobe"
    else: 
        return None