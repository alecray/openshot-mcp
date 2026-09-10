import json
from pathlib import Path

import pytest

from openshot_mcp.grid import BeatGrid
from openshot_mcp.project import Project

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
    a.pop("history")
    b.pop("history")
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
    from openshot_mcp import lock
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


def test_unknown_keys_and_relative_paths_survive_roundtrip(tmp_path):
    """Sentinel keys are preserved; same-drive paths are written relative and read back absolute."""
    src = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    src["settings"] = {"sentinel_unknown": 1}
    proj = tmp_path / "p.osp"
    proj.write_text(json.dumps(src), encoding="utf-8")
    p = Project.load(proj)
    f = p.import_media(MP4)
    assert Path(f["path"]).is_absolute()
    p.grid = BeatGrid(bpm=88, offset_s=0.0, fps=p.fps)
    p.add_clip(f["id"], layer=3000000, position_s=0.0, end_s=0.5, snap="none")
    p.save(check_lock=False, backup=False)
    on_disk = json.loads(proj.read_text(encoding="utf-8"))
    assert on_disk["settings"] == {"sentinel_unknown": 1}
    stored = on_disk["files"][0]["path"]
    same_drive = proj.drive.lower() == MP4.drive.lower()
    assert (not Path(stored).is_absolute()) == same_drive, stored
    assert on_disk["clips"][0]["reader"]["path"] == stored
    assert on_disk["history"] == {"undo": [], "redo": []}
    again = Project.load(proj)
    assert again.file(f["id"])["path"] == f["path"]
    assert again.validate() == []


def test_save_refuses_if_changed_on_disk(tmp_path):
    proj = tmp_path / "p.osp"
    proj.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
    p = Project.load(proj)
    proj.write_text(TEMPLATE.read_text(encoding="utf-8") + "\n", encoding="utf-8")  # someone else saved
    with pytest.raises(RuntimeError):
        p.save(check_lock=False, backup=False)


def test_duration_is_frame_rounded():
    import subprocess
    p = Project.load(TEMPLATE)
    f = p.import_media(MP4)
    probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(MP4)],
                                      capture_output=True, text=True).stdout)["streams"][0]
    num, den = (int(x) for x in probe["time_base"].split("/"))
    assert f["video_timebase"] == {"num": num, "den": den}
    assert f["duration"] == pytest.approx(f["video_length"] / 60)
