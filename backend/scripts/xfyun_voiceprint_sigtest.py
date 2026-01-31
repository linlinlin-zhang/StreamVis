from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import time
import uuid
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import get_settings


def _enc(v: Any) -> str:
    return urllib.parse.quote(str(v), safe="")


def _base_pairs(params: Dict[str, Any], *, encode_key: bool, encode_val: bool, skip_empty: bool) -> str:
    items = []
    for k, v in params.items():
        if k == "signature":
            continue
        if v is None:
            continue
        vs = str(v)
        if skip_empty and vs == "":
            continue
        kk = _enc(k) if encode_key else str(k)
        vv = _enc(vs) if encode_val else vs
        items.append((str(k), kk, vv))
    items.sort(key=lambda t: t[0])
    return "&".join([f"{kk}={vv}" for _, kk, vv in items])


def _hmac_b64(secret: str, msg: str, algo: str) -> str:
    if algo == "sha1":
        digestmod = hashlib.sha1
    elif algo == "sha256":
        digestmod = hashlib.sha256
    else:
        raise ValueError(algo)
    mac = hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), digestmod).digest()
    return base64.b64encode(mac).decode("utf-8")


def _md5_hex(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def try_call(signature: str, *, url: str, q: Dict[str, Any], body: Dict[str, Any]) -> Tuple[str, str]:
    full = url + ("?" + urllib.parse.urlencode(q) if "?" not in url else "")
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(full, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("signature", signature)
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = resp.read().decode("utf-8")
    obj = json.loads(raw) if raw else {}
    return str(obj.get("code") or ""), str(obj.get("desc") or "")


def main() -> None:
    s = get_settings()
    if not s.xfyun_voiceprint_delete_url:
        print("missing XFYUN_VOICEPRINT_DELETE_URL")
        return
    q = {
        "appId": s.xfyun_app_id,
        "accessKeyId": s.xfyun_access_key_id,
        "dateTime": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
        "signatureRandom": uuid.uuid4().hex[:12],
    }
    body = {"feature_ids": [f"ping_{int(time.time())}"]}
    merged = {**q, **body}
    merged_q_only = dict(q)

    variants: Dict[str, Callable[[], str]] = {
        "sha1_encode_kv_skip_empty": lambda: _hmac_b64(s.xfyun_access_key_secret, _base_pairs(merged, encode_key=True, encode_val=True, skip_empty=True), "sha1"),
        "sha1_encode_kv_keep_empty": lambda: _hmac_b64(s.xfyun_access_key_secret, _base_pairs(merged, encode_key=True, encode_val=True, skip_empty=False), "sha1"),
        "sha1_encode_v_only": lambda: _hmac_b64(s.xfyun_access_key_secret, _base_pairs(merged, encode_key=False, encode_val=True, skip_empty=True), "sha1"),
        "sha1_no_encode": lambda: _hmac_b64(s.xfyun_access_key_secret, _base_pairs(merged, encode_key=False, encode_val=False, skip_empty=True), "sha1"),
        "sha256_encode_kv": lambda: _hmac_b64(s.xfyun_access_key_secret, _base_pairs(merged, encode_key=True, encode_val=True, skip_empty=True), "sha256"),
        "sha256_encode_v_only": lambda: _hmac_b64(s.xfyun_access_key_secret, _base_pairs(merged, encode_key=False, encode_val=True, skip_empty=True), "sha256"),
        "sha1_md5_then_hmac": lambda: _hmac_b64(s.xfyun_access_key_secret, _md5_hex(_base_pairs(merged, encode_key=True, encode_val=True, skip_empty=True)), "sha1"),
        "sha1_encode_kv_query_only": lambda: _hmac_b64(s.xfyun_access_key_secret, _base_pairs(merged_q_only, encode_key=True, encode_val=True, skip_empty=True), "sha1"),
        "sha256_encode_kv_query_only": lambda: _hmac_b64(s.xfyun_access_key_secret, _base_pairs(merged_q_only, encode_key=True, encode_val=True, skip_empty=True), "sha256"),
    }

    for name, fn in variants.items():
        try:
            sig = fn()
            code, desc = try_call(sig, url=s.xfyun_voiceprint_delete_url, q=q, body=body)
            print(name, "=>", code, desc[:120])
        except Exception as e:
            print(name, "=>", "EXC", str(e)[:120])


if __name__ == "__main__":
    main()
