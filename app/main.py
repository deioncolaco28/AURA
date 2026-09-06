from app.automation.action_executor import ActionExecutor
from app.core.agent import Agent
from app.voice.stt import SpeechRecognitionSTT
from app.voice.tts import Pyttsx3TTS
from app.voice.voice_manager import VoiceManager


def main():
    print("=" * 50)
    print(" AURA")
    print(" Automated User Response Assistant")
    print("=" * 50)

    stt = SpeechRecognitionSTT()
    tts = Pyttsx3TTS()

    voice_manager = VoiceManager(
        stt=stt,
        tts=tts,
    )

    agent = Agent(
        voice_manager=voice_manager,
        action_executor=ActionExecutor(),
    )

    print("\nAURA is ready.")
    print("Say a command...\n")

    agent.run_once()


if __name__ == "__main__":
    main()