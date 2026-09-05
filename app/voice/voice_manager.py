from app.voice.stt import SpeechToText
from app.voice.tts import TextToSpeech


class VoiceManager:
    """Coordinates speech input and speech output."""

    def __init__(
        self,
        stt: SpeechToText,
        tts: TextToSpeech,
    ):
        self.stt = stt
        self.tts = tts

    def listen(self) -> str:
        """Capture and return the user's speech."""

        return self.stt.listen()

    def speak(self, text: str) -> None:
        """Speak a response to the user."""

        self.tts.speak(text)