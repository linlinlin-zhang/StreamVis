from __future__ import annotations

import json
import mimetypes
import os
import uuid
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional


class MoonshotError(RuntimeError):
    pass


@dataclass(frozen=True)
class UploadedFile:
    id: str
    filename: str
    purpose: str
    raw: Dict[str, Any]


def _http_json(req: urllib.request.Request, timeout_s: float) -> Dict[str, Any]:
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8") if e.fp else ""
        raise MoonshotError(f"http_error status={e.code} body={raw}") from e
    except Exception as e:
        raise MoonshotError(str(e)) from e


class MoonshotFilesClient:
    def __init__(self, *, api_key: str, base_url: str) -> None:
        if not api_key:
            raise ValueError("api_key required")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    def _auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    def upload(self, *, file_bytes: bytes, filename: str, purpose: str = "file-extract") -> UploadedFile:
        boundary = f"----streamvis-{uuid.uuid4().hex}"
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        parts = []
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="purpose"\r\n\r\n'
                f"{purpose}\r\n"
            ).encode("utf-8")
        )
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode("utf-8")
        )
        parts.append(file_bytes)
        parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
        body = b"".join(parts)

        req = urllib.request.Request(f"{self._base_url}/files", data=body, method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        req.add_header("Content-Length", str(len(body)))
        for k, v in self._auth_headers().items():
            req.add_header(k, v)

        res = _http_json(req, timeout_s=90.0)
        file_id = res.get("id") or ""
        if not file_id:
            raise MoonshotError(f"missing file id: {res}")
        return UploadedFile(id=str(file_id), filename=str(res.get("filename") or filename), purpose=str(res.get("purpose") or purpose), raw=res)

    def retrieve_content(self, *, file_id: str) -> str:
        req = urllib.request.Request(f"{self._base_url}/files/{file_id}/content", method="GET")
        for k, v in self._auth_headers().items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=60.0) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8") if e.fp else ""
            raise MoonshotError(f"http_error status={e.code} body={raw}") from e
        except Exception as e:
            raise MoonshotError(str(e)) from e

    def delete(self, *, file_id: str) -> None:
        req = urllib.request.Request(f"{self._base_url}/files/{file_id}", method="DELETE")
        for k, v in self._auth_headers().items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=30.0):
                return
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8") if e.fp else ""
            raise MoonshotError(f"http_error status={e.code} body={raw}") from e
        except Exception as e:
            raise MoonshotError(str(e)) from e

