# Generates voices (Kokoro TTS) + synthesized SFX/music, mixes the soundtrack, and writes timing.json.
import json, os, sys
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from story import LINES, VOICES, CROWD
from kokoro_onnx import Kokoro

SR = 24000
FPS = 24
K = Kokoro("/home/user/tts/kokoro-v1.0.onnx", "/home/user/tts/voices-v1.0.bin")
rng = np.random.default_rng(3)
os.makedirs(os.path.join(HERE, "audio"), exist_ok=True)


def tts(text, voice, speed):
    s, sr = K.create(text, voice=voice, speed=speed, lang="en-us")
    assert sr == SR
    # trim leading/trailing silence
    idx = np.where(np.abs(s) > 0.01)[0]
    if len(idx):
        s = s[max(0, idx[0] - 600): idx[-1] + 1200]
    return s.astype(np.float32)


def env(n, a=0.005, r=0.1):
    t = np.arange(n) / SR
    e = np.minimum(1, t / a) * np.exp(-t / r)
    return e


# ---------- SFX ----------
def sfx_boing():
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 180 + 520 * (t / t[-1]) ** 0.6
    ph = 2 * np.pi * np.cumsum(f * (1 + 0.08 * np.sin(2 * np.pi * 28 * t))) / SR
    return 0.5 * np.sin(ph) * env(n, 0.003, 0.18)


def sfx_bigboing():
    n = int(1.4 * SR); t = np.arange(n) / SR
    f = 90 + 1400 * (t / t[-1]) ** 1.5
    ph = 2 * np.pi * np.cumsum(f * (1 + 0.12 * np.sin(2 * np.pi * 18 * t))) / SR
    return 0.6 * np.sin(ph) * env(n, 0.003, 0.9)


def sfx_whoosh():
    n = int(2.0 * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    # crude band sweep via moving-average with changing width -> just shape amplitude
    k = 40; sm = np.convolve(noise, np.ones(k) / k, mode="same")
    shape = np.sin(np.pi * t / t[-1]) ** 2
    return 0.9 * sm * shape


def sfx_thunk():
    n = int(0.35 * SR); t = np.arange(n) / SR
    return 0.7 * np.sin(2 * np.pi * (90 - 40 * t) * t) * env(n, 0.002, 0.07)


def sfx_scratch():
    n = int(0.5 * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    f = 900 * np.abs(np.sin(2 * np.pi * 3 * t)) + 200
    tone = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR))
    return 0.25 * (0.6 * tone + 0.4 * noise) * env(n, 0.002, 0.25)


def sfx_sting():
    out = np.zeros(int(2.2 * SR))
    for i, (f, st) in enumerate([(110, 0.0), (103.8, 0.35), (82.4, 0.7)]):
        n = int((1.5 if i == 2 else 0.33) * SR); t = np.arange(n) / SR
        w = sum(np.sin(2 * np.pi * f * h * t) / h for h in range(1, 8))
        seg = 0.25 * w * env(n, 0.005, 0.9 if i == 2 else 0.25)
        a = int(st * SR); out[a:a + n] += seg
    return out


