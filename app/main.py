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

    # Lifecycle startup greeting via VoiceManager / TTS
    try:
        voice_manager.speak(
            "Hello! I'm AURA. I'm ready to help. Please tell me what you'd like me to do."
        )
    except Exception as exc:
        print(f"Startup greeting failed: {exc}")

    try:
        agent.run_once()
    finally:
        try:
            voice_manager.speak("Goodbye!")
        except Exception:
            pass


if __name__ == "__main__":
    main()