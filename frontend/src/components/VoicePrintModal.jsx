import React, { useEffect, useMemo, useRef, useState } from 'react';
import { X, Mic, Square, Save } from 'lucide-react';

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
    } catch {
    } finally {
      processorRef.current = null;
      sourceRef.current = null;
      audioCtxRef.current = null;
      streamRef.current = null;
    }
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
      setError('声纹注册音频需至少 10 秒。');
      return;
    }
    if (durSec > 60) {
      setError('声纹注册音频需不超过 60 秒。');
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

  return (
    <div className="modal-mask" role="dialog" aria-modal="true">
      <div className="modal-card">
        <div className="modal-header">
          <div className="modal-title">声纹注册（10–60 秒）</div>
          <button className="modal-close" type="button" onClick={onClose}>
            <X size={16} />
          </button>
        </div>
        <div className="modal-body">
          <div className="modal-row">
            <label>发言人名称</label>
            <input value={speakerName} onChange={(e) => setSpeakerName(e.target.value)} placeholder="例如：张三 / Speaker A" />
          </div>
          <div className="modal-row">
            <label>uid（可选）</label>
            <input value={uid} onChange={(e) => setUid(e.target.value)} placeholder="用于区分用户（可不填）" />
          </div>
          <div className="modal-actions">
            {status !== 'recording' ? (
              <button className="btn" type="button" onClick={startRecording} disabled={status === 'uploading' || status === 'requesting'}>
                <Mic size={16} />
                开始录音
              </button>
            ) : (
              <button className="btn" type="button" onClick={stopRecording}>
                <Square size={16} />
                停止（已录 {seconds}s）
              </button>
            )}
            <button className="btn primary" type="button" onClick={upload} disabled={status !== 'ready'}>
              <Save size={16} />
              注册声纹
            </button>
          </div>
          {featureId ? <div className="modal-success">feature_id：{featureId}</div> : null}
          {error ? <div className="modal-error">{error}</div> : null}
          <div className="modal-hint">注册后可在语音转写中开启“注册声纹模式”，说话人分离会更稳定。</div>
        </div>
      </div>
    </div>
  );
};

export default VoicePrintModal;

