from app.core.assistant import Assistant


def main():
    print("=" * 50)
    print(" AURA")
    print(" Automated User Response Assistant")
    print("=" * 50)

    assistant = Assistant()
    assistant.start()


if __name__ == "__main__":
    main()