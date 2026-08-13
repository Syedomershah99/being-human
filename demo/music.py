"""
Generates the demo's background bed.

Synthesised from scratch rather than sourced, so the repo carries no music
licence question at all. It is deliberately plain: a slow minor drone, a
quiet pulse on the two-second grid, and a breath of filtered noise. The point
is to fill the silence under a muted-autoplay video, not to be listened to.

    python3 demo/music.py --seconds 30.2 --out demo/bed.wav

Stdlib plus numpy (which manim already pulls in). No network, no samples.
"""

import argparse
import math
import struct
import wave

import numpy as np

SR = 44100


def adsr(n, attack, release, sr=SR):
    """Simple fade-in / fade-out envelope, in seconds."""
    env = np.ones(n)
    a = int(attack * sr)
    r = int(release * sr)
    if a > 0:
        env[:a] = np.linspace(0.0, 1.0, a) ** 2
    if r > 0:
        env[-r:] = np.linspace(1.0, 0.0, r) ** 2
    return env


def one_pole_lowpass(x, cutoff, sr=SR):
    """Cheap smoothing filter -- takes the edge off raw sine stacks."""
    dt = 1.0 / sr
    rc = 1.0 / (2 * math.pi * cutoff)
    alpha = dt / (rc + dt)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += alpha * (x[i] - acc)
        y[i] = acc
    return y


def drone(t, freqs, detune=0.4):
    """
    A stack of sines with slow independent tremolo.

    The per-partial LFO is what keeps it from sounding like a test tone: each
    voice drifts at its own rate, so the chord never sits perfectly still.
    """
    out = np.zeros_like(t)
    for i, f in enumerate(freqs):
        lfo = 0.72 + 0.28 * np.sin(2 * math.pi * (0.05 + 0.017 * i) * t + i)
        # A pair of slightly detuned partials beats gently against itself.
        out += lfo * (np.sin(2 * math.pi * f * t)
                      + 0.6 * np.sin(2 * math.pi * (f + detune) * t)) / (i + 1.7)
    return out


def pulse_track(t, period=2.0, freq=660.0, sr=SR):
    """A soft tick on the grid, so the video has a pulse without a drum."""
    out = np.zeros_like(t)
    n = len(t)
    for k in range(int(t[-1] / period) + 1):
        start = int(k * period * sr)
        length = int(0.28 * sr)
        if start + length > n:
            break
        seg = np.arange(length) / sr
        env = np.exp(-seg * 16.0)
        tone = np.sin(2 * math.pi * freq * seg) + 0.5 * np.sin(2 * math.pi * freq * 2 * seg)
        out[start:start + length] += env * tone * 0.22
    return out


def air(n, rng):
    """Filtered noise. Fills the gap between the partials so it breathes."""
    noise = rng.normal(0.0, 1.0, n)
    return one_pole_lowpass(noise, 900.0) * 0.05


def build(seconds, seed=7):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)

    # A minor: A2 E3 A3 C4 E4. Minor because the video opens on a problem.
    chord = drone(t, [110.0, 164.81, 220.0, 261.63, 329.63])
    chord = one_pole_lowpass(chord, 1400.0)

    mix = 0.55 * chord + pulse_track(t) + air(n, rng)
    mix *= adsr(n, attack=2.2, release=3.2)

    peak = np.max(np.abs(mix)) or 1.0
    mix = mix / peak * 0.20          # ~-14 dBFS: audible, never competing

    # Wide but mono-safe: a few ms of delay on one side reads as space.
    delay = int(0.009 * SR)
    left = mix
    right = np.concatenate([np.zeros(delay), mix[:-delay]])
    return np.stack([left, right], axis=1)


def write_wav(path, stereo):
    data = (np.clip(stereo, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(path, "w") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def main():
    ap = argparse.ArgumentParser(description="Synthesise the demo bed.")
    ap.add_argument("--seconds", type=float, default=30.2)
    ap.add_argument("--out", default="demo/bed.wav")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    write_wav(args.out, build(args.seconds, args.seed))
    print("wrote %s (%.1fs)" % (args.out, args.seconds))


if __name__ == "__main__":
    main()
