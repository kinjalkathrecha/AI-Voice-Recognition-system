import React, { useState, useRef } from "react";
import axios from "axios";
import { Link } from "react-router-dom";

const BACKEND_URL = "http://127.0.0.1:3000"; // change if needed

function App(){
  const [file, setFile] = useState(null);
  const [recording, setRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [audioURL, setAudioURL] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [userId, setUserId] = useState("kinjal01");
  const chunksRef = useRef([]);

  // start recording using MediaRecorder
  const startRecording = async () => {
    setResult(null);
    try{
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      mr.ondataavailable = e => { if(e.data.size>0) chunksRef.current.push(e.data) };
      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        chunksRef.current = [];
        const f = new File([blob], "recording.webm", { type: "audio/webm" });
        setFile(f);
        const url = URL.createObjectURL(blob);
        setAudioURL(url);
      };
      mr.start();
      setMediaRecorder(mr);
      setRecording(true);
    }catch(e){
      alert("Microphone access denied or not available.");
      console.error(e);
    }
  };

  const stopRecording = () => {
    if(mediaRecorder){
      mediaRecorder.stop();
      setRecording(false);
    }
  };

  const handleFileChange = (e) => {
    setResult(null);
    const f = e.target.files[0];
    if(f) setFile(f);
    setAudioURL(URL.createObjectURL(f));
  };

  const submitAudio = async () => {
    if(!file){
      alert("Please record or upload an audio file first.");
      return;
    }

    setLoading(true);
    setResult(null);

    const form = new FormData();
    form.append("file", file);
    form.append("user_id", userId);

    try{
      const res = await axios.post(`${BACKEND_URL}/process-audio`, form, {
        headers: {"Content-Type":"multipart/form-data"},
        timeout: 240000
      });

      setResult(res.data);

      // fetch recommendation (backend has GET /recommend-lesson?user_id=...)
      try{
        const rec = await axios.get(`${BACKEND_URL}/recommend-lesson`, {
          params: { user_id: userId }
        });
        setResult(prev => ({...prev, recommendation: rec.data.recommendation || rec.data.message || rec.data}));
      }catch(err){
        console.warn("Recommendation fetch failed", err);
      }

    }catch(err){
      console.error(err);
      alert("Failed to process audio. Check backend and CORS.");
    }finally{
      setLoading(false);
    }
  };

  return (
    <div className="container">

      <div className="header">
        <div>
          <div className="title">🎙 AI Language Learning — Frontend</div>
          <div className="small">Record, upload & get instant feedback</div>
        </div>
        <div className="controls">
          <input
            placeholder="user id"
            value={userId}
            onChange={e=>setUserId(e.target.value)}
            className="file-input"
            style={{width:140}}
          />
          <Link to="/dashboard" className="btn secondary">Dashboard</Link>
        </div>
      </div>

      <div className="card">
        <h3>Record with mic</h3>
        <div className="row" style={{marginTop:8}}>
          {!recording && <button className="btn" onClick={startRecording}>Start Recording</button>}
          {recording && <button className="btn" onClick={stopRecording}>Stop Recording</button>}
          <div className="small">or</div>
          <input className="file-input" type="file" accept="audio/*" onChange={handleFileChange} />
        </div>

        {audioURL && (
          <div className="result">
            <div className="kv"><span className="k">Preview</span><span className="v"><audio src={audioURL} controls /></span></div>
          </div>
        )}

        <div style={{marginTop:12}} className="row">
          <button className="btn" onClick={submitAudio} disabled={loading}>
            {loading ? "Processing..." : "Submit to Backend"}
          </button>
        </div>

        {result && (
          <div className="result">
            <div className="kv"><span className="k">Transcription:</span><span className="v">{result.original_text || result.transcription || "—"}</span></div>
            <div className="kv"><span className="k">Corrected:</span><span className="v">{result.corrected_text || result.corrected || "—"}</span></div>
            <div className="kv"><span className="k">Pronunciation:</span><span className="v">{result.pronunciation_score ?? result.pronunciation_score ?? result.pronunciation ?? "—"}</span></div>
            <div className="kv"><span className="k">Grammar score:</span><span className="v">{result.grammar_score ?? result.grammar_accuracy ?? "—"}</span></div>

            <div className="reco">
              <strong>Recommendation:</strong>
              <div style={{marginTop:8}}>{result.recommendation || "No recommendation available"}</div>
            </div>
          </div>
        )}
      </div>

      
    </div>
  );
}

export default App;
