from __future__ import annotations

import asyncio
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


class BailianError(RuntimeError):
    pass


@dataclass(frozen=True)
class BailianImageResult:
    task_id: str
    urls: List[str]
    raw: Dict[str, Any]


def _http_json(method: str, url: str, *, headers: Dict[str, str], body: Optional[Dict[str, Any]] = None, timeout_s: float = 30.0) -> Dict[str, Any]:
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8") if e.fp else ""
        raise BailianError(f"http_error status={e.code} body={raw}") from e
    except Exception as e:
        raise BailianError(str(e)) from e


class BailianImagesClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://dashscope.aliyuncs.com",
        workspace: Optional[str] = None,
        t2i_endpoint: str = "/api/v1/services/aigc/text2image/image-synthesis",
        i2i_endpoint: str = "/api/v1/services/aigc/image2image/image-synthesis",
        task_endpoint_prefix: str = "/api/v1/tasks/",
    ) -> None:
        if not api_key:
            raise ValueError("api_key required")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._workspace = workspace
        self._t2i_endpoint = t2i_endpoint
        self._i2i_endpoint = i2i_endpoint
        self._task_prefix = task_endpoint_prefix

    def _headers(self, *, async_enable: bool) -> Dict[str, str]:
        h = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if async_enable:
            h["X-DashScope-Async"] = "enable"
        if self._workspace:
            h["X-DashScope-WorkSpace"] = self._workspace
        return h

    def create_text_to_image_task(
        self,
        *,
        model: str,
        prompt: str,
        negative_prompt: str = "",
        size: str = "1024*1024",
        n: int = 1,
        style: Optional[str] = None,
    ) -> str:
        body: Dict[str, Any] = {
            "model": model,
            "input": {"prompt": prompt},
            "parameters": {"size": size, "n": int(n)},
        }
        if negative_prompt:
            body["input"]["negative_prompt"] = negative_prompt
        if style:
            body["parameters"]["style"] = style

        res = _http_json(
            "POST",
            f"{self._base_url}{self._t2i_endpoint}",
            headers=self._headers(async_enable=True),
            body=body,
            timeout_s=60.0,
        )
        out = res.get("output") or {}
        task_id = out.get("task_id")
        if not task_id:
            raise BailianError(f"missing task_id: {res}")
        return str(task_id)

    def create_image_edit_task(
        self,
        *,
        model: str,
        function: str,
        prompt: str,
        base_image_url: str,
        n: int = 1,
    ) -> str:
        body: Dict[str, Any] = {
            "model": model,
            "input": {"function": function, "prompt": prompt, "base_image_url": base_image_url},
            "parameters": {"n": int(n)},
        }
        res = _http_json(
            "POST",
            f"{self._base_url}{self._i2i_endpoint}",
            headers=self._headers(async_enable=True),
            body=body,
            timeout_s=60.0,
        )
        out = res.get("output") or {}
        task_id = out.get("task_id")
        if not task_id:
            raise BailianError(f"missing task_id: {res}")
        return str(task_id)

    def get_task(self, task_id: str) -> Dict[str, Any]:
        return _http_json(
            "GET",
            f"{self._base_url}{self._task_prefix}{task_id}",
            headers={"Authorization": f"Bearer {self._api_key}"},
            body=None,
            timeout_s=30.0,
        )

    async def wait_task(
        self,
        task_id: str,
        *,
        timeout_s: float = 90.0,
        poll_interval_s: float = 0.8,
    ) -> BailianImageResult:
        start = time.time()
        last: Dict[str, Any] = {}
        while True:
            last = await asyncio.to_thread(self.get_task, task_id)
            out = last.get("output") or {}
            status = str(out.get("task_status") or "").upper()

            if status == "SUCCEEDED":
                urls: List[str] = []
                for r in (out.get("results") or []):
                    if isinstance(r, dict) and r.get("url"):
                        urls.append(str(r["url"]))
                if not urls:
                    raise BailianError(f"task succeeded but no urls: {last}")
                return BailianImageResult(task_id=task_id, urls=urls, raw=last)

            if status in {"FAILED", "UNKNOWN"}:
                code = out.get("code") or last.get("code")
                message = out.get("message") or last.get("message")
                raise BailianError(f"task failed status={status} code={code} message={message}")

            if time.time() - start > timeout_s:
                raise BailianError(f"task timeout status={status}")

            await asyncio.sleep(poll_interval_s)

