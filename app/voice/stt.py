from abc import ABC, abstractmethod


class SpeechToText(ABC):
    """Interface for speech-to-text systems."""

    @abstractmethod
    def listen(self) -> str:
        """Listen to the user and return recognized text."""
        raise NotImplementedError


import speech_recognition as sr


class SpeechRecognitionSTT(SpeechToText):
    """Speech-to-text implementation using SpeechRecognition."""

    def __init__(self):
        self.recognizer = sr.Recognizer()

    def listen(self) -> str:
        """Listen through the default microphone."""

        with sr.Microphone() as source:
            print("Listening...")

            self.recognizer.adjust_for_ambient_noise(
                source,
                duration=0.5,
            )

            audio = self.recognizer.listen(source)

        try:
            text = self.recognizer.recognize_google(audio)

            print(f"You said: {text}")

            return text

        except sr.UnknownValueError:
            print("Sorry, I could not understand that.")

            return ""

        except sr.RequestError as error:
            print(f"Speech recognition service error: {error}")

            return ""