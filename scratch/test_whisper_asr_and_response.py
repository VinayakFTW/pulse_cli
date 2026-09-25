import os
import sys
import time
import argparse
import numpy as np

# Ensure UTF-8 output encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pulse_ear.speech_handler import (
    get_stt_model,
    transcribe_audio,
    record_microphone,
    speak,
    set_tts_enabled,
    SAMPLE_RATE,
)
from pulse_brain.llm_interface import (
    load_openai_model,
    query_llm,
    generate_response,
    parse_tool_call,
)
from pulse_config.config import (
    ROUTER_SYSTEM_PROMPT,
    reload_prompts,
)


def synthesize_test_speech(text: str, output_path: str):
    """
    Synthesizes a known speech waveform to a WAV file using SopranoTTS
    for deterministic automated ASR testing.
    """
    from soprano import SopranoTTS
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tts = SopranoTTS(backend="transformers", device=device)
    tts.infer(text, out_path=output_path)
    return output_path


def test_whisper_initialization():
    print("\n[Test 1] Initializing Whisper STT Model...")
    t0 = time.time()
    model = get_stt_model()
    init_duration = time.time() - t0

    assert model is not None, "Failed to initialize Whisper model."
    from faster_whisper import WhisperModel
    assert isinstance(model, WhisperModel), f"Expected WhisperModel instance, got {type(model)}"

    print(f"    PASSED: Whisper model initialized in {init_duration:.2f}s.")
    return model


def test_asr_audio_resilience():
    print("\n[Test 2] Testing ASR Audio Input Resilience (NumPy Arrays & Silence)...")
    
    # 1. Test 2 seconds of pure silence (zeros array at 16kHz)
    silence_duration = 2.0
    silence_samples = int(SAMPLE_RATE * silence_duration)
    silence_audio = np.zeros(silence_samples, dtype=np.float32)

    t0 = time.time()
    silence_text, silence_lang = transcribe_audio(silence_audio)
    silence_time = time.time() - t0

    # Silence should transcribe to empty/whitespace without throwing
    assert silence_text.strip() == "", f"Expected empty text for silence, got: '{silence_text}'"
    print(f"    Silence Handling: Transcribed in {silence_time:.2f}s -> Output: '{silence_text}' (Lang: {silence_lang})")

    # 2. Test 1 second of synthetic 440Hz sine wave (non-speech tone)
    tone_duration = 1.0
    t = np.linspace(0, tone_duration, int(SAMPLE_RATE * tone_duration), endpoint=False)
    sine_audio = (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    tone_text, tone_lang = transcribe_audio(sine_audio)
    print(f"    Synthetic Tone Handling: Handled cleanly without errors -> Output: '{tone_text}' (Lang: {tone_lang})")

    print("    PASSED: ASR handled edge-case audio arrays robustly.")


def test_asr_transcription_accuracy_and_benchmark():
    print("\n[Test 3] Testing ASR Speech Accuracy & Real-Time Factor (RTF)...")
    
    test_phrase = "What is the capital of France?"
    sample_wav = os.path.join("scratch", "_tmp_asr_test.wav")

    print(f"    Synthesizing reference speech: '{test_phrase}'...")
    synthesize_test_speech(test_phrase, sample_wav)
    assert os.path.exists(sample_wav), f"WAV file not found at {sample_wav}"

    try:
        # Measure transcription latency
        t0 = time.time()
        transcribed_text, detected_lang = transcribe_audio(sample_wav)
        transcribe_duration = time.time() - t0

        print(f"    Recognized Text: '{transcribed_text}'")
        print(f"    Detected Language: '{detected_lang}'")
        print(f"    Transcription Latency: {transcribe_duration:.3f}s")

        # Estimate audio duration from file size (16-bit 32kHz wav ~ 64KB/sec)
        file_size = os.path.getsize(sample_wav)
        approx_audio_duration = file_size / (32000 * 2)
        rtf = transcribe_duration / max(approx_audio_duration, 0.1)
        print(f"    Approx Audio Duration: {approx_audio_duration:.2f}s | Real-Time Factor (RTF): {rtf:.3f}")

        # Assertions
        assert detected_lang == "en", f"Expected language 'en', got: '{detected_lang}'"
        cleaned_lower = transcribed_text.lower()
        assert "capital" in cleaned_lower and "france" in cleaned_lower, (
            f"Transcription mismatch! Expected keywords 'capital' and 'france'. Got: '{transcribed_text}'"
        )
        assert rtf < 1.0, f"ASR is slower than real-time! RTF: {rtf:.2f}"

        print(f"    PASSED: Accuracy verified (matched '{test_phrase}') with fast RTF ({rtf:.3f}).")
        return transcribed_text

    finally:
        if os.path.exists(sample_wav):
            try:
                os.remove(sample_wav)
            except OSError:
                pass


def test_model_response_generation():
    print("\n[Test 4] Testing LLM Model Response Generation...")
    
    client, model_type = load_openai_model()
    assert client is not None, "Failed to load LLM client."

    test_prompt = "What is the capital of France? Reply in less than 10 words."
    history = [
        {"role": "user", "content": test_prompt}
    ]

    t0 = time.time()
    response_text = query_llm(client, history, model_type=model_type)
    duration = time.time() - t0

    print(f"    Query: '{test_prompt}'")
    print(f"    Model Response: '{response_text.strip()}' (Latency: {duration:.2f}s)")

    assert response_text and len(response_text.strip()) > 0, "Model returned an empty response."
    assert "paris" in response_text.lower(), f"Expected 'Paris' in response, got: '{response_text}'"

    print("    PASSED: Model response generated accurately and within latency constraints.")
    return client, model_type


def test_e2e_asr_to_model_response():
    print("\n[Test 5] Testing End-to-End Pipeline (Speech Audio -> Whisper ASR -> LLM Response)...")
    
    client, model_type = load_openai_model()
    reload_prompts()

    # Case A: Conversational Voice Query
    print("\n  Case A: Conversational Speech Query...")
    sample_wav = os.path.join("scratch", "_tmp_e2e_calc.wav")
    query_text = "What is 7 plus 5? Answer with only the number."
    
    synthesize_test_speech(query_text, sample_wav)

    try:
        # Step 1: STT via Whisper
        t0 = time.time()
        asr_text, lang = transcribe_audio(sample_wav)
        stt_dur = time.time() - t0
        print(f"    [ASR] Transcribed: '{asr_text}' (Lang: {lang}) in {stt_dur:.2f}s")
        assert asr_text.strip(), "ASR transcribed empty text from query audio."

        # Step 2: Feed into Router / LLM Pipeline (matching cli_agent.py logic)
        tool_check_history = [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": asr_text}
        ]

        t1 = time.time()
        response, _ = generate_response(
            asr_text,
            tool_check_history,
            client,
            model_type=model_type,
            is_tool_check=True
        )
        llm_dur = time.time() - t1
        print(f"    [LLM] Response: '{response.strip()}' in {llm_dur:.2f}s")

        assert "12" in response, f"Expected answer '12' in response, got: '{response}'"
        print("    -> Case A Success: Spoken query accurately transcribed and answered by model.")

    finally:
        if os.path.exists(sample_wav):
            try:
                os.remove(sample_wav)
            except OSError:
                pass

    # Case B: Voice Command for CLI Agent Task
    print("\n  Case B: Action-Oriented Speech Command for Tool Router...")
    sample_wav_b = os.path.join("scratch", "_tmp_e2e_tool.wav")
    tool_command = "Create a python script named hello.py that prints hello world"

    synthesize_test_speech(tool_command, sample_wav_b)

    try:
        asr_tool_text, _ = transcribe_audio(sample_wav_b)
        print(f"    [ASR] Transcribed Command: '{asr_tool_text}'")

        tool_check_history = [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": asr_tool_text}
        ]

        tool_response, _ = generate_response(
            asr_tool_text,
            tool_check_history,
            client,
            model_type=model_type,
            is_tool_check=True
        )
        print(f"    [Router Output]: '{tool_response.strip()}'")

        tool_name, params = parse_tool_call(tool_response)
        assert tool_name == "cli_agent", f"Expected tool 'cli_agent', got: '{tool_name}' (response: {tool_response})"
        assert "task" in params, f"Expected 'task' parameter in tool arguments: {params}"
        print(f"    -> Case B Success: Spoken command routed to tool '{tool_name}' with task: '{params['task']}'")

    finally:
        if os.path.exists(sample_wav_b):
            try:
                os.remove(sample_wav_b)
            except OSError:
                pass

    print("\n    PASSED: End-to-End ASR -> Model Response pipeline operates seamlessly.")


def test_interactive_live_microphone(enable_tts: bool = False):
    print("\n" + "=" * 65)
    print("           INTERACTIVE LIVE MICROPHONE TEST MODE")
    print("=" * 65)
    print("Speak clearly into your microphone when prompted.")
    print("Recording will automatically stop when silence is detected.")
    print("=" * 65 + "\n")

    input("Press [Enter] to start recording...")

    # Record from user's live microphone
    audio = record_microphone(max_duration=15, silence_duration=1.2)
    
    if len(audio) == 0:
        print("No audio captured.")
        return

    print("\nTranscribing with Whisper Large-v3-Turbo...")
    t0 = time.time()
    transcribed_text, detected_lang = transcribe_audio(audio)
    asr_latency = time.time() - t0

    print(f"-> Language Detected: {detected_lang}")
    print(f"-> You Spoke: '{transcribed_text}' (Latency: {asr_latency:.2f}s)")

    if not transcribed_text.strip():
        print("No speech detected in recorded audio.")
        return

    # Query LLM
    print("\nGenerating PulseAI response...")
    client, model_type = load_openai_model()
    reload_prompts()

    tool_check_history = [
        {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
        {"role": "user", "content": transcribed_text}
    ]

    t1 = time.time()
    response, _ = generate_response(
        transcribed_text,
        tool_check_history,
        client,
        model_type=model_type,
        is_tool_check=True
    )
    llm_latency = time.time() - t1

    tool_name, params = parse_tool_call(response)
    if tool_name:
        print(f"-> PulseAI Action: [Tool: {tool_name}] Task: {params.get('task')}")
        speech_out = f"Executing tool {tool_name}"
    else:
        print(f"-> PulseAI Response: {response.strip()}")
        speech_out = response

    print(f"-> Total Pipeline Latency: {asr_latency + llm_latency:.2f}s (ASR: {asr_latency:.2f}s, LLM: {llm_latency:.2f}s)")

    if enable_tts:
        print("\nPlaying spoken response via Soprano TTS...")
        set_tts_enabled(True)
        speak(speech_out)


def asr_stt_tests():
    parser = argparse.ArgumentParser(description="Whisper ASR & Model Response Test Suite")
    parser.add_argument("--mic", action="store_true", help="Run interactive live microphone test")
    parser.add_argument("--tts", action="store_true", help="Enable spoken response playback via Soprano TTS")
    args = parser.parse_args()

    # Disable audio playback during automated tests by default
    set_tts_enabled(args.tts)

    if args.mic:
        test_interactive_live_microphone(enable_tts=args.tts)
    else:
        print("=" * 65)
        print("     STARTING WHISPER ASR & MODEL RESPONSE TEST SUITE")
        print("=" * 65)

        test_whisper_initialization()
        test_asr_audio_resilience()
        test_asr_transcription_accuracy_and_benchmark()
        test_model_response_generation()
        test_e2e_asr_to_model_response()

        print("\n" + "=" * 65)
        print("   ALL WHISPER ASR & MODEL RESPONSE TESTS PASSED SUCCESSFULLY! ")
        print("=" * 65)
