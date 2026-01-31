from __future__ import annotations

import base64
import json
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.xfyun_auth import build_signature


@dataclass(frozen=True)
class VoicePrintResult:
    code: str
    desc: str
    feature_id: str
    raw: Dict[str, Any]


def _datetime_tz() -> str:
    import time

    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime())


def _post_json(url: str, *, payload: Dict[str, Any], signature: str, timeout_s: float = 30.0) -> Dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(url, data=body, headers={"Content-Type": "application/json", "signature": signature})
    with urlopen(req, timeout=timeout_s) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def register_voiceprint(
    *,
    register_url: str,
    app_id: str,
    access_key_id: str,
    access_key_secret: str,
    audio_bytes: bytes,
    audio_type: str = "raw",
    uid: str = "",
) -> VoicePrintResult:
    q: Dict[str, Any] = {
        "appId": app_id,
        "accessKeyId": access_key_id,
        "dateTime": _datetime_tz(),
        "signatureRandom": uuid.uuid4().hex[:12],
    }
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    body: Dict[str, Any] = {"audio_data": audio_b64, "audio_type": audio_type}
    if uid:
        body["uid"] = uid

    sig, _ = build_signature(q, access_key_secret=access_key_secret)
    url = register_url
    if "?" not in url:
        url = url + "?" + urlencode(q)
    resp = _post_json(url, payload=body, signature=sig)
    data_str = resp.get("data") or "{}"
    feature_id = ""
    try:
        data_obj = json.loads(data_str) if isinstance(data_str, str) else dict(data_str)
        feature_id = str((data_obj or {}).get("feature_id") or "")
    except Exception:
        feature_id = ""
    return VoicePrintResult(code=str(resp.get("code") or ""), desc=str(resp.get("desc") or ""), feature_id=feature_id, raw=resp)


def update_voiceprint(
    *,
    update_url: str,
    app_id: str,
    access_key_id: str,
    access_key_secret: str,
    feature_id: str,
    audio_bytes: bytes,
    audio_type: str = "raw",
) -> Dict[str, Any]:
    q: Dict[str, Any] = {
        "appId": app_id,
        "accessKeyId": access_key_id,
        "dateTime": _datetime_tz(),
        "signatureRandom": uuid.uuid4().hex[:12],
    }
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    body: Dict[str, Any] = {"audio_data": audio_b64, "audio_type": audio_type, "feature_id": feature_id}
    sig, _ = build_signature(q, access_key_secret=access_key_secret)
    url = update_url
    if "?" not in url:
        url = url + "?" + urlencode(q)
    return _post_json(url, payload=body, signature=sig)


def delete_voiceprint(
    *,
    delete_url: str,
    app_id: str,
    access_key_id: str,
    access_key_secret: str,
    feature_ids: list[str],
) -> Dict[str, Any]:
    q: Dict[str, Any] = {
        "appId": app_id,
        "accessKeyId": access_key_id,
        "dateTime": _datetime_tz(),
        "signatureRandom": uuid.uuid4().hex[:12],
    }
    body: Dict[str, Any] = {"feature_ids": feature_ids}
    sig, _ = build_signature(q, access_key_secret=access_key_secret)
    url = delete_url
    if "?" not in url:
        url = url + "?" + urlencode(q)
    return _post_json(url, payload=body, signature=sig)
