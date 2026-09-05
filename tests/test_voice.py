from app.voice.stt import SpeechToText
from app.voice.tts import TextToSpeech
from app.voice.voice_manager import VoiceManager


class MockSTT(SpeechToText):
    """Fake speech-to-text implementation for testing."""

    def listen(self) -> str:
        return "Open Notepad"


class MockTTS(TextToSpeech):
    """Fake text-to-speech implementation for testing."""

    def __init__(self):
        self.last_text = None

    def speak(self, text: str) -> None:
        self.last_text = text


def test_voice_manager_listen():
    voice_manager = VoiceManager(
        stt=MockSTT(),
        tts=MockTTS(),
    )

    text = voice_manager.listen()

    assert text == "Open Notepad"


def test_voice_manager_speak():
    tts = MockTTS()

    voice_manager = VoiceManager(
        stt=MockSTT(),
        tts=tts,
    )

    voice_manager.speak("Hello")

    assert tts.last_text == "Hello"