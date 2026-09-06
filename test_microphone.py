import speech_recognition as sr


recognizer = sr.Recognizer()

print("Available microphones:")

for index, name in enumerate(
    sr.Microphone.list_microphone_names()
):
    print(f"{index}: {name}")

print("\nTesting default microphone...")

with sr.Microphone() as source:
    print("Adjusting for ambient noise...")
    recognizer.adjust_for_ambient_noise(
        source,
        duration=2,
    )

    print("Speak now...")
    audio = recognizer.listen(
        source,
        timeout=5,
        phrase_time_limit=10,
    )

print("Audio captured.")
print("Sending audio for recognition...")

try:
    text = recognizer.recognize_google(audio)

    print(f"\nRecognized text: {text}")

except sr.UnknownValueError:
    print("\nCould not understand the audio.")

except sr.RequestError as error:
    print(f"\nSpeech recognition service error: {error}")