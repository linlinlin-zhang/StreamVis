import React, { useEffect, useMemo, useRef, useState } from 'react';
import { X, Mic, Square, Save, Loader2 } from 'lucide-react';
import './VoicePrintModal.css';

const WAV_MIME = 'audio/wav';

const writeWav = (samples, sampleRate) => {
  const numChannels = 1;
  const bytesPerSample = 2;
  const blockAlign = numChannels * bytesPerSample;
  const byteRate = sampleRate * blockAlign;
  const dataSize = samples.length * bytesPerSample;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);
  let offset = 0;

  const writeString = (s) => {
    for (let i = 0; i < s.length; i++) view.setUint8(offset + i, s.charCodeAt(i));
    offset += s.length;
  };

  writeString('RIFF');
  view.setUint32(offset, 36 + dataSize, true);
  offset += 4;
  writeString('WAVE');
  writeString('fmt ');
  view.setUint32(offset, 16, true);
  offset += 4;
  view.setUint16(offset, 1, true);
  offset += 2;
  view.setUint16(offset, numChannels, true);
  offset += 2;
  view.setUint32(offset, sampleRate, true);
  offset += 4;
  view.setUint32(offset, byteRate, true);
  offset += 4;
  view.setUint16(offset, blockAlign, true);
  offset += 2;
  view.setUint16(offset, 16, true);
  offset += 2;
  writeString('data');
  view.setUint32(offset, dataSize, true);
  offset += 4;

  for (let i = 0; i < samples.length; i++, offset += 2) view.setInt16(offset, samples[i], true);
  return new Blob([buffer], { type: WAV_MIME });
};

const downsampleTo16k = (float32Array, inputSampleRate) => {
  const outputSampleRate = 16000;
  if (inputSampleRate === outputSampleRate) {
    const out = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) out[i] = Math.max(-1, Math.min(1, float32Array[i])) * 0x7fff;
    return out;
  }
  const ratio = inputSampleRate / outputSampleRate;
  const newLength = Math.round(float32Array.length / ratio);
  const out = new Int16Array(newLength);
  let offsetResult = 0;
  let offsetBuffer = 0;
  while (offsetResult < out.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
    let accum = 0;
    let count = 0;
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < float32Array.length; i++) {
      accum += float32Array[i];
      count++;
    }
    const sample = count ? accum / count : 0;
    out[offsetResult] = Math.max(-1, Math.min(1, sample)) * 0x7fff;
    offsetResult++;
    offsetBuffer = nextOffsetBuffer;
  }
  return out;
};

