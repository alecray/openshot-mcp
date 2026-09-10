"""Beat grid: bpm + offset → beat/bar times, frame-exact snapping, and wav analysis."""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path


def _fps_frac(fps: dict | Fraction | float) -> Fraction:
    if isinstance(fps, dict):
        return Fraction(int(fps["num"]), int(fps["den"]))
    return Fraction(fps).limit_denominator(1001)


@dataclass
class Section:
    start_s: float
    label: str = ""


@dataclass
class BeatGrid:
    bpm: float
    offset_s: float = 0.0
    fps: object = field(default_factory=lambda: {"num": 30, "den": 1})
    beats_per_bar: int = 4
    sections: list[Section] = field(default_factory=list)
    confidence: str = "explicit"
    detected: dict = field(default_factory=dict)

    # ---- exact arithmetic -------------------------------------------------
    @property
    def fps_frac(self) -> Fraction:
        return _fps_frac(self.fps)

    @property
    def beat_len(self) -> Fraction:
        return Fraction(60) / Fraction(str(self.bpm))

    @property
    def bar_len(self) -> Fraction:
        return self.beat_len * self.beats_per_bar

    def beat_time(self, n: int) -> Fraction:
        return self.beat_time_frac(Fraction(n))

    def beat_time_frac(self, n: Fraction) -> Fraction:
        """Exact time of (possibly fractional) beat index n."""
        return Fraction(str(self.offset_s)) + n * self.beat_len

    def bar_time(self, n: int) -> Fraction:
        return self.beat_time(n * self.beats_per_bar)

    def to_frame(self, t: Fraction | float) -> int:
        ft = t if isinstance(t, Fraction) else Fraction(str(t))
        return int(round(ft * self.fps_frac))

    def frame_to_s(self, frame: int) -> float:
        return float(Fraction(frame) / self.fps_frac)

    def nearest_beat(self, t: float) -> int:
        return int(round((Fraction(str(t)) - self.beat_time(0)) / self.beat_len))

    def snap(self, t: float, unit: str = "beat") -> tuple[int, float]:
        """Return (frame, seconds) of ``t`` quantized to the nearest beat/bar line, frame-exact."""
        if unit == "none":
            f = self.to_frame(t)
            return f, self.frame_to_s(f)
        n = self.nearest_beat(t)
        if unit == "bar":
            n = int(round(n / self.beats_per_bar)) * self.beats_per_bar
        f = self.to_frame(self.beat_time(max(n, 0)))
        return f, self.frame_to_s(f)

    def next_line_after(self, t: float, unit: str = "beat") -> float:
        n = self.nearest_beat(t)
        while float(self.beat_time(n)) <= t + 1e-9:
            n += 1
        if unit == "bar":
            while n % self.beats_per_bar:
                n += 1
        return self.frame_to_s(self.to_frame(self.beat_time(n)))

    def as_dict(self, total_s: float | None = None) -> dict:
        n_beats = int((total_s - self.offset_s) / float(self.beat_len)) + 1 if total_s else None
        return {
            "bpm": self.bpm,
            "offset_s": self.offset_s,
            "beats_per_bar": self.beats_per_bar,
            "beat_len_s": float(self.beat_len),
            "bar_len_s": float(self.bar_len),
            "fps": self.fps,
            "confidence": self.confidence,
            "sections": [{"start_s": s.start_s, "label": s.label} for s in self.sections],
            "n_beats": n_beats,
            "beat_times_s": [float(self.beat_time(i)) for i in range(n_beats)] if n_beats else None,
            "detected": self.detected,
        }


SECTION_LABELS = "ABCDEFGHIJ"


def analyze_wav(path: str | Path, fps: dict, bpm: float | None = None, offset_s: float | None = None,
                sections: list[float] | None = None, n_sections: int = 6) -> BeatGrid:
    """Detect tempo, beat offset, and section changes with librosa; explicit args override."""
    import librosa
    import numpy as np

    y, sr = librosa.load(str(path), sr=22050, mono=True)
    total = len(y) / sr
    detected: dict = {}

    tempo_est, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
    tempo_est = float(np.atleast_1d(tempo_est)[0])
    tempos = librosa.feature.tempo(y=y, sr=sr, aggregate=None)
    spread = float(np.std(tempos)) if len(tempos) else 0.0
    detected.update(tempo=tempo_est, tempo_spread=spread, first_beat_s=float(beats[0]) if len(beats) else None,
                    n_tracked_beats=len(beats))

    # Refine tempo and phase by maximizing onset strength sampled on the candidate grid.
    hop = 128
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    t_on = librosa.frames_to_time(np.arange(len(onset)), sr=sr, hop_length=hop)

    def grid_score(b: float, phi: float) -> float:
        beat = 60.0 / b
        pts = phi + np.arange(0, int((t_on[-1] - phi) / beat) + 1) * beat
        return float(np.interp(pts, t_on, onset).mean())

    if bpm is None:
        cands = np.arange(max(30.0, tempo_est - 3), tempo_est + 3.001, 0.1)
        best = max(((grid_score(b, phi), b) for b in cands for phi in np.arange(0, 60.0 / b, 0.01)),
                   key=lambda x: x[0])
        use_bpm = round(best[1], 1)
        if abs(use_bpm - round(use_bpm)) < 0.15:
            use_bpm = float(round(use_bpm))
    else:
        use_bpm = float(bpm)
    beat_len = 60.0 / use_bpm
    if offset_s is None:
        phis = np.arange(0, beat_len, 0.002)
        use_off = float(max(phis, key=lambda phi: grid_score(use_bpm, phi)))
        if use_off > beat_len * 0.9:  # essentially on the grid start, wrapped
            use_off = 0.0
        detected["offset_s"] = use_off
    else:
        use_off = float(offset_s)
    detected["refined_bpm"] = use_bpm

    if spread < 2:
        conf = "high"
    elif spread < 6:
        conf = "medium"
    else:
        conf = "low"
    if bpm is not None and offset_s is not None:
        conf = "explicit"

    grid = BeatGrid(bpm=float(use_bpm), offset_s=float(use_off), fps=fps, confidence=conf, detected=detected)

    if sections is None:
        bar = float(grid.bar_len)
        hop = 512
        rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0]
        onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
        t = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)
        edges = [float(grid.bar_time(i)) for i in range(int((total - use_off) / bar) + 1)]
        feats = []
        for a in edges:
            m = (t >= a) & (t < a + bar)
            feats.append((float(np.log(rms[m].mean() + 1e-6)) if m.any() else 0.0,
                          float(onset[m].mean()) if m.any() else 0.0))
        feats = np.array(feats)
        if len(feats) > 1:
            d = np.abs(np.diff(feats, axis=0))
            d = d / (d.std(axis=0) + 1e-9)
            score = d.sum(axis=1)
            k = min(n_sections - 1, len(score))
            picks = sorted(np.argsort(score)[-k:] + 1) if k > 0 else []
            starts = [0.0] + [edges[i] for i in picks]
        else:
            starts = [0.0]
        detected["section_starts_s"] = starts
    else:
        starts = sorted(set([0.0] + [float(s) for s in sections]))

    grid.sections = [Section(start_s=s, label=SECTION_LABELS[i] if i < len(SECTION_LABELS) else str(i))
                     for i, s in enumerate(starts)]
    grid.detected["duration_s"] = total
    return grid
