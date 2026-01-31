from __future__ import annotations

import base64
import os
import socket
import ssl
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import get_settings
from app.core.xfyun_rtasr import build_rtasr_url


def main() -> None:
    s = get_settings()
    url = build_rtasr_url(
        base_url=s.xfyun_rtasr_base_url,
        app_id=s.xfyun_app_id,
        access_key_id=s.xfyun_access_key_id,
        access_key_secret=s.xfyun_access_key_secret,
        lang=s.xfyun_lang,
        audio_encode=s.xfyun_audio_encode,
        samplerate=s.xfyun_samplerate,
        role_type=s.xfyun_role_type,
        feature_ids=s.xfyun_feature_ids,
        eng_spk_match=s.xfyun_eng_spk_match,
        uuid_str="ping",
    )
    pu = urllib.parse.urlparse(url)
    host = pu.hostname or ""
    path = pu.path + ("?" + pu.query if pu.query else "")
    key = base64.b64encode(os.urandom(16)).decode("utf-8")
    req = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    ).encode("utf-8")

    ctx = ssl.create_default_context()
    sock = socket.create_connection((host, 443), timeout=6)
    ss = ctx.wrap_socket(sock, server_hostname=host)
    ss.settimeout(4)
    ss.sendall(req)
    data = b""
    try:
        while b"\r\n\r\n" not in data and len(data) < 8192:
            chunk = ss.recv(1024)
            if not chunk:
                break
            data += chunk
    except Exception:
        pass
    finally:
        try:
            ss.close()
        except Exception:
            pass

    head = data.split(b"\r\n\r\n")[0].decode("utf-8", "ignore").splitlines()
    if not head:
        print("empty response")
        return
    print("status_line:", head[0])
    for line in head[1:8]:
        print("hdr:", line)


if __name__ == "__main__":
    main()