def sfx_siren():
    n = int(2.4 * SR); t = np.arange(n) / SR
    f = 750 + 250 * np.sign(np.sin(2 * np.pi * 1.6 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return 0.18 * np.sin(ph) * np.minimum(1, t / 0.05) * np.minimum(1, (t[-1] - t) / 0.3)


def music(seconds):
    # cheerful chiptune-ish loop: C G Am F arpeggios + bass
    bpm = 132; beat = 60 / bpm; n = int(seconds * SR)
    out = np.zeros(n)
    chords = [[60, 64, 67, 72], [55, 59, 62, 67], [57, 60, 64, 69], [53, 57, 60, 65]]
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    step = beat / 2; i = 0; t0 = 0.0
    while t0 < seconds:
        ch = chords[int(t0 / (beat * 4)) % 4]
        note = ch[i % 4] + (12 if (i // 4) % 2 else 0)
        m = int(step * SR); t = np.arange(m) / SR
        tone = np.sign(np.sin(2 * np.pi * hz(note) * t)) * 0.06 * env(m, 0.002, 0.12)
        a = int(t0 * SR); b = min(n, a + m); out[a:b] += tone[: b - a]
        if i % 4 == 0:
            bm = int(beat * 2 * SR); tb = np.arange(bm) / SR
            bass = np.sin(2 * np.pi * hz(ch[0] - 24) * tb) * 0.18 * env(bm, 0.004, 0.35)
            b2 = min(n, a + bm); out[a:b2] += bass[: b2 - a]
        if i % 2 == 0:  # hat
            hm = int(0.04 * SR); out[a:a + hm] += rng.standard_normal(min(hm, n - a)) * 0.03 * env(min(hm, n - a), 0.001, 0.01)
        t0 += step; i += 1
    return out


SFX = dict(boing=sfx_boing, bigboing=sfx_bigboing, whoosh=sfx_whoosh, thunk=sfx_thunk,
           scratch=sfx_scratch, sting=sfx_sting, siren=sfx_siren)

# ---------- assemble ----------
t = 1.2  # lead-in
clips = []      # (start_sec, samples, speaker)
sfx_at = []     # (start_sec, name)
timing = []
for L in LINES:
    who = L["who"]
    if who == "none":
        dur = L["dur"]; samples = None
    elif who == "crowd":
        parts = []
        for j, (v, sp) in enumerate(CROWD):
            s = tts(L.get("say", L["text"]), v, sp * (0.95 + 0.04 * j))
            parts.append((rng.uniform(0, 0.12), s))
        dur = max(o + len(s) / SR for o, s in parts)
        samples = np.zeros(int(dur * SR) + 1)
        for o, s in parts:
            a = int(o * SR); samples[a:a + len(s)] += s * 0.45
    else:
        v, sp = VOICES[who]
        samples = tts(L.get("say", L["text"]), v, sp)
        dur = len(samples) / SR
    if samples is not None:
        clips.append((t, samples, who))
    for name, off in L.get("sfx", []):
        st = t + off if off >= 0 else t + dur + off
        sfx_at.append((st, name))
    timing.append(dict(id=L["id"], who=who, text=L["text"], start=t, end=t + dur))
    t += dur + L.get("gap", 0.45)

total = t + 0.5
N = int(total * SR) + SR
mix = np.zeros(N)
for st, s, who in clips:
    a = int(st * SR); mix[a:a + len(s)] += s

# music segments
music_on = None
segs = []
for st, name in sorted(sfx_at):
    if name == "music":
        music_on = st
    elif name == "musicstop" and music_on is not None:
        segs.append((music_on, st)); music_on = None
if music_on is not None:
    segs.append((music_on, total))
for a, b in segs:
    m = music(b - a)
    fade = np.minimum(1, np.minimum(np.arange(len(m)) / (0.3 * SR), (len(m) - np.arange(len(m))) / (0.05 * SR)))
    i = int(a * SR); mix[i:i + len(m)] += m * fade
for st, name in sfx_at:
    if name in SFX:
        s = SFX[name](); i = int(st * SR); mix[i:i + len(s)] += s

mix = mix[: int(total * SR)]
mix = mix / max(1e-6, np.abs(mix).max()) * 0.9
sf.write(os.path.join(HERE, "audio", "soundtrack.wav"), mix.astype(np.float32), SR)

# ---------- mouth envelopes per speaker ----------
nf = int(total * FPS) + 2
speakers = ["narrator", "mayor", "jax", "dave", "linda", "crowd"]
envs = {s: np.zeros(nf) for s in speakers}
for st, s, who in clips:
    spf = SR / FPS
    for f in range(int(len(s) / spf) + 1):
        chunk = s[int(f * spf): int((f + 1) * spf)]
        if len(chunk):
            envs[who][int(st * FPS) + f] = np.abs(chunk).mean()
for k in envs:
    m = envs[k].max()
    if m > 0:
        envs[k] = np.minimum(1, envs[k] / m * 1.8)
sfx_list = sorted([dict(t=st, name=n) for st, n in sfx_at], key=lambda d: d["t"])
json.dump(dict(dur=total, lines=timing, sfx=sfx_list, env={k: [round(x, 3) for x in v] for k, v in envs.items()}),
          open(os.path.join(HERE, "timing.json"), "w"))
print("TOTAL", round(total, 1), "s")
for L in timing:
    print(f'{L["start"]:6.1f} {L["end"]:6.1f} {L["id"]:5} {L["text"][:60]}')
