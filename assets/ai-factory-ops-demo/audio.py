import pathlib
import wave

import numpy as np

SR, DUR = 48000, 31.0
n = int(SR * DUR)
t = np.arange(n) / SR
mix = np.zeros(n)
rng = np.random.default_rng(3)


def at(sec):
    return int(sec * SR)


def add(sig, sec, gain=1.0):
    i = at(sec)
    k = min(len(sig), n - i)
    mix[i:i + k] += sig[:k] * gain


def env(dur, a, d, curve=3.0):
    m = int(dur * SR)
    x = np.arange(m) / SR
    return np.minimum(x / a, 1.0) * np.exp(-np.maximum(x - a, 0) / d) ** 1.0 * (1 - 0) ** curve


def noise(dur):
    return rng.normal(0, 1, int(dur * SR))


def lp(x, cut):
    a = np.exp(-2 * np.pi * cut / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = a * acc + (1 - a) * x[i]
        y[i] = acc
    return y


# --- bed: sub drone with slow swell ---
drone = (0.55 * np.sin(2 * np.pi * 55 * t) + 0.3 * np.sin(2 * np.pi * 82.4 * t)
         + 0.18 * np.sin(2 * np.pi * 110 * t + 0.4 * np.sin(2 * np.pi * 0.07 * t)))
swell = 0.35 + 0.25 * np.sin(2 * np.pi * 0.045 * t) + 0.4 * np.clip((t - 14) / 7, 0, 1)
mix += drone * swell * 0.16 * np.clip(t / 2.5, 0, 1) * np.clip((DUR - t) / 3, 0, 1)

# air / hiss bed
air = lp(noise(DUR), 900)[:n]
mix += air * 0.05 * (0.4 + 0.6 * np.clip((t - 15) / 8, 0, 1))

# --- zone sweeps across the datacenter row ---
for i in range(5):
    sec = 15.4 + 1.2 + i * 0.95
    d = 0.6
    x = np.arange(int(d * SR)) / SR
    sw = lp(noise(d), 1400)[:len(x)] * np.exp(-x / 0.28) * (1 - np.exp(-x / 0.02))
    add(sw, sec, 0.075)
    add(np.sin(2 * np.pi * (300 - 110 * x / d) * x) * np.exp(-x / 0.2), sec, 0.03)

# --- impacts on scene starts ---
for sec, g in [(1.6, 1.0), (5.2, 1.15), (11.4, .8), (15.4, 1.1), (22.1, 1.1), (25.3, 1.45)]:
    d = 2.6
    e = env(d, 0.004, 0.55)
    x = np.arange(len(e)) / SR
    body = np.sin(2 * np.pi * (78 * np.exp(-x * 2.2) + 34) * x)
    tail = lp(noise(d), 260) * np.exp(-x / 0.9)
    add((body * 0.9 + tail * 0.7) * e, sec, 0.30 * g)

# --- alert pulses ---
for i in range(5):
    sec = 5.8 + i * 1.0
    d = 0.5
    e = env(d, 0.006, 0.10)
    x = np.arange(len(e)) / SR
    add(np.sin(2 * np.pi * 1180 * x) * e * (1 + 0.15 * i), sec, 0.035)
    add(np.sin(2 * np.pi * 880 * x) * e, sec + 0.16, 0.028)

# --- keyboard typing, 14.0 -> 16.2 ---
def key(space=False):
    d = 0.16
    x = np.arange(int(d * SR)) / SR
    n = noise(d)
    click = lp(lp(n - lp(n, 600), 3000), 3000) * np.exp(-x / (0.0038 if not space else 0.0055))
    f = (78 if space else rng.uniform(128, 205))
    thock = np.sin(2 * np.pi * f * x) * np.exp(-x / 0.016) * (1 - np.exp(-x / 0.0006))
    plate = np.sin(2 * np.pi * f * 2.7 * x) * np.exp(-x / 0.008) * 0.35
    return click * 7.0 + thock * (1.9 if space else 1.25) + plate


sec = 11.9
while sec < 13.4:
    g = rng.uniform(0.75, 1.0)
    space = rng.random() < 0.16
    add(key(space), sec, 0.026 * g * (1.35 if space else 1.0))
    add(key(space) * 0.35, sec + rng.uniform(0.035, 0.055), 0.013 * g)   # key release
    sec += rng.uniform(0.045, 0.085) + (0.09 if rng.random() < 0.12 else 0)

# --- agent deploy blips (scene 4) ---
for i in range(6):
    sec = 16.6 + i * 0.8
    d = 0.9
    e = env(d, 0.004, 0.16)
    x = np.arange(len(e)) / SR
    f = 440 * (2 ** (i / 12))
    add((np.sin(2 * np.pi * f * x) + 0.5 * np.sin(2 * np.pi * f * 2 * x)) * e, sec, 0.055)
    # evidence return
    add(lp(noise(0.5), 2600) * env(0.5, 0.05, 0.12), sec + 1.6, 0.05)

# --- risers into 30.0 and 40.0 ---
for sec, d in [(20.7, 1.4), (24.3, 1.0)]:
    m = int(d * SR)
    x = np.arange(m) / SR
    r = lp(noise(d), 1200)[:m] * (x / d) ** 3
    r += np.sin(2 * np.pi * (180 + 420 * (x / d) ** 2) * x) * (x / d) ** 4 * 0.5
    add(r, sec, 0.11)

# --- resolve chord at 30.2 and lockup at 40.4 ---
for sec, freqs, g in [(22.3, [110, 146.8, 220, 293.7], .8), (25.4, [82.4, 123.5, 164.8, 246.9, 329.6], 1.2)]:
    d = 6.0
    e = env(d, 0.35, 2.2)
    x = np.arange(len(e)) / SR
    ch = sum(np.sin(2 * np.pi * f * x + j) / (1 + j * .6) for j, f in enumerate(freqs))
    add(ch * e, sec, 0.055 * g)

# --- soft ticking clock through investigation ---
for i in range(20):
    sec = 16.0 + i * 0.5
    if sec > 21.4:
        break
    d = 0.08
    add(lp(noise(d), 3200) * env(d, 0.001, 0.02), sec, 0.035)

# master
mix = np.tanh(mix * 1.5) / 1.5
mix *= 0.85 / np.max(np.abs(mix))
mix *= np.clip(t / 1.0, 0, 1) * np.clip((DUR - t) / 2.0, 0, 1)

st = np.stack([mix, np.roll(mix, 220)], 1)  # gentle width
pcm = (np.clip(st, -1, 1) * 32767).astype('<i2')
OUT = pathlib.Path(__file__).parent / 'audio.wav'
with wave.open(str(OUT), 'w') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print(f'wrote {OUT} ({DUR}s)')