const VoicePrintModal = ({ open, onClose, onRegistered }) => {
  const [status, setStatus] = useState('idle');
  const [uid, setUid] = useState('');
  const [speakerName, setSpeakerName] = useState('');
  const [error, setError] = useState('');
  const [featureId, setFeatureId] = useState('');

  const streamRef = useRef(null);
  const audioCtxRef = useRef(null);
  const processorRef = useRef(null);
  const sourceRef = useRef(null);
  const startTsRef = useRef(0);
  const samplesRef = useRef([]);
  const totalSamplesRef = useRef(0);

  const seconds = useMemo(() => {
    if (status !== 'recording') return 0;
    return Math.floor((Date.now() - startTsRef.current) / 1000);
  }, [status]);

  useEffect(() => {
    if (!open) {
      setStatus('idle');
      setError('');
      setFeatureId('');
      setSpeakerName('');
      setUid('');
    }
  }, [open]);

  const stopRecording = async () => {
    setStatus('stopping');
    try {
      processorRef.current?.disconnect();
      sourceRef.current?.disconnect();
      await audioCtxRef.current?.close();
      streamRef.current?.getTracks()?.forEach((t) => t.stop());
    } catch {}
    processorRef.current = null;
    sourceRef.current = null;
    audioCtxRef.current = null;
    streamRef.current = null;
    setStatus('ready');
  };

  const startRecording = async () => {
    setError('');
    setFeatureId('');
    setStatus('requesting');
    samplesRef.current = [];
    totalSamplesRef.current = 0;
    startTsRef.current = Date.now();
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      audioCtxRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      sourceRef.current = source;
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;
      processor.onaudioprocess = (e) => {
        if (status !== 'recording') return;
        const data = e.inputBuffer.getChannelData(0);
        const pcm16 = downsampleTo16k(data, audioCtx.sampleRate);
        samplesRef.current.push(pcm16);
        totalSamplesRef.current += pcm16.length;
      };
      source.connect(processor);
      processor.connect(audioCtx.destination);
      setStatus('recording');
    } catch (e) {
      setError(e?.message || '无法访问麦克风');
      setStatus('idle');
    }
  };

  const upload = async () => {
    const durSec = totalSamplesRef.current / 16000;
    if (durSec < 10) {
      setError('声纹注册音频需至少 10 秒');
      return;
    }
    if (durSec > 60) {
      setError('声纹注册音频需不超过 60 秒');
      return;
    }
    setStatus('uploading');
    try {
      const merged = new Int16Array(totalSamplesRef.current);
      let offset = 0;
      for (const c of samplesRef.current) {
        merged.set(c, offset);
        offset += c.length;
      }
      const wavBlob = writeWav(merged, 16000);
      const form = new FormData();
      form.append('file', new File([wavBlob], `${speakerName || 'speaker'}.wav`, { type: WAV_MIME }));
      if (uid) form.append('uid', uid);
      const resp = await fetch('http://localhost:8000/api/xfyun/voiceprint/register', { method: 'POST', body: form });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data?.detail || '注册失败');
      const fid = data?.feature_id || '';
      if (!fid) throw new Error(data?.desc || '未返回 feature_id');
      setFeatureId(fid);
      setStatus('done');
      onRegistered?.({ speakerName: speakerName || 'speaker', featureId: fid });
    } catch (e) {
      setError(e?.message || '注册失败');
      setStatus('ready');
    }
  };

  if (!open) return null;

  const getStatusDisplay = () => {
    switch (status) {
      case 'recording':
        return { icon: <Square size={18} />, text: `停止录音 (${seconds}s)`, variant: 'danger' };
      case 'requesting':
        return { icon: <Loader2 size={18} className="animate-spin" />, text: '请求麦克风...', variant: 'secondary', disabled: true };
      case 'stopping':
        return { icon: <Loader2 size={18} className="animate-spin" />, text: '停止中...', variant: 'secondary', disabled: true };
      case 'ready':
        return { icon: <Save size={18} />, text: '注册声纹', variant: 'primary' };
      case 'uploading':
        return { icon: <Loader2 size={18} className="animate-spin" />, text: '上传中...', variant: 'primary', disabled: true };
      default:
        return { icon: <Mic size={18} />, text: '开始录音', variant: 'secondary' };
    }
  };

  const statusDisplay = getStatusDisplay();

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-container">
        <div className="modal-header">
          <div className="modal-title-group">
            <h2 className="modal-title">声纹注册</h2>
            <p className="modal-subtitle">录制 10-60 秒的语音样本</p>
          </div>
          <button className="modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {/* 录音状态指示器 */}
          {status === 'recording' && (
            <div className="recording-indicator">
              <div className="recording-waves">
                <span></span>
                <span></span>
                <span></span>
                <span></span>
                <span></span>
              </div>
              <span className="recording-time">{seconds} 秒</span>
            </div>
          )}

          <div className="form-group">
            <label className="form-label">发言人名称</label>
            <input
              type="text"
              className="form-input"
              value={speakerName}
              onChange={(e) => setSpeakerName(e.target.value)}
              placeholder="例如：张三 / Speaker A"
              disabled={status === 'recording' || status === 'uploading'}
            />
          </div>

          <div className="form-group">
            <label className="form-label">用户 ID（可选）</label>
            <input
              type="text"
              className="form-input"
              value={uid}
              onChange={(e) => setUid(e.target.value)}
              placeholder="用于区分不同用户"
              disabled={status === 'recording' || status === 'uploading'}
            />
          </div>

          {error && (
            <div className="alert alert-error">
              {error}
            </div>
          )}

          {featureId && (
            <div className="alert alert-success">
              <div className="success-title">✓ 注册成功</div>
              <div className="success-id">ID: {featureId}</div>
            </div>
          )}

          <div className="modal-hint">
            <p>💡 提示：</p>
            <ul>
              <li>请在安静环境下录音</li>
              <li>保持正常语速，朗读任意文本</li>
              <li>录音时长需在 10-60 秒之间</li>
              <li>注册后可在语音转写中识别说话人</li>
            </ul>
          </div>
        </div>

        <div className="modal-footer">
          {status !== 'idle' && status !== 'requesting' ? (
            <button
              className={`btn btn-${statusDisplay.variant}`}
              onClick={status === 'recording' ? stopRecording : upload}
              disabled={statusDisplay.disabled}
            >
              {statusDisplay.icon}
              <span>{statusDisplay.text}</span>
            </button>
          ) : (
            <button
              className="btn btn-secondary"
              onClick={startRecording}
              disabled={status === 'requesting'}
            >
              <Mic size={18} />
              <span>开始录音</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default VoicePrintModal;
