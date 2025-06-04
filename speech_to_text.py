import os
import speech_recognition as sr
from pydub import AudioSegment # Requires ffmpeg to be installed https://ffmpeg.org/download.html
from langdetect import detect

ogg_path = "temp.ogg"
wav_path = "temp.wav"

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
            detected = detect(text)
            if lang.lower().startswith(detected.lower()):
                # Return both text and detected language code
                return text, detected
        except:
            continue

    # Fallback: return first result with the language it was recognized in
    if results:
        first_lang, first_text = next(iter(results.items()))
        return first_text, first_lang
    # If no text was recognized, return None
    else:
        return None, None