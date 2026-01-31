from __future__ import annotations

import asyncio
import os
import sys
import time
from typing import Any, Dict, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.bailian_images import BailianError, BailianImagesClient
from app.core.config import get_settings
from app.core.kimi_client import KimiClient, KimiError
from app.core.moonshot_files import MoonshotError, MoonshotFilesClient
from app.core.xfyun_rtasr import build_rtasr_url
from app.core.xfyun_voiceprint import delete_voiceprint


def _mask(s: str) -> str:
    if not s:
        return ""
    if len(s) <= 6:
        return "*" * len(s)
    return s[:2] + "*" * (len(s) - 4) + s[-2:]


def _ok(msg: str) -> None:
    print(f"[OK] {msg}")


def _warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}")


def _bool(v: bool) -> str:
    return "on" if v else "off"


def _check_kimi(settings) -> None:
    if not settings.moonshot_api_key:
        _warn("Kimi: 未配置 MOONSHOT_API_KEY（跳过实际连通性测试）")
        return

    client = KimiClient(
        api_key=settings.moonshot_api_key,
        base_url=settings.moonshot_base_url,
        model=settings.moonshot_model,
        timeout_s=30.0,
    )
    try:
        resp = client.chat(
            messages=[{"role": "system", "content": "你是连通性测试。"}, {"role": "user", "content": "ping"}],
            temperature=0.0,
            max_tokens=8,
            stream=False,
        )
        choices = resp.get("choices") or []
        msg = (choices[0] or {}).get("message") if choices else {}
        content = (msg or {}).get("content") or ""
        _ok(f"Kimi chat: 可用（model={settings.moonshot_model} enable={_bool(settings.enable_kimi)}）返回={str(content)[:30]!r}")
    except KimiError as e:
        _fail(f"Kimi chat: 失败（model={settings.moonshot_model}）{str(e)}")


def _check_kimi_files(settings) -> None:
    if not settings.moonshot_api_key:
        _warn("Kimi Files: 未配置 MOONSHOT_API_KEY（跳过）")
        return
    client = MoonshotFilesClient(api_key=settings.moonshot_api_key, base_url=settings.moonshot_base_url)
    data = b"streamvis ping"
    try:
        uploaded = client.upload(file_bytes=data, filename="ping.txt", purpose="file-extract")
        content = client.retrieve_content(file_id=uploaded.id)
        client.delete(file_id=uploaded.id)
        if content is None:
            _fail("Kimi Files: 上传/读取返回空")
        else:
            _ok(f"Kimi Files: 可用（base_url={settings.moonshot_base_url}）读取长度={len(str(content))}")
    except MoonshotError as e:
        _fail(f"Kimi Files: 失败 {str(e)}")


def _check_dashscope_images(settings) -> None:
    if not settings.dashscope_api_key:
        _warn("DashScope 图片: 未配置 DASHSCOPE_API_KEY（跳过）")
        return
    try:
        cli = BailianImagesClient(
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
            workspace=settings.dashscope_workspace or None,
        )
        try:
            cli.get_task("task_not_exist_ping")
            _ok("DashScope 图片: get_task 返回成功（非预期但说明可连通）")
        except BailianError as e:
            s = str(e)
            if "status=401" in s or "Unauthorized" in s:
                _fail("DashScope 图片: 鉴权失败（DASHSCOPE_API_KEY / workspace 可能不对）")
            else:
                _ok(f"DashScope 图片: 连接正常（未创建任务，get_task 预期报错）{s[:120]}")
    except Exception as e:
        _fail(f"DashScope 图片: 初始化失败 {str(e)}")


async def _check_xfyun_ws(settings) -> None:
    if not (settings.xfyun_app_id and settings.xfyun_access_key_id and settings.xfyun_access_key_secret):
        _warn("讯飞 RTASR: 未配置 XFYUN_APP_ID / XFYUN_ACCESS_KEY_ID / XFYUN_ACCESS_KEY_SECRET（跳过）")
        return
    if not settings.xfyun_rtasr_base_url:
        _warn("讯飞 RTASR: 未配置 XFYUN_RTASR_BASE_URL（跳过）")
        return
    try:
        import websockets
    except Exception:
        _fail("讯飞 RTASR: 缺少 websockets 依赖，请先 pip install -r backend/requirements.txt")
        return

    url = build_rtasr_url(
        base_url=settings.xfyun_rtasr_base_url,
        app_id=settings.xfyun_app_id,
        access_key_id=settings.xfyun_access_key_id,
        access_key_secret=settings.xfyun_access_key_secret,
        lang=settings.xfyun_lang,
        audio_encode=settings.xfyun_audio_encode,
        samplerate=settings.xfyun_samplerate,
        role_type=settings.xfyun_role_type,
        feature_ids=settings.xfyun_feature_ids,
        eng_spk_match=settings.xfyun_eng_spk_match,
        uuid_str="ping",
    )
    try:
        async with websockets.connect(url, open_timeout=8, close_timeout=2) as ws:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                _ok(f"讯飞 RTASR: WS 握手成功（收到首包）{str(msg)[:80]}")
            except asyncio.TimeoutError:
                _ok("讯飞 RTASR: WS 握手成功（未收到首包，仍可能正常）")
    except Exception as e:
        _fail(f"讯飞 RTASR: WS 连接失败 {str(e)}")


def _check_voiceprint(settings) -> None:
    if not (settings.xfyun_app_id and settings.xfyun_access_key_id and settings.xfyun_access_key_secret):
        _warn("讯飞 声纹: 未配置鉴权（跳过）")
        return
    if not settings.xfyun_voiceprint_delete_url:
        _warn("讯飞 声纹: 未配置 XFYUN_VOICEPRINT_DELETE_URL（无法做无副作用连通性测试）")
        return
    try:
        resp = delete_voiceprint(
            delete_url=settings.xfyun_voiceprint_delete_url,
            app_id=settings.xfyun_app_id,
            access_key_id=settings.xfyun_access_key_id,
            access_key_secret=settings.xfyun_access_key_secret,
            feature_ids=[f"ping_{int(time.time())}"],
        )
        code = str(resp.get("code") or "")
        desc = str(resp.get("desc") or "")
        if code == "000000":
            _ok("讯飞 声纹: delete 可用（返回 000000）")
        else:
            _ok(f"讯飞 声纹: 可连通（返回 code={code} desc={desc[:80]!r}，正常情况下可能因 feature_id 不存在而非 000000）")
    except Exception as e:
        _fail(f"讯飞 声纹: 调用失败 {str(e)}")


def main() -> None:
    settings = get_settings()
    print("== StreamVis AI 连接诊断 ==")
    print(f"Kimi enable={_bool(settings.enable_kimi)} model={settings.moonshot_model} base_url={settings.moonshot_base_url}")
    print(f"Images enable={_bool(settings.enable_images)} model_t2i={settings.t2i_model} base_url={settings.dashscope_base_url} workspace={_mask(settings.dashscope_workspace or '')}")
    print(f"XFYUN enable={_bool(settings.xfyun_enable)} rtasr_base_url={settings.xfyun_rtasr_base_url} role_type={settings.xfyun_role_type}")
    print("")

    _check_kimi(settings)
    _check_kimi_files(settings)
    _check_dashscope_images(settings)
    _check_voiceprint(settings)
    asyncio.run(_check_xfyun_ws(settings))


if __name__ == "__main__":
    main()

