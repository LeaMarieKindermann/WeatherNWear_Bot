from gtts import gTTS
import os
import tempfile

def text_to_speech(text, lang='de'):
    """
    Converts text to speech and returns the path to the audio file (OGG for Telegram).
    """
    # gTTS supports 'de' and 'en' etc.
    tts = gTTS(text=text, lang=lang)
    # Use a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
        tts.save(fp.name)
        mp3_path = fp.name
    # Convert mp3 to ogg (Telegram prefers OGG/Opus for voice messages)
    ogg_path = mp3_path.replace('.mp3', '.ogg')
    os.system(f'ffmpeg -y -i "{mp3_path}" -acodec libopus "{ogg_path}"')
    os.remove(mp3_path)
    return ogg_path
