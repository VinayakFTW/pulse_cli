import speech_recognition as sr
import sounddevice as sd
from soprano.utils.streaming import play_stream
from soprano import SopranoTTS
from faster_whisper import WhisperModel

_tts_model = None
_tts_enabled = True

SAMPLE_RATE = 16000

def set_tts_enabled(enabled: bool):
    """Controls whether speak() synthesizes and plays audio."""
    global _tts_enabled
    _tts_enabled = bool(enabled)

def is_tts_enabled() -> bool:
    """Returns whether TTS audio playback is currently enabled."""
    return _tts_enabled

def get_tts_model():
    """Lazy loads SopranoTTS on demand to avoid import delays and premature VRAM allocation."""
    global _tts_model
    if _tts_model is None:
        device = 'cuda'
        _tts_model = SopranoTTS(
            backend='transformers',
            device=device,
            cache_size_mb=500,
            decoder_batch_size=2
        )
    return _tts_model

def speak(_audio=None, voice_change=False):
    """
    Synthesizes text to speech using Soprano TTS and plays it via sounddevice streaming.
    Returns the spoken text string.
    """
    if not _audio or not _tts_enabled:
        return str(_audio) if _audio is not None else ""

    text = str(_audio).strip()
    if not text:
        return ""

    try:
        model = get_tts_model()
        stream = model.infer_stream(text, chunk_size=1)
        play_stream(stream)
    except Exception as e:
        print(f"Audio playback error: {e}")

    return text

def get_stt_model():
    global _stt_model

    if _stt_model is None:
        print("Loading Whisper Large-v3-Turbo...")

        _stt_model = WhisperModel(
            "large-v3-turbo",
            device="cuda",
            compute_type="float16",
        )

        print("Whisper loaded.")
    return _stt_model

def record_microphone(duration=5):
    """
    Records microphone audio directly into a NumPy array.

    Returns:
        np.ndarray: float32 mono audio at 16 kHz
    """

    print("Listening...")

    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
    )

    sd.wait()
    return audio[:, 0]

def transcribe_audio(audio):
    """
    Transcribes a NumPy audio array using local Whisper.
    """

    model = get_stt_model()

    segments, info = model.transcribe(
        audio,
        beam_size=1,
        language=None,
        vad_filter=True,
    )

    text = "".join(
        segment.text
        for segment in segments
    ).strip()

    return text, info.language

def command(duration=5):
    """
    Records audio from microphone and transcribes using Whisper.
    """
    try:
        audio = record_microphone(duration)
        text, language = transcribe_audio(audio)

        if not text:
            print("Didn't understand anything.")
            return "0"

        print(f"Language: {language}")
        print(f"Recognized: {text}")

        return text

    except Exception as e:
        print(f"STT error: {e}")
        return "0"


def listen_for_wake_word(wake_word="wake", duration=2):
    """
    Checks for internet and routes to Google (online) for wake word detection.
    """
    print(f"Listening for wake word '{wake_word}'...")

    audio = record_microphone(duration)
    text, _ = transcribe_audio(audio)
    text = text.lower().strip()

    if wake_word.lower() in text:
        print(f"Wake word detected in: '{text}'")
        return True

    return False
