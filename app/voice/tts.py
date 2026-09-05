from abc import ABC, abstractmethod


class TextToSpeech(ABC):
    """Interface for text-to-speech systems."""

    @abstractmethod
    def speak(self, text: str) -> None:
        """Speak the provided text."""
        raise NotImplementedError


import pyttsx3


class Pyttsx3TTS(TextToSpeech):
    """Local text-to-speech implementation using pyttsx3."""

    def __init__(self):
        self.engine = pyttsx3.init()

    def speak(self, text: str) -> None:
        """Convert text into spoken audio."""

        if not text:
            return

        print(f"AURA: {text}")

        self.engine.say(text)
        self.engine.runAndWait()