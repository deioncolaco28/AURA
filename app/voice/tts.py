from abc import ABC, abstractmethod

import subprocess


class TextToSpeech(ABC):
    @abstractmethod
    def speak(self, text: str) -> None:
        raise NotImplementedError


class Pyttsx3TTS(TextToSpeech):
    """
    Windows-native text-to-speech implementation.

    Uses the Windows System.Speech synthesizer through
    PowerShell instead of relying on pyttsx3's event loop.
    """

    def __init__(self):
        self._powershell = self._find_powershell()

    @staticmethod
    def _find_powershell() -> str:
        """
        Locate Windows PowerShell.
        """
        candidates = [
            r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
            "powershell.exe",
        ]

        for candidate in candidates:
            try:
                result = subprocess.run(
                    [candidate, "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    return candidate

            except Exception:
                continue

        raise RuntimeError(
            "Windows PowerShell could not be found."
        )

    def speak(self, text: str) -> None:
        """
        Speak the supplied text using Windows Speech.
        """

        if not text or not text.strip():
            return

        message = text.strip()

        print(f"AURA: {message}")

        # Escape PowerShell string characters safely.
        safe_message = (
            message
            .replace("`", "``")
            .replace("'", "''")
        )

        command = f"""
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speaker.Volume = 100
$speaker.Rate = 0
$speaker.Speak('{safe_message}')
$speaker.Dispose()
"""

        try:
            result = subprocess.run(
                [
                    self._powershell,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    command,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                print(
                    "TTS playback failed:"
                )
                print(
                    result.stderr.strip()
                )

        except subprocess.TimeoutExpired:
            print(
                "TTS playback timed out."
            )

        except Exception as error:
            print(
                f"TTS playback error: {error}"
            )