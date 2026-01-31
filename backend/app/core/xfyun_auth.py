from __future__ import annotations

import base64
import hashlib
import hmac
import urllib.parse
from typing import Any, Dict, Tuple


def _urlencode(s: str) -> str:
    return urllib.parse.quote(str(s), safe="")


def build_signature(params: Dict[str, Any], *, access_key_secret: str) -> Tuple[str, str]:
    items = []
    for k, v in params.items():
        if k == "signature":
            continue
        items.append((str(k), _urlencode(k), _urlencode(v)))
    items.sort(key=lambda t: t[0])
    base_string = "&".join([f"{ek}={ev}" for _, ek, ev in items])
    mac = hmac.new(access_key_secret.encode("utf-8"), base_string.encode("utf-8"), hashlib.sha1).digest()
    signature = base64.b64encode(mac).decode("utf-8")
    return signature, base_string
