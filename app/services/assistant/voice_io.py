"""Optional voice I/O: speech-to-text and text-to-speech (local, lazy).

Typed chat always works with zero extra dependencies. Voice features
activate only when the user has installed a supported local engine:

- STT: faster-whisper (preferred) or SpeechRecognition
- TTS: piper (preferred) or pyttsx3
- microphone: sounddevice or PyAudio (via SpeechRecognition)

Every helper reports availability first; the UI shows an understandable
message instead of failing when nothing is installed.
"""
from typing import Any, Dict, Optional


def stt_status() -> Dict[str, Any]:
    """Which speech-to-text engines are importable on this PC."""
    engines = {}
    for name in ("faster_whisper", "speech_recognition", "sounddevice",
                 "pyaudio", "pyttsx3", "piper"):
        try:
            __import__(name)
            engines[name] = True
        except Exception:
            engines[name] = False
    return {"stt_available": bool(engines["faster_whisper"]
                                  or engines["speech_recognition"]),
            "tts_available": bool(engines["pyttsx3"] or engines["piper"]),
            "engines": engines}


def transcribe_once(timeout: int = 8) -> str:
    """Record one utterance and return text. Raises LearningError clearly."""
    from app.services.local_agent.schemas import LearningError
    status = stt_status()
    if not status["stt_available"]:
        raise LearningError(
            "Voice input needs an optional local speech engine "
            "(install faster-whisper or SpeechRecognition). "
            "Typed chat works without it.")
    # faster-whisper path (file-based transcription when available).
    try:
        if status["engines"].get("sounddevice") and \
                status["engines"].get("faster_whisper"):
            return _transcribe_whisper(timeout)
    except LearningError:
        raise
    except Exception as e:
        raise LearningError(f"Voice recording failed: {e}")
    try:
        if status["engines"].get("speech_recognition"):
            return _transcribe_speech_recognition(timeout)
    except LearningError:
        raise
    except Exception as e:
        raise LearningError(f"Voice recognition failed: {e}")
    raise LearningError("No usable microphone path on this PC.")


def _transcribe_whisper(timeout: int) -> str:
    from app.services.local_agent.schemas import LearningError
    try:
        import sounddevice as sd  # type: ignore
        import soundfile as sf  # type: ignore
        from faster_whisper import WhisperModel  # type: ignore
    except Exception as e:
        raise LearningError(f"Voice engine is incomplete: {e}")
    import tempfile
    path = tempfile.mktemp(prefix="ctm-voice-", suffix=".wav")
    try:
        audio = sd.rec(int(16000 * min(timeout, 15)), samplerate=16000,
                       channels=1, blocking=True)
        sf.write(path, audio, 16000)
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(path)
        text = " ".join(s.text for s in segments).strip()
    finally:
        try:
            import os
            os.unlink(path)
        except OSError:
            pass
    if not text:
        raise LearningError("I could not hear anything. Please try again.")
    return text


def _transcribe_speech_recognition(timeout: int) -> str:
    from app.services.local_agent.schemas import LearningError
    try:
        import speech_recognition as sr  # type: ignore
    except Exception as e:
        raise LearningError(f"Voice engine is incomplete: {e}")
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            audio = recognizer.listen(source, timeout=timeout,
                                      phrase_time_limit=timeout)
        # Sphinx is offline; Google would need internet, so prefer Sphinx.
        try:
            return recognizer.recognize_sphinx(audio) or ""
        except Exception:
            raise LearningError(
                "Offline recognition (Sphinx) is unavailable. "
                "Typed chat works without it.")
    except LearningError:
        raise
    except Exception as e:
        raise LearningError(f"Voice recognition failed: {e}")


def speak(text: str, enabled: bool = True) -> bool:
    """Speak text when a local TTS engine exists. Returns True if spoken."""
    if not enabled or not (text or "").strip():
        return False
    try:
        import pyttsx3  # type: ignore
        engine = pyttsx3.init()
        engine.say(text[:400])
        engine.runAndWait()
        return True
    except Exception:
        return False
