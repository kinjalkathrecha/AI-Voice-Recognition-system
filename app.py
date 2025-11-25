import os
import numpy as np
import librosa
import sqlite3
from flask import Flask, request, jsonify, send_file
import whisper
from gtts import gTTS
from werkzeug.utils import secure_filename
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


# Flask setup
app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
from flask_cors import CORS
CORS(app)
# ---------- DATABASE SETUP ----------
DB_PATH = "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            pronunciation_avg REAL,
            grammar_accuracy REAL,
            last_topic TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()


def update_user_progress(user_id, p_score, g_score, topic):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM user_progress WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if row:
        cursor.execute("""
            UPDATE user_progress
            SET pronunciation_avg=?, grammar_accuracy=?, last_topic=?
            WHERE user_id=?
        """, (p_score, g_score, topic, user_id))
    else:
        cursor.execute("""
            INSERT INTO user_progress (user_id, pronunciation_avg, grammar_accuracy, last_topic)
            VALUES (?, ?, ?, ?)
        """, (user_id, p_score, g_score, topic))

    conn.commit()
    conn.close()


def get_user_progress(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT pronunciation_avg, grammar_accuracy, last_topic FROM user_progress WHERE user_id=?", (user_id,))
    row = cursor.fetchone()

    conn.close()
    return row


# ---------- LOAD MODELS ----------
print("🧠 Loading Whisper model...")
whisper_model = whisper.load_model("tiny")

print("📘 Loading Grammar Correction model (T5-base)...")
grammar_tokenizer = AutoTokenizer.from_pretrained("prithivida/grammar_error_correcter_v1")
grammar_model = AutoModelForSeq2SeqLM.from_pretrained("prithivida/grammar_error_correcter_v1")


def evaluate_pronunciation(audio_path):
    try:
        y, sr = librosa.load(audio_path, sr=None)
        energy = np.mean(np.abs(y))
        rate = len(y) / sr
        score = (energy * 0.6 + rate * 0.4) * 100
        return round(float(score), 2)
    except:
        return 0.0


def correct_grammar(text):
    try:
        input_text = "gec: " + text
        input_ids = grammar_tokenizer.encode(input_text, return_tensors="pt")
        outputs = grammar_model.generate(input_ids, max_length=128, num_beams=4)
        return grammar_tokenizer.decode(outputs[0], skip_special_tokens=True)
    except:
        return text


# ---------- ROUTES ----------
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Welcome to the AI Language Learning Tool API"}), 200


@app.route("/generate-audio", methods=["POST"])
def generate_audio():
    data = request.get_json()
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    output_path = os.path.join(os.path.dirname(__file__), "output.mp3")
    tts = gTTS(text)
    tts.save(output_path)

    return send_file(output_path, as_attachment=True)


@app.route("/process-audio", methods=["POST"])
def process_audio():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    user_id = request.form.get("user_id", "default_user")

    file = request.files["file"]
    filepath = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
    file.save(filepath)

    try:
        # Step 1: Transcribe
        result = whisper_model.transcribe(filepath)
        original_text = result["text"].strip()

        # Step 2: Grammar
        corrected_text = correct_grammar(original_text)

        # Step 3: Pronunciation
        p_score = evaluate_pronunciation(filepath)

        # Step 4: Grammar score (simple)
        g_score = 100 if corrected_text == original_text else 50

        # Step 5: Update DB
        update_user_progress(user_id, p_score, g_score, "general conversation")

        return jsonify({
            "original_text": original_text,
            "corrected_text": corrected_text,
            "pronunciation_score": p_score,
            "grammar_score": g_score
        }), 200

    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@app.route("/recommend-lesson", methods=["GET"])
def recommend_lesson():
    user_id = request.args.get("user_id", "default_user")
    progress = get_user_progress(user_id)

    if not progress:
        return jsonify({"message": "No user history found. Complete one audio test first."})

    p_score, g_score, last_topic = progress

    if p_score < 50:
        recommendation = "🎧 Do listening & repetition practice."
    elif g_score < 70:
        recommendation = "📝 Do basic grammar and writing exercises."
    else:
        recommendation = "🎤 Practice speaking longer sentences."

    return jsonify({
        "pronunciation_avg": p_score,
        "grammar_accuracy": g_score,
        "last_topic": last_topic,
        "recommendation": recommendation
    })


if __name__ == "__main__":
    app.run(debug=True, port=3000)
