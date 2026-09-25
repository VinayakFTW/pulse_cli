import os
import sys
import time
import numpy as np
import sounddevice as sd
from soprano.utils.streaming import play_stream
from soprano import SopranoTTS


def _configure_windows_cuda_dlls():
    """
    Ensures Windows dynamic linker can resolve CUDA 12 and cuDNN DLLs installed via pip
    (e.g., nvidia-cublas-cu12, nvidia-cudnn-cu12) for whisper.
    """
    if sys.platform != "win32":
        return

    import ctypes
    import glob
    import site

    search_dirs = []

    for base in site.getsitepackages():
        for sub in ("cublas", "cudnn", "cuda_nvrtc"):
            p = os.path.join(base, "nvidia", sub, "bin")
            if os.path.isdir(p) and p not in search_dirs:
                search_dirs.append(p)

    cuda_path = os.environ.get("CUDA_PATH")
    if cuda_path:
        for sub in ("bin", os.path.join("bin", "x64")):
            p = os.path.join(cuda_path, sub)
            if os.path.isdir(p) and p not in search_dirs:
                search_dirs.append(p)

    for d in search_dirs:
        try:
            os.add_dll_directory(d)
        except (AttributeError, OSError, FileNotFoundError):
            pass
        if d not in os.environ.get("PATH", ""):
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")

        for dll_file in sorted(glob.glob(os.path.join(d, "*.dll"))):
            try:
                ctypes.CDLL(dll_file)
            except Exception:
                pass


_configure_windows_cuda_dlls()

from faster_whisper import WhisperModel

_tts_model = None
_tts_enabled = True
_stt_model = None

SAMPLE_RATE = 16000

def set_tts_enabled(enabled: bool):
    """Controls whether speak() synthesizes and plays audio."""
    global _tts_enabled
    _tts_enabled = bool(enabled)

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
        _configure_windows_cuda_dlls()
        print("Loading Whisper Large-v3-Turbo...")

        try:
            _stt_model = WhisperModel(
                "large-v3-turbo",
                device="cuda",
                compute_type="float16",
            )
            print("Whisper loaded on CUDA (float16).")
        except Exception as e:
            print(f"Warning: Failed to load Whisper on CUDA ({e}).")
            print("Falling back to CPU (int8)...")
            _stt_model = WhisperModel(
                "large-v3-turbo",
                device="cpu",
                compute_type="int8",
            )
            if _stt_model is None:
                raise RuntimeError("Failed to load Whisper model on both CUDA and CPU.")
            print("Whisper loaded on CPU.")
    return _stt_model

def record_microphone( max_duration=60, silence_duration=1.0, threshold=0.02, min_duration=0.5, ):
    """
    Records audio from the microphone until silence is detected or max_duration is reached.
    Returns a NumPy array of the recorded audio.
    """
    print("Listening...")
    block_duration = 0.1 # 100 ms
    block_size = int(SAMPLE_RATE * block_duration)
    audio_chunks = []
    silence_time = 0.0 
    speech_started = False
    start_time = time.time()
    with sd.InputStream( samplerate=SAMPLE_RATE, channels=1, dtype="float32", blocksize=block_size, ) as stream:
        while True:
            audio, _ = stream.read(block_size)
            audio = audio[:, 0].copy()
            rms = np.sqrt(np.mean(audio ** 2))
            audio_chunks.append(audio)
            if rms > threshold: 
                speech_started = True
                silence_time = 0.0
            elif speech_started:
                silence_time += block_duration
            if speech_started and silence_time >= silence_duration:
                break
            if time.time() - start_time >= max_duration:
                break
    audio = np.concatenate(audio_chunks)
    trim_samples = int(silence_time * SAMPLE_RATE)
    if trim_samples > 0 and trim_samples < len(audio):
        audio = audio[:-trim_samples]

    return audio

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

def get_user_input(mode="voice"):
    if mode == "text":
        try:
            return input("\nVinayak (Text): ").strip()
        except EOFError:
            return "0"
    else:
        return command()

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
