from __future__ import annotations

import json
import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Optional, Tuple

import websockets

from app.core.xfyun_auth import build_signature


@dataclass(frozen=True)
class TranscriptEvent:
    segment_id: str
    speaker: str
    text: str
    is_final: bool
    raw: Dict[str, Any]


def _now_utc_string() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime())


def build_rtasr_url(
    *,
    base_url: str,
    app_id: str,
    access_key_id: str,
    access_key_secret: str,
    lang: str = "autodialect",
    audio_encode: str = "pcm_s16le",
    samplerate: int = 16000,
    role_type: int = 2,
    feature_ids: str = "",
    eng_spk_match: int = 0,
    pd: str = "",
    eng_punc: str = "",
    uuid_str: Optional[str] = None,
) -> str:
    params: Dict[str, Any] = {
        "appId": app_id,
        "accessKeyId": access_key_id,
        "utc": _now_utc_string(),
        "lang": lang,
        "audio_encode": audio_encode,
        "samplerate": int(samplerate),
        "role_type": int(role_type),
    }
    if uuid_str:
        params["uuid"] = uuid_str
    if feature_ids:
        params["feature_ids"] = feature_ids
    if eng_spk_match:
        params["eng_spk_match"] = int(eng_spk_match)
    if pd:
        params["pd"] = pd
    if eng_punc:
        params["eng_punc"] = eng_punc

    sig, _ = build_signature(params, access_key_secret=access_key_secret)
    params["signature"] = sig

    from urllib.parse import urlencode

    return f"{base_url}?{urlencode(params)}"


def _extract_text_and_speaker(payload: Dict[str, Any]) -> Tuple[str, str, bool]:
    action = str(payload.get("action") or "")
    is_final = action == "result"
    speaker = "spk0"

    data = payload.get("data")
    if isinstance(data, str):
        try:
            data_obj = json.loads(data)
        except Exception:
            data_obj = None
    else:
        data_obj = data if isinstance(data, dict) else None

    if isinstance(data_obj, dict):
        cn = data_obj.get("cn") if isinstance(data_obj.get("cn"), dict) else None
        st = cn.get("st") if cn and isinstance(cn.get("st"), dict) else None
        if st:
            rl = st.get("rl") or st.get("role") or st.get("spk") or st.get("speaker")
            if rl is not None:
                speaker = f"spk{rl}"
            rt = st.get("rt") if isinstance(st.get("rt"), list) else []
            words = []
            for r in rt:
                ws = r.get("ws") if isinstance(r, dict) else None
                if not isinstance(ws, list):
                    continue
                for w in ws:
                    cw = w.get("cw") if isinstance(w, dict) else None
                    if not isinstance(cw, list) or not cw:
                        continue
                    top = cw[0]
                    wtxt = top.get("w") if isinstance(top, dict) else ""
                    if wtxt:
                        words.append(str(wtxt))
            text = "".join(words).strip()
            return text, speaker, is_final

    text = str(data or "").strip()
    return text, speaker, is_final


async def stream_rtasr(
    *,
    base_url: str,
    app_id: str,
    access_key_id: str,
    access_key_secret: str,
    audio_iter: AsyncIterator[bytes],
    lang: str = "autodialect",
    audio_encode: str = "pcm_s16le",
    samplerate: int = 16000,
    role_type: int = 2,
    feature_ids: str = "",
    eng_spk_match: int = 0,
) -> AsyncIterator[TranscriptEvent]:
    sess = uuid.uuid4().hex[:8]
    url = build_rtasr_url(
        base_url=base_url,
        app_id=app_id,
        access_key_id=access_key_id,
        access_key_secret=access_key_secret,
        lang=lang,
        audio_encode=audio_encode,
        samplerate=samplerate,
        role_type=role_type,
        feature_ids=feature_ids,
        eng_spk_match=eng_spk_match,
        uuid_str=sess,
    )

    async with websockets.connect(url, max_size=8 * 1024 * 1024) as ws:
        async def _sender() -> None:
            async for chunk in audio_iter:
                if not chunk:
                    continue
                await ws.send(chunk)

        sender_task = asyncio.create_task(_sender())

        try:
            while True:
                msg = await ws.recv()
                if isinstance(msg, bytes):
                    continue
                try:
                    payload = json.loads(msg)
                except Exception:
                    continue
                if str(payload.get("action") or "") == "error":
                    yield TranscriptEvent(segment_id=f"seg_{sess}_error", speaker="sys", text=str(payload.get("desc") or ""), is_final=True, raw=payload)
                    break
                text, speaker, is_final = _extract_text_and_speaker(payload)
                if not text:
                    continue
                seg_id = payload.get("sid") or f"seg_{sess}_{uuid.uuid4().hex[:6]}"
                yield TranscriptEvent(segment_id=str(seg_id), speaker=str(speaker), text=text, is_final=bool(is_final), raw=payload)
        finally:
            if sender_task:
                sender_task.cancel()
