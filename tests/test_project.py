import json
from pathlib import Path

import pytest

from openshot_mcp.project import Project
from openshot_mcp.grid import BeatGrid

FIX = Path(__file__).parent / "fixtures"
TEMPLATE = Path(__file__).parents[1] / "templates" / "empty_720p30.osp"
MP4 = FIX / "one_sec_60fps.mp4"
WAV = FIX / "click_88bpm.wav"


def test_load_save_roundtrip(tmp_path):
    p = Project.load(TEMPLATE)
    out = tmp_path / "rt.osp"
    p.save(out, backup=False, check_lock=False)
    a = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    b = json.loads(out.read_text(encoding="utf-8"))
    a.pop("history"); b.pop("history")
    assert a == b


def test_import_video_file_entry():
    p = Project.load(TEMPLATE)
    f = p.import_media(MP4)
    assert f["media_type"] == "video"
    assert f["fps"] == {"num": 60, "den": 1}
    assert f["video_timebase"] == {"num": 1, "den": 15360}
    assert f["video_length"] == 60
    assert f["has_video"] is True and f["has_audio"] is False
    assert f["path"] == str(MP4).replace("\\", "/")
    assert len(f["id"]) == 10 and f["id"].isupper() or f["id"].isalnum()
    # idempotent
    assert p.import_media(MP4)["id"] == f["id"]
    assert len(p.data["files"]) == 1


def test_add_clip_snaps_to_beat():
    p = Project.load(TEMPLATE)
    f = p.import_media(MP4)
    p.grid = BeatGrid(bpm=88, offset_s=0.0, fps=p.fps)
    c = p.add_clip(f["id"], layer=3000000, position_s=4.0, snap="beat")
    assert c["position"] == pytest.approx(123 / 30)  # beat 6 = 4.0909 s -> frame 123
    # end defaults to the next beat line, clamped to the 1 s file
    assert c["end"] - c["start"] == pytest.approx(min(1.0, (143 - 123) / 30))  # beat 7 = 4.7727 s -> frame 143
    assert c["layer"] == 3000000 and c["file_id"] == f["id"]
    assert c["reader"]["path"] == f["path"]
    assert "ui" not in c and "image" not in c


def test_place_sequence_contiguous():
    p = Project.load(TEMPLATE)
    f = p.import_media(MP4)
    p.grid = BeatGrid(bpm=88, offset_s=0.0, fps=p.fps)
    clips = p.place_sequence(layer=3000000, items=[{"file_id": f["id"], "beats": 1}] * 5, from_s=0.0)
    assert len(clips) == 5
    for a, b in zip(clips, clips[1:]):
        assert a["position"] + a["duration"] == pytest.approx(b["position"], abs=1e-9)
        assert (a["position"] * 30) == pytest.approx(round(a["position"] * 30), abs=1e-9)


def test_validate_catches_overlap_and_dangling():
    p = Project.load(TEMPLATE)
    f = p.import_media(MP4)
    p.grid = BeatGrid(bpm=88, offset_s=0.0, fps=p.fps)
    p.add_clip(f["id"], layer=3000000, position_s=0.0, end_s=1.0, snap="none")
    with pytest.raises(ValueError):
        p.add_clip(f["id"], layer=3000000, position_s=0.5, end_s=1.0, snap="none")
    c = p.add_clip(f["id"], layer=3000000, position_s=0.5, end_s=1.0, snap="none", allow_overlap=True)
    c["file_id"] = "NOPE000000"
    problems = p.validate()
    assert any("overlap" in x for x in problems)
    assert any("dangling" in x for x in problems)


def test_save_refuses_when_open(tmp_path, monkeypatch):
    import openshot_mcp.lock as lock
    p = Project.load(TEMPLATE)
    out = tmp_path / "x.osp"
    monkeypatch.setattr(lock, "is_open_in_openshot", lambda path: True)
    with pytest.raises(RuntimeError):
        p.save(out, backup=False)
    p.save(out, backup=False, force=True)
    assert out.exists()


def test_analyze_music_known_click():
    from openshot_mcp.grid import analyze_wav
    g = analyze_wav(WAV, fps={"num": 30, "den": 1})
    assert abs(g.bpm - 88) <= 1.0
    assert g.offset_s == pytest.approx(0.0, abs=0.02)
