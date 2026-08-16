"""Generates the per-shot AI images (Gemini image model, aka "Nano Banana") and,
when budget allows, one short AI-video hook clip (Runway image-to-video)
animated from the first image.

Note: Google's older Imagen models (predict-endpoint based) are being shut down
Aug 17 2026, so image gen goes through the Gemini generateContent endpoint
instead - a genuinely different request/response shape, not just a model rename.

Provider REST APIs evolve fastest of anything in this pipeline - if calls start
failing with schema errors, check the provider's current API docs first; the
shapes below are correct as of Aug 2026 but are the most likely thing to drift.
"""
from __future__ import annotations

import base64
import sys
import time
from pathlib import Path

import requests

from . import config as cfg
from . import stock
from .http_util import raise_for_retryable_status, retry_call

GEMINI_IMAGE_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
RUNWAY_BASE = "https://api.dev.runwayml.com/v1"


def generate_image(config: dict, prompt: str) -> bytes:
    providers = config["providers"]["image"]
    api_key = cfg.env("GOOGLE_IMAGE_API_KEY")
    url = GEMINI_IMAGE_ENDPOINT.format(model=providers["model"])

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {"aspectRatio": "9:16"},
        },
    }
    def _call() -> dict:
        resp = requests.post(url, headers={"x-goog-api-key": api_key}, json=payload, timeout=90)
        raise_for_retryable_status(resp, "Gemini image request")
        return resp.json()

    body = retry_call(_call, description="Gemini image generation")

    candidates = body.get("candidates") or []
    if not candidates:
        raise RuntimeError(
            f"Gemini returned no candidates for prompt {prompt[:120]!r}. "
            f"Response: {str(body)[:400]}"
        )

    parts = candidates[0].get("content", {}).get("parts", [])
    image_part = next((p for p in parts if "inlineData" in p), None)
    if image_part is None:
        # Usually a safety refusal: the model answers with a text part explaining
        # why, instead of an image. Surface that text - it names the actual problem.
        text = " ".join(p.get("text", "") for p in parts).strip()
        finish = candidates[0].get("finishReason", "unknown")
        raise RuntimeError(
            f"Gemini returned no image for prompt {prompt[:120]!r} "
            f"(finishReason={finish}). Model said: {text[:300] or '<no text>'}"
        )
    return base64.b64decode(image_part["inlineData"]["data"])


def generate_images_for_shots(config: dict, shot_list: list[dict], out_dir: Path) -> list[Path]:
    """Generates one image per shot, tolerating individual shot failures.

    A permanent failure on one shot (typically a safety refusal on an unlucky
    prompt) should not throw away the whole run along with everything already
    paid for, so a failed shot reuses the previous shot's image. The first shot
    has nothing to fall back to, so that one is still fatal.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for shot in shot_list:
        path = out_dir / f"shot_{shot['index']:02d}.png"
        try:
            path.write_bytes(generate_image(config, shot["visual_prompt"]))
        except Exception as e:
            if not paths:
                raise
            print(
                f"[visuals] Shot {shot['index']} failed ({e}); reusing previous image.",
                file=sys.stderr,
            )
            path = paths[-1]
        paths.append(path)
    return paths


def resolve_shot_media(
    config: dict, shot_list: list[dict], out_dir: Path
) -> tuple[list[Path], list[str], int]:
    """Resolves each shot to a media file, returning (paths, kinds, billable_images).

    `kinds[i]` is "video" or "image", which tells the assembler whether to play
    the clip or apply Ken Burns motion to a still. Shots the LLM marked as
    "stock" try Pexels first (free, real motion) and fall back to an AI image
    when no suitable footage exists or no Pexels key is configured.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    max_images = config["providers"]["image"].get("max_per_video", 8)

    paths: list[Path] = []
    kinds: list[str] = []
    generated: list[Path] = []   # distinct AI images actually paid for
    stock_hits = 0

    for shot in shot_list:
        idx = shot["index"]
        clip_path = None

        if shot.get("media_type") == "stock" and shot.get("stock_query"):
            clip_path = stock.fetch_clip(shot["stock_query"], out_dir / f"shot_{idx:02d}.mp4")

        if clip_path is not None:
            paths.append(clip_path)
            kinds.append("video")
            stock_hits += 1
            continue

        # Past the cap, recycle an already-generated image rather than paying for
        # another. Alternating zoom direction per shot keeps the reuse from
        # reading as a repeat.
        if len(generated) >= max_images and generated:
            paths.append(generated[len(paths) % len(generated)])
            kinds.append("image")
            continue

        image_path = out_dir / f"shot_{idx:02d}.png"
        try:
            image_path.write_bytes(generate_image(config, shot["visual_prompt"]))
        except Exception as e:
            if not paths:
                raise
            print(f"[visuals] Shot {idx} failed ({e}); reusing previous media.", file=sys.stderr)
            paths.append(paths[-1])
            kinds.append(kinds[-1])
            continue
        generated.append(image_path)
        paths.append(image_path)
        kinds.append("image")

    print(
        f"[visuals] {len(paths)} shots: {stock_hits} stock clip(s), "
        f"{len(generated)} AI image(s) generated, "
        f"{len(paths) - stock_hits - len(generated)} reused"
    )
    # Only distinct generated images are billable.
    return paths, kinds, len(generated)


def count_ai_images(kinds: list[str]) -> int:
    """Only AI images cost money; stock clips are free."""
    return sum(1 for k in kinds if k == "image")


def generate_hero_clip(config: dict, first_image_path: Path, prompt: str, out_path: Path) -> Path:
    """Animates the first shot image into a short video clip via Runway.
    Runway's API is async: create a task, poll until SUCCEEDED, download the result."""
    api_key = cfg.env("RUNWAY_API_KEY")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Runway-Version": "2024-11-06",
    }
    providers = config["providers"]["hero_video_clip"]

    image_b64 = base64.b64encode(first_image_path.read_bytes()).decode("utf-8")
    payload = {
        "model": providers["model"],
        "promptImage": f"data:image/png;base64,{image_b64}",
        "promptText": prompt,
        "duration": providers["clip_seconds"],
        "ratio": "720:1280",  # must be one of Runway's fixed set of ratios; this is the 9:16 option
    }
    create = requests.post(f"{RUNWAY_BASE}/image_to_video", headers=headers, json=payload, timeout=60)
    if not create.ok:
        raise RuntimeError(f"Runway task creation failed ({create.status_code}): {create.text}")
    task_id = create.json()["id"]

    for _ in range(60):  # poll up to ~5 minutes
        time.sleep(5)
        status = requests.get(f"{RUNWAY_BASE}/tasks/{task_id}", headers=headers, timeout=30)
        if not status.ok:
            raise RuntimeError(f"Runway task poll failed ({status.status_code}): {status.text}")
        body = status.json()
        if body["status"] == "SUCCEEDED":
            video_url = body["output"][0]
            video_bytes = requests.get(video_url, timeout=60).content
            out_path.write_bytes(video_bytes)
            return out_path
        if body["status"] == "FAILED":
            raise RuntimeError(f"Runway task failed: {body}")

    raise TimeoutError("Runway hero clip generation timed out")


def estimated_image_cost_usd(config: dict, num_images: int) -> float:
    return num_images * config["providers"]["image"]["est_cost_per_image_usd"]


def estimated_hero_clip_cost_usd(config: dict) -> float:
    hero = config["providers"]["hero_video_clip"]
    return hero["clip_seconds"] * hero["est_cost_per_second_usd"]
