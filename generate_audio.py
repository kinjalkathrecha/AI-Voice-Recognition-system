from gtts import gTTS

# The text you want to convert to speech
text = "Hello, this is a test audio for Whisper transcription."
language = "en"

# Create audio file
tts = gTTS(text=text, lang=language)
tts.save("sample_audio.mp3")

print("✅ sample_audio.mp3 created successfully!")
