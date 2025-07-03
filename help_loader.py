import os

def load_help_text(feature, language):
    """
    Load help text from external .txt file.
    
    Args:
        feature (str): The feature name (main, packing, routines, wardrobe, reminders)
        language (str): Language code (de or en)
        
    Returns:
        str: The help text content
    """
    filename = f"help_{feature}_{language}.txt"
    
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return f"Help text not found for {feature} in {language}."

def format_help_text(feature, language):
    """
    Load and return help text for a specific feature and language.
    
    Args:
        feature (str): The feature name (main, packing, routines, wardrobe, reminders)
        language (str): Language code (de or en)
        
    Returns:
        str: Help text in Markdown format
    """
    return load_help_text(feature, language)

def get_main_help_text(language):
    """
    Get the main help text with title and description.
    
    Args:
        language (str): Language code (de or en)
        
    Returns:
        str: Main help text
    """
    return load_help_text("main", language)