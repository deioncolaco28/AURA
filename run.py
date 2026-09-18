from app.config.constants import AssistantMode
from app.core.agent import Agent
from app.voice.stt import SpeechRecognitionSTT
from app.voice.tts import Pyttsx3TTS
from app.voice.voice_manager import VoiceManager


def create_voice_manager() -> VoiceManager:
    """Create the default voice stack."""

    stt = SpeechRecognitionSTT()
    tts = Pyttsx3TTS()

    return VoiceManager(
        stt=stt,
        tts=tts,
    )


def create_agent() -> Agent:
    """Create the main AURA agent."""

    voice_manager = create_voice_manager()

    return Agent(
        voice_manager=voice_manager,
    )


def print_banner() -> None:
    print()
    print("=" * 60)
    print("       AURA - Automated User Response Assistant")
    print("=" * 60)
    print()
    print("Voice-controlled computer-use assistant")
    print()
    print("Modes:")
    print("  • Do It For Me")
    print("  • Show Me How")
    print()
    print("Examples:")
    print("  Open Notepad")
    print("  Open Calculator")
    print("  Show me how to open Notepad")
    print()
    print("Say 'exit' to stop.")
    print("=" * 60)
    print()


def main() -> None:
    print_banner()

    agent = create_agent()

    print("AURA initialized.")
    print("Listening for commands...")
    print()

    # Lifecycle startup greeting via VoiceManager / TTS
    try:
        agent.voice_manager.speak(
            "Hello! I'm AURA. I'm ready to help. Please tell me what you'd like me to do."
        )
    except Exception as exc:
        print(f"Startup greeting failed: {exc}")

    while True:
        try:
            text = agent.voice_manager.listen()

            if not text:
                continue

            if text.strip().lower() in {
                "exit",
                "quit",
                "stop",
                "goodbye",
            }:
                agent.voice_manager.speak(
                    "Goodbye! Have a great day."
                )
                break

            agent.process_text(text)

            print()
            print(
                "Ready for the next command..."
            )
            print()

        except KeyboardInterrupt:
            print()
            print("AURA stopped by user.")
            try:
                agent.voice_manager.speak("Goodbye!")
            except Exception:
                pass
            break

        except Exception as error:
            print(
                f"AURA runtime error: {error}"
            )

            try:
                agent.voice_manager.speak(
                    "I encountered an error "
                    "while processing that command."
                )
            except Exception:
                pass


if __name__ == "__main__":
    main()