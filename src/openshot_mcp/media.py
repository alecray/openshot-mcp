"""ffprobe a media file into an OpenShot ``files[]`` entry, and build clips from files."""
from __future__ import annotations

import json
import os
import subprocess
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parents[2] / "templates"
CLIP_DEFAULTS = json.loads((TEMPLATES / "clip_defaults.json").read_text(encoding="utf-8"))

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff"}


def _frac(s: str) -> Fraction:
    num, _, den = s.partition("/")
    return Fraction(int(num), int(den or 1))


def _fd(fr: Fraction) -> dict:
    return {"num": fr.numerator, "den": fr.denominator}


def ffprobe(path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}: {r.stderr.strip()}")
    return json.loads(r.stdout)


def norm_path(path: str | Path) -> str:
    return str(Path(path).resolve()).replace("\\", "/")


def file_entry(path: str | Path, file_id: str) -> dict:
    """Build a flat OpenShot ``files[]`` entry (FFmpegReader shape) from ffprobe output."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    info = ffprobe(p)
    streams = info.get("streams", [])
    fmt = info.get("format", {})
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    is_image = p.suffix.lower() in IMAGE_EXT
    duration = float(fmt.get("duration") or (video or audio or {}).get("duration") or 0.0)

    if video is not None:
        fps = _frac(video.get("r_frame_rate", "30/1"))
        tb = _frac(video.get("time_base", f"1/{fps}"))
        width, height = int(video["width"]), int(video["height"])
        nb = video.get("nb_frames")
        video_length = int(nb) if nb and nb.isdigit() else int(round(duration * fps))
        sar = video.get("sample_aspect_ratio", "1:1")
        pr = Fraction(*(int(x) for x in sar.split(":"))) if sar and sar != "0:1" else Fraction(1)
        dar = Fraction(width * pr.numerator, height * pr.denominator)
        vcodec = video.get("codec_name", "")
    else:
        fps, tb, width, height = Fraction(30), Fraction(1, 30), 1280, 720
        video_length = int(round(duration * 30))
        pr, dar, vcodec = Fraction(1), Fraction(1), ""
    # libopenshot rounds the duration to whole frames of the chosen fps (audio-only files use 30 fps).
    duration = float(Fraction(video_length) / fps)

    if audio is not None:
        sample_rate = int(audio.get("sample_rate", 0))
        channels = int(audio.get("channels", 0))
        acodec = audio.get("codec_name", "")
        a_tb = _frac(audio.get("time_base", f"1/{sample_rate or 1}"))
        a_bitrate = int(audio.get("bit_rate") or fmt.get("bit_rate") or 0)
        layout = {1: 4, 2: 3}.get(channels, 3)  # libopenshot LAYOUT_MONO=4, LAYOUT_STEREO=3
    else:
        sample_rate, channels, acodec, a_tb, a_bitrate, layout = 0, 0, "", Fraction(1, 1), 0, 0

    if is_image:
        media_type = "image"
    elif video is not None and video.get("codec_name") not in {"png", "mjpeg", "bmp"}:
        media_type = "video"
    elif video is not None:
        media_type = "image"
    else:
        media_type = "audio"

    return {
        "acodec": acodec,
        "audio_bit_rate": a_bitrate,
        "audio_stream_index": int(audio["index"]) if audio is not None else -1,
        "audio_timebase": _fd(a_tb),
        "channel_layout": layout,
        "channels": channels,
        "display_ratio": _fd(dar),
        "duration": duration,
        "duration_strategy": "VideoPreferred",
        "file_size": int(fmt.get("size") or os.path.getsize(p)),
        "fps": _fd(fps),
        "has_audio": audio is not None,
        "has_single_image": media_type == "image",
        "has_video": video is not None,
        "height": height,
        "id": file_id,
        "interlaced_frame": False,
        "media_type": media_type,
        "metadata": {},
        "path": norm_path(p),
        "pixel_format": 0 if video is not None else -1,
        "pixel_ratio": _fd(pr),
        "sample_rate": sample_rate,
        "top_field_first": True,
        "type": "FFmpegReader" if media_type != "image" else "QtImageReader",
        "vcodec": vcodec,
        "video_bit_rate": int(video.get("bit_rate") or fmt.get("bit_rate") or 0) if video is not None else 0,
        "video_length": video_length,
        "video_stream_index": int(video["index"]) if video is not None else -1,
        "video_timebase": _fd(tb),
        "width": width,
    }


def clip_from_file(file: dict, clip_id: str, layer: int, position: float, start: float, end: float,
                   title: str | None = None) -> dict:
    """Build a ``clips[]`` entry with OpenShot's default curves and this file as its reader."""
    clip = deepcopy(CLIP_DEFAULTS)
    reader = {k: v for k, v in file.items() if k not in ("ui", "image")}
    clip.update({
        "id": clip_id,
        "file_id": file["id"],
        "title": title or Path(file["path"]).name,
        "reader": reader,
        "layer": int(layer),
        "position": float(position),
        "start": float(start),
        "end": float(end),
        "duration": float(end) - float(start),
    })
    return clip
