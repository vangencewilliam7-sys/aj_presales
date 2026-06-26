import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mic, MicOff, Send, HelpCircle, StopCircle, PauseCircle, Loader2, BrainCircuit, Eye, Target, Zap, FileText, ArrowRight, Image as ImageIcon, X, Monitor, Film } from 'lucide-react';

interface Message {
  id: string;
  role: 'expert' | 'ai';
  text: string;
  timestamp: number;
  imageUrl?: string;
  videoUrl?: string;
  decision?: {
    intent_classification: string;
    internal_reasoning: string;
    action: string;
  };
}

const InterviewPage: React.FC = () => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isSynthesizing, setIsSynthesizing] = useState(false);
  const [showDecision, setShowDecision] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedVideo, setSelectedVideo] = useState<File | null>(null);
  const videoFileInputRef = useRef<HTMLInputElement>(null);

  const [isScreenRecording, setIsScreenRecording] = useState(false);
  const [screenRecordingTimer, setScreenRecordingTimer] = useState(0);
  const [videoPreview, setVideoPreview] = useState<string | null>(null);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [isAnalyzingVideo, setIsAnalyzingVideo] = useState(false);
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerIntervalRef = useRef<number | null>(null);
  const recordedChunksRef = useRef<Blob[]>([]);

  const [showScriptSidebar, setShowScriptSidebar] = useState(true);
  const [scriptThemes, setScriptThemes] = useState<any[]>([]);
  const [activeBlock, setActiveBlock] = useState('Block 1: Personal Origin & Persona');
  const [tangentCount, setTangentCount] = useState(0);

  const sessionId = localStorage.getItem('session_id');
  const icebreakerData = JSON.parse(localStorage.getItem('icebreaker') || '{}');

  useEffect(() => {
    if (!sessionId) {
      navigate('/');
      return;
    }
    
    // Seed the conversation with a generic opening
    setMessages([
      {
        id: '1',
        role: 'ai',
        text: icebreakerData.opening_icebreaker || "Welcome to the studio. We're excited to dive into your background and extract the unwritten rules of your domain.",
        timestamp: Date.now() - 600000,
        decision: {
          intent_classification: 'opening_question',
          internal_reasoning: 'Day 1 opening icebreaker from the generated script.',
          action: 'script_question'
        }
      }
    ]);

    // Fetch the script data for the sidebar
    fetch(`http://localhost:9120/session/${sessionId}`)
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success' && data.session?.script) {
          const arc = data.session.script.interview_arc || data.session.script;
          const extractedThemes = Object.entries(arc || {}).map(([key, phase]: [string, any], idx) => ({
            theme_id: idx,
            theme_title: key.replace('block_', 'Block ').replace(/_/g, ' '),
            editorial_rationale: phase.goal || "Phase goal",
            tentative_duration: phase.tentative_duration_minutes || 20,
            questions: phase.questions || []
          }));
          setScriptThemes(extractedThemes);
          if (extractedThemes.length > 0) {
            setActiveBlock(extractedThemes[0].theme_title);
          }
        }
      })
      .catch(err => console.error("Failed to fetch session script", err));

  }, [sessionId, navigate]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedImage(file);
      const reader = new FileReader();
      reader.onload = (e) => setImagePreview(e.target?.result as string);
      reader.readAsDataURL(file);
    }
  };

  const clearImage = () => {
    setSelectedImage(null);
    setImagePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleVideoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedVideo(file);
      setVideoPreview(URL.createObjectURL(file));
    }
  };

  const clearVideo = () => {
    setRecordedBlob(null);
    setSelectedVideo(null);
    setVideoPreview(null);
    if (videoFileInputRef.current) videoFileInputRef.current.value = '';
  };

  const startScreenRecording = async () => {
    try {
      const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
      const micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      const tracks = [...screenStream.getTracks(), ...micStream.getTracks()];
      const combinedStream = new MediaStream(tracks);
      streamRef.current = combinedStream;
      
      // Try webm, fallback to mp4
      const mimeType = MediaRecorder.isTypeSupported('video/webm') ? 'video/webm' : 'video/mp4';
      const recorder = new MediaRecorder(combinedStream, { 
        mimeType,
        videoBitsPerSecond: 250000 // Compress to 250 kbps to keep file size low
      });
      mediaRecorderRef.current = recorder;
      recordedChunksRef.current = [];
      
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) recordedChunksRef.current.push(e.data);
      };
      
      recorder.onstop = () => {
        const blob = new Blob(recordedChunksRef.current, { type: mimeType });
        setRecordedBlob(blob);
        setVideoPreview(URL.createObjectURL(blob));
        tracks.forEach(t => t.stop());
      };
      
      recorder.start(1000);
      setIsScreenRecording(true);
      setScreenRecordingTimer(0);
      timerIntervalRef.current = window.setInterval(() => {
        setScreenRecordingTimer(prev => prev + 1);
      }, 1000);
      
    } catch (err) {
      console.error(err);
      alert("Screen sharing or microphone permission was denied.");
    }
  };

  const stopScreenRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
    setIsScreenRecording(false);
  };

  const handleSend = async (text: string) => {
    if ((!text.trim() && !selectedImage && !recordedBlob && !selectedVideo) || !sessionId) return;
    
    if (recordedBlob || selectedVideo) {
      const currentPreview = videoPreview;
      const isUploaded = !!selectedVideo;
      const videoSource = isUploaded ? selectedVideo : recordedBlob;
      const inputType = isUploaded ? "video" : "screen_recording";
      const fileExt = isUploaded ? selectedVideo.name.split('.').pop() : (recordedBlob.type.includes("webm") ? "webm" : "mp4");
      const filename = isUploaded ? selectedVideo.name : `recording_${Date.now()}.${fileExt}`;
      
      setMessages(prev => [...prev, { id: Date.now().toString(), role: 'expert', text: `[${isUploaded ? 'Uploaded Video' : 'Screen Recording'}] ${text}`, timestamp: Date.now(), videoUrl: currentPreview || undefined }]);
      setIsAnalyzingVideo(true);
      
      const formData = new FormData();
      formData.append("session_id", sessionId);
      formData.append("context_text", text);
      formData.append("input_type", inputType);
      formData.append("file", videoSource, filename);
      
      clearVideo();
      setInputText('');

      try {
        const res = await fetch('http://localhost:9120/api/journalist/visual-input/analyze', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        
        if (!res.ok) {
           throw new Error(data.message || data.detail || "Analysis failed");
        }
        
        setMessages(prev => [...prev, {
          id: (Date.now() + 1).toString(),
          role: 'ai',
          text: data.first_follow_up_question || "Interesting recording. Could you elaborate on what we just saw?",
          timestamp: Date.now(),
          decision: {
            intent_classification: 'video_analysis',
            internal_reasoning: data.short_summary || 'Analyzed screen recording',
            action: 'video_follow_up'
          }
        }]);
      } catch (err: any) {
        console.error(err);
        alert(err.message || "Failed to analyze video.");
      } finally {
        setIsAnalyzingVideo(false);
      }
      return;
    }
    
    if (selectedImage) {
      const currentPreview = imagePreview;
      setMessages(prev => [...prev, { id: Date.now().toString(), role: 'expert', text: `[Uploaded Image: ${selectedImage.name}] ${text}`, timestamp: Date.now(), imageUrl: currentPreview || undefined }]);
      setIsLoading(true);
      const formData = new FormData();
      formData.append("session_id", sessionId);
      formData.append("context_text", text);
      formData.append("input_type", "image");
      formData.append("file", selectedImage);
      
      clearImage();
      setInputText('');

      try {
        const res = await fetch('http://localhost:9120/api/journalist/visual-input/analyze', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        
        setMessages(prev => [...prev, {
          id: (Date.now() + 1).toString(),
          role: 'ai',
          text: data.first_follow_up_question || "Interesting. Can you tell me more about what we're looking at?",
          timestamp: Date.now(),
          decision: {
            intent_classification: 'visual_analysis',
            internal_reasoning: data.short_summary || 'Analyzed uploaded image',
            action: 'visual_follow_up'
          }
        }]);
      } catch (err) {
        console.error(err);
        alert("Failed to analyze image.");
      } finally {
        setIsLoading(false);
      }
      return;
    }

    setMessages(prev => [...prev, { id: Date.now().toString(), role: 'expert', text, timestamp: Date.now() }]);
    setInputText('');
    setIsLoading(true);
    
    try {
      const res = await fetch('http://localhost:9120/live-turn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          expert_answer: text,
          current_script_question: "General exploration", // Ideally mapped to active UI question
          active_block: activeBlock,
          tangent_count: tangentCount
        })
      });
      const data = await res.json();
      
      const intent = data.decision?.intent || 'unknown';
      if (intent === 'substantive') {
        setTangentCount(prev => prev + 1);
      } else if (intent === 'skip' || data.decision?.action === 'next_script_question') {
        setTangentCount(0);
      }
      
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        text: data.question || "Let's move on to the next topic.",
        timestamp: Date.now(),
        decision: {
          intent_classification: data.decision?.intent || 'unknown',
          internal_reasoning: data.decision?.reasoning || 'Backend copilot decision',
          action: data.decision?.action || 'next'
        }
      }]);
    } catch (err) {
      console.error(err);
      alert("Failed to get AI response.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleEndInterview = async () => {
    if (!confirm('Pause the interview and run the Homework Engine?')) return;
    if (!sessionId) return;
    
    setIsSynthesizing(true);
    try {
      await fetch(`http://localhost:9120/end-session/${sessionId}`, { method: 'POST' });
      navigate('/homework');
    } catch (err) {
      console.error(err);
      alert("Failed to synthesize session.");
      setIsSynthesizing(false);
    }
  };

  const handleNextBlock = () => {
    const currentIndex = scriptThemes.findIndex(t => t.theme_title === activeBlock);
    if (currentIndex >= 0 && currentIndex < scriptThemes.length - 1) {
      setActiveBlock(scriptThemes[currentIndex + 1].theme_title);
      setTangentCount(0);
    }
  };

  if (isSynthesizing) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', background: 'var(--bg)', color: 'var(--text)' }}>
        <Loader2 size={48} className="spin" style={{ color: 'var(--accent)', marginBottom: '20px' }} />
        <h2>Synthesizing Knowledge...</h2>
        <p style={{ color: 'var(--text-dim)' }}>Extracting tacit knowledge from session SESS-DEMO-DAY1 for Demo Expert.</p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', background: 'var(--bg)' }}>
      <div className="chat-page" style={{ flex: 1, position: 'relative', display: 'flex', flexDirection: 'column', height: '100%' }}>
      <header className="chat-header">
        <div className="chat-header-left">
          <button className="chat-logo-btn" onClick={() => setShowScriptSidebar(!showScriptSidebar)}>
            <BrainCircuit size={20} />
          </button>
          <div className="chat-header-info">
            <h1>Live Interview — Demo Expert</h1>
            <div className="chat-header-status">
              <div className="pulse-dot" style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--green)' }}></div>
              SESS-DEMO-DAY1 · Recording Active
            </div>
          </div>
        </div>
        
        <div className="chat-header-right" style={{ gap: '12px', display: 'flex', alignItems: 'center' }}>
          <div className="progress-section" style={{ marginRight: '16px', display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
            <label style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Active Block: {activeBlock}</label>
            <div style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text)' }}>
              Tangent Depth: {tangentCount}
            </div>
          </div>
          
          <button className="btn-ghost" style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }} onClick={handleNextBlock}>
            Next Block <ArrowRight size={14} style={{ marginLeft: '6px', verticalAlign: '-2px' }} />
          </button>
          <button className="btn-ghost" style={{ borderColor: 'var(--red)', color: 'var(--red)' }} onClick={handleEndInterview} disabled={isSynthesizing}>
            <PauseCircle size={14} style={{ marginRight: '6px', verticalAlign: '-2px' }} /> PAUSE INTERVIEW
          </button>
        </div>
      </header>

      <div className="chat-feed" ref={scrollRef}>
        {messages.map(m => (
          <div key={m.id} className={`msg msg-${m.role}`}>
            <div className="msg-label">
              {m.role === 'expert' ? 'Demo Expert' : 'AI Journalist'}
              {m.role === 'ai' && m.decision && (
                <button className="decision-toggle" onClick={() => setShowDecision(showDecision === m.id ? null : m.id)}>
                  <Zap size={10} /> AI Decision Log
                </button>
              )}
            </div>
            <div className="msg-bubble">
              {m.videoUrl && (
                <div style={{ marginBottom: '8px' }}>
                  <video src={m.videoUrl} controls style={{ maxWidth: '100%', maxHeight: '250px', borderRadius: '8px', border: '1px solid var(--border)' }} />
                </div>
              )}
              {m.imageUrl && (
                <div style={{ marginBottom: '8px' }}>
                  <img src={m.imageUrl} alt="Uploaded preview" style={{ maxWidth: '100%', maxHeight: '250px', borderRadius: '8px', border: '1px solid var(--border)' }} />
                </div>
              )}
              <div className="msg-text">{m.text}</div>
            </div>
            {m.role === 'ai' && m.decision && showDecision === m.id && (
              <div className="decision-section">
                <div className="decision-panel">
                  <div className="decision-grid">
                    <div className="decision-item">
                      <div className="decision-item-label"><Target size={10} /> Intent Classification</div>
                      <div className="decision-item-value">
                        <span className={`depth-tag depth-deep`}>{m.decision.intent_classification}</span>
                      </div>
                    </div>
                    <div className="decision-item">
                      <div className="decision-item-label"><Zap size={10} /> Action</div>
                      <div className="decision-item-value">{m.decision.action}</div>
                    </div>
                  </div>
                  <div className="decision-monologue">
                    <div className="decision-item-label"><Eye size={10} /> Internal Reasoning</div>
                    <p style={{ fontSize: '13px', color: 'var(--text-dim)', lineHeight: '1.6', marginTop: '6px' }}>{m.decision.internal_reasoning}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="msg msg-ai">
            <div className="typing-indicator">
              <div className="typing-dots">
                <div className="typing-dot" /><div className="typing-dot" /><div className="typing-dot" />
              </div>
              <span className="typing-text">Synthesizing follow-up...</span>
            </div>
          </div>
        )}
        {isAnalyzingVideo && (
          <div className="msg msg-ai">
            <div className="typing-indicator">
              <div className="typing-dots">
                <div className="typing-dot" /><div className="typing-dot" /><div className="typing-dot" />
              </div>
              <span className="typing-text">Understanding your recording...</span>
            </div>
          </div>
        )}
      </div>

      <div className="chat-input-bar" style={{ flexDirection: 'column', alignItems: 'center' }}>
        {videoPreview && (
          <div style={{ position: 'relative', width: 'fit-content', marginBottom: '10px', alignSelf: 'flex-start', marginLeft: '12%' }}>
            <video src={videoPreview} controls style={{ maxHeight: '150px', borderRadius: '8px', border: '1px solid var(--border)' }} />
            <button onClick={clearVideo} style={{ position: 'absolute', top: '-8px', right: '-8px', background: 'var(--red)', color: 'white', border: 'none', borderRadius: '50%', width: '20px', height: '20px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><X size={12} /></button>
          </div>
        )}
        {imagePreview && (
          <div style={{ position: 'relative', width: 'fit-content', marginBottom: '10px', alignSelf: 'flex-start', marginLeft: '12%' }}>
            <img src={imagePreview} alt="Preview" style={{ maxHeight: '100px', borderRadius: '8px', border: '1px solid var(--border)' }} />
            <button onClick={clearImage} style={{ position: 'absolute', top: '-8px', right: '-8px', background: 'var(--red)', color: 'white', border: 'none', borderRadius: '50%', width: '20px', height: '20px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><X size={12} /></button>
          </div>
        )}
        {isScreenRecording && (
          <div style={{ marginBottom: '10px', color: 'var(--red)', fontWeight: 'bold', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div className="typing-dot" style={{ background: 'var(--red)', animation: 'pulse 1s infinite' }} />
            Recording Screen & Mic: {Math.floor(screenRecordingTimer / 60).toString().padStart(2, '0')}:{(screenRecordingTimer % 60).toString().padStart(2, '0')}
          </div>
        )}
        <div className="chat-input-wrapper">
          <input 
            type="file" 
            accept="image/png, image/jpeg, image/webp" 
            ref={fileInputRef} 
            onChange={handleImageSelect} 
            style={{ display: 'none' }} 
          />
          <input 
            type="file" 
            accept="video/mp4, video/webm, video/quicktime" 
            ref={videoFileInputRef} 
            onChange={handleVideoSelect} 
            style={{ display: 'none' }} 
          />
          <button 
            className="mic-btn"
            onClick={() => fileInputRef.current?.click()}
            title="Upload Image"
          >
            <ImageIcon size={20} />
          </button>
          <button 
            className="mic-btn"
            onClick={() => videoFileInputRef.current?.click()}
            title="Upload Video"
          >
            <Film size={20} />
          </button>
          <button 
            className={`mic-btn ${isScreenRecording ? 'recording' : ''}`}
            onClick={isScreenRecording ? stopScreenRecording : startScreenRecording}
            title={isScreenRecording ? "Stop Screen Recording" : "Screen Share + Explain"}
            style={isScreenRecording ? { color: 'var(--red)' } : {}}
          >
            {isScreenRecording ? <StopCircle size={20} /> : <Monitor size={20} />}
          </button>
          <button 
            className={`mic-btn ${isRecording ? 'recording' : ''}`} 
            onClick={() => setIsRecording(!isRecording)}
            disabled={isTranscribing}
          >
            {isTranscribing ? <Loader2 size={20} className="spin" /> : (isRecording ? <MicOff size={20} /> : <Mic size={20} />)}
          </button>
          <textarea
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(inputText); }
            }}
            placeholder="Type expert's response..."
            className="chat-textarea"
            rows={1}
          />
          <button className="send-btn" onClick={() => handleSend(inputText)} disabled={isLoading || isAnalyzingVideo || (!inputText.trim() && !selectedImage && !recordedBlob)}>
            <Send size={20} />
          </button>
        </div>
      </div>
      </div>

      {showScriptSidebar && (
        <div className="script-sidebar" style={{ width: '400px', height: '100%', background: 'var(--bg-card)', borderLeft: '1px solid var(--border)', display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
          <div style={{ padding: '20px', borderBottom: '1px solid var(--border)', background: '#fff' }}>
            <h3 style={{ margin: 0, fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileText size={16} style={{ color: 'var(--accent)' }}/> Live Teleprompter
            </h3>
            <p style={{ margin: '4px 0 0', fontSize: '12px', color: 'var(--text-dim)' }}>Read these questions to guide the interview.</p>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
            {scriptThemes.map(theme => (
              <div key={theme.theme_id} style={{ marginBottom: '24px' }}>
                <h4 style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-dim)', marginBottom: '12px', display: 'flex', justifyContent: 'space-between' }}>
                  <span>{theme.theme_title}</span>
                  <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>{theme.tentative_duration}m</span>
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {theme.questions.map((q: any) => (
                    <div key={q.id} style={{ background: '#f8fafc', border: '1px solid var(--border)', borderRadius: '8px', padding: '12px' }}>
                      <p style={{ margin: 0, fontSize: '13px', lineHeight: '1.5', fontWeight: 500 }}>"{q.question_text}"</p>
                      <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '8px', fontStyle: 'italic' }}>
                        Rationale: {q.rationale}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
            {scriptThemes.length === 0 && <p style={{ fontSize: '13px', color: 'var(--text-dim)' }}>Loading script...</p>}
          </div>
        </div>
      )}
    </div>
  );
};

export default InterviewPage;
