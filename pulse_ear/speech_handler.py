import pyttsx3
import speech_recognition as sr
import numpy as np
import sounddevice as sd
import queue
import requests


# Change how the Engine Sounds-------xXunderconstructionXx-------------------------------------------------------------------

"""
def voice_change(voice_index=None):
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    try:
        if len(voices) > voice_index:
            engine.setProperty('voice', voices[voice_index].id)
        else:
            print(f"Invalid voice index. Available voices: {list(range(len(voices)))}")
    except Exception as e:
        print(f"Error setting voice: {e}")
        engine.setProperty('voice', voices[0].id)
    return engine
"""

def speak(_audio=None,voice_change=False):
    # if voice_change:
    #     engine = voice_change(voice_index)
    # else:
    #     engine = pyttsx3.init()
    engine = pyttsx3.init()
    engine.say(_audio)
    engine.runAndWait()
    engine.stop()
    return _audio


def check_internet_connection(url='http://www.google.com/', timeout=5):
    """Checks for a stable internet connection."""
    try:
        requests.get(url, timeout=timeout)
        return True
    except (requests.ConnectionError, requests.Timeout):
        return False

def command_google():
    """
    Listens using speech_recognition and uses Google's (ONLINE) Web Speech API.
    """
    _recog = sr.Recognizer()
    with sr.Microphone() as _source:
        print("Listening... (Google Online)")
        _recog.pause_threshold = 1
        _recog.adjust_for_ambient_noise(_source, duration=1)
        _audio = _recog.listen(_source)
    
    try:
        print("Recognizing... (Google Online)")
        _query = _recog.recognize_google(_audio)
        print(f"Recognized: {_query}")
        return _query
    except sr.UnknownValueError:
        print("Sorry, I didn't understand that")
        return "0"
    except sr.RequestError as error1:
        print(f"Google API request failed; {error1}")
        return "0"
    except Exception as error2:
        print(f"An error occurred: {error2}")
        return "0"

def command():
    """
    Checks for internet and routes to Google (online) or Whisper (offline).
    """
    if check_internet_connection():
        return command_google()
    else:
        print("No internet connection.")
        return None

def listen_for_wake_word_google(wake_word="wake", duration=2):
    """Listens for wake word using Google (Online) Web Speech."""
    print(f"Listening for wake word '{wake_word}'... (Google Online)")
    r = sr.Recognizer()
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = r.listen(source, timeout=3, phrase_time_limit=duration)
        except sr.WaitTimeoutError:
            return False

    try:
        transcribed_text = r.recognize_google(audio).lower().strip()
        if wake_word in transcribed_text:
            print(f"Wake word detected in: '{transcribed_text}'")
            return True
        return False
    except (sr.UnknownValueError, sr.RequestError):
        return False
    except Exception as e:
        print(f"An error occurred during wake word detection: {e}")
        return False


def listen_for_wake_word(wake_word="wake", duration=2):
    """
    Checks for internet and routes to Google (online) for wake word detection.
    """
    if check_internet_connection():
        return listen_for_wake_word_google(wake_word, duration)
    else:
        return "Network Error"
