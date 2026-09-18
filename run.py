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


from app.core.health import HealthChecker


def print_banner() -> None:
    print()
    print("=" * 65)
    print("        AURA - Automated User Response Assistant (v1.0)")
    print("=" * 65)
    print()
    print("Voice & Text Whole-PC Automation & Tutoring Assistant")
    print()
    print("System Readiness Status:")
    report = HealthChecker.check_system()
    for line in report.summary_lines():
        print(line)
    print()
    print("Modes:")
    print("  • Do It For Me (Autonomous Execution)")
    print("  • Show Me How  (Interactive Step-by-Step Tutoring)")
    print()
    print("Examples:")
    print("  • Open Notepad and type Hello AURA")
    print("  • Open the report, summarize it, and save as Word document")
    print("  • Find the highest AQI value in this spreadsheet")
    print("  • Show me how to open Calculator")
    print()
    print("Type or say 'exit' / 'stop' to quit.")
    print("=" * 65)
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