import os
from flask import Flask, request, jsonify, send_file
import whisper
from gtts import gTTS
from werkzeug.utils import secure_filename

# ---------------------------------------------------------
# Flask setup
# ---------------------------------------------------------
app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------------------------------------------------
# Load Whisper model (only once at startup)
# ---------------------------------------------------------
print("🧠 Loading Whisper model (this may take a while)...")
model = whisper.load_model("tiny")

# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------
@app.route("/", methods=["GET"])
def home():
    """Simple welcome message."""
    return jsonify({"message": "Welcome to the AI Language Learning Tool API"}), 200


# ---------------------------------------------------------
# 1️⃣ Generate sample audio
# ---------------------------------------------------------
@app.route("/generate-audio", methods=["POST"])
def generate_audio():
    """Generate a test audio file from provided text."""
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Please provide text in JSON body, e.g. {'text': 'Hello world'}"}), 400

    text = data["text"]
    filename = "sample_audio.mp3"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    try:
        tts = gTTS(text=text, lang="en")
        tts.save(filepath)
        print(f"✅ Audio generated successfully: {filepath}")
        return jsonify({
            "message": "Audio generated successfully",
            "file_path": filepath,
            "text": text
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------
# 2️⃣ Transcribe uploaded audio
# ---------------------------------------------------------
@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    """Handle audio file upload and transcription."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
    file.save(filepath)
    print(f"📂 File saved: {filepath}")

    print("🎧 Transcribing...")
    try:
        # Force English for clarity
        result = model.transcribe(filepath, language="en")
        transcription = result["text"].strip()
        print(f"📝 Transcription: {transcription}")
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

    return jsonify({"transcription": transcription}), 200


# ---------------------------------------------------------
# 3️⃣ Text-to-Speech conversion (TTS)
# ---------------------------------------------------------
@app.route("/text-to-speech", methods=["POST"])
def text_to_speech():
    """Convert text to spoken audio."""
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Please provide text in JSON body"}), 400

    text = data["text"]
    filename = "output_speech.mp3"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    try:
        tts = gTTS(text=text, lang="en")
        tts.save(filepath)
        print(f"🔊 Speech generated: {filepath}")

        # Return the audio file directly to user
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------
# Run the Flask app
# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=3000)
