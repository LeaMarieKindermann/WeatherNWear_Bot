import os
import speech_recognition as sr
from pydub import AudioSegment # Requires ffmpeg to be installed https://ffmpeg.org/download.html
from langdetect import detect, detect_langs
from langdetect.lang_detect_exception import LangDetectException

ogg_path = "temp.ogg"
wav_path = "temp.wav"

"""
Helper function to detect the language of a given text.

----
Args:
    text (str): The text to analyze.
"""
def detect_language(text):
    rerun = 0
    """
    Detect the language of a given text using langdetect with confidence scoring.
    Returns the ISO language code (e.g. 'de', 'en').
    Only returns 'de' or 'en' as these are the only supported languages.
    Uses ML-based detection with multiple attempts for better accuracy.
    Returns None if no supported language is detected with sufficient confidence.
    """
    if not text or not text.strip():
        return None
    
    try:
        # Try to get confidence scores for all detected languages
        lang_probs = detect_langs(text)
        
        # Filter for supported languages and find the best match
        supported_langs = {}
        for lang_prob in lang_probs:
            if lang_prob.lang in ['de', 'en']:
                supported_langs[lang_prob.lang] = lang_prob.prob
        
        if supported_langs:
            # Return the language with highest confidence
            best_lang = max(supported_langs, key=supported_langs.get)
            confidence = supported_langs[best_lang]
            
            # Only return if confidence is reasonable (> 0.1)
            if confidence > 0.1:
                return best_lang
        
        # Fallback: try simple detect multiple times (langdetect can be inconsistent)
        detection_results = []
        for _ in range(5):  # Try 5 times for better accuracy
            try:
                detected = detect(text)
                if detected in ['de', 'en']:
                    detection_results.append(detected)
            except LangDetectException:
                continue
        
        if detection_results:
            # Return most common result
            from collections import Counter
            most_common = Counter(detection_results).most_common(1)[0][0]
            return most_common
            
    except (LangDetectException, Exception):
        pass
    
    if rerun < 5:
        rerun += 1
        return detect_language(text)
    # If ML detection fails completely, return None
    return None

"""
Transcribe voice messages to text.
This function is called when the user sends a voice message.
It uses the Google Speech Recognition API to transcribe the voice message
and detects the spoken language.
"""
def transcribe_voice(bot, message, languages=["de-DE", "en-US"]):  # Corrected language codes
    # Get the file info from Telegram using the file ID in the message
    file_info = bot.get_file(message.voice.file_id)

    # Download the actual audio file from Telegram's servers
    downloaded_file = bot.download_file(file_info.file_path)

    # Save the downloaded file as an OGG file (Telegram uses this format)
    with open(ogg_path, "wb") as temp_file:
        temp_file.write(downloaded_file)
    
    # Convert the OGG file to WAV format (needed for speech recognition)
    audio = AudioSegment.from_ogg(ogg_path)
    audio.export(wav_path, format="wav")
    
    # Initialize the recognizer
    speech_recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio_data = speech_recognizer.record(source)

    # Clean up temporary files
    os.remove(ogg_path)
    os.remove(wav_path)

    results = {}
    for lang in languages:
        try:
            text = speech_recognizer.recognize_google(audio_data, language=lang)
            if text:
                results[lang] = text
        except (sr.UnknownValueError, sr.RequestError):
            continue

    # Try to detect the language from recognized texts
    for lang, text in results.items():
        try:
            detected = detect_language(text)
            if lang.lower().startswith(detected.lower()):
                # Return both text and detected language code
                return text, detected
        except Exception:
            continue

    # Fallback: return first result with the language it was recognized in
    if results:
        first_lang, first_text = next(iter(results.items()))
        return first_text, first_lang
    # If no text was recognized, return None
    else:
        return None, None