"""Sound design for the AF Pod YouTube package: one 48 kHz stereo WAV per piece, timed to the Blender animation (30 fps).

  python3 sfx.py <out dir>

Layers Mister Horse library sounds (swooshes, pops, elastic creak, glitter clink) with goo sounds synthesized here
(wet splats, droplet bloops, slurps) and a short marimba jingle for the intro and end card.
"""
import os, subprocess, sys, numpy as np

SR = 48000; FPS = 30
OUT = sys.argv[1]
MH = os.path.expanduser('~/Library/Application Support/MisterHorse/ProductManager/AssetPacks')
LIB = {
    'approach': '5f58caeda5b19ec2e048f90e2f72761429930cd34bed7ab60971c5c3767c847c/Swooshy Approach 01 #d9af353b.wav',
    'swoosh_a': '5f58caeda5b19ec2e048f90e2f72761429930cd34bed7ab60971c5c3767c847c/Swoosh 01 - 01 #7847b773.wav',
    'swoosh_b': '5f58caeda5b19ec2e048f90e2f72761429930cd34bed7ab60971c5c3767c847c/Swoosh 01 - 02 #02d3c790.wav',
    'swoosh_c': 'b5043682cdbe0eedd95e606abc09fe69aacdd45c43219bd1b42e55050e50764f/Swoosh 04 - 02 #d8b435f0.wav',
    'trans_23': '5f58caeda5b19ec2e048f90e2f72761429930cd34bed7ab60971c5c3767c847c/Swoosh Transition 23 #9da956db.wav',
    'pop_small': '5f58caeda5b19ec2e048f90e2f72761429930cd34bed7ab60971c5c3767c847c/Small Pop 01 #b2717bfd.wav',
    'pop_hollow': '5f58caeda5b19ec2e048f90e2f72761429930cd34bed7ab60971c5c3767c847c/Hollow Pop 06 #8ea6dd84.wav',
    'creak': '5f58caeda5b19ec2e048f90e2f72761429930cd34bed7ab60971c5c3767c847c/Elastic Soft Rubber Creak 01 #63bab6e3.wav',
    'clink': '5f58caeda5b19ec2e048f90e2f72761429930cd34bed7ab60971c5c3767c847c/Glittering Clink 02 #68ad0c8d.wav',
    'boom': '5f58caeda5b19ec2e048f90e2f72761429930cd34bed7ab60971c5c3767c847c/Medium Cinematic Boom 14 #4cce2321.wav',
}
rng = np.random.default_rng(7)


def load(key):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(MH, LIB[key]), '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def mono(x): return np.stack([x, x], 1)


def lowpass(x, fc):
    a = np.exp(-2 * np.pi * fc / SR); y = np.empty_like(x); s = 0.0
    for i, v in enumerate(x): s = (1 - a) * v + a * s; y[i] = s
    return y


def bandpass_sweep(x, f0, f1, q=4.0):
    """state-variable bandpass whose centre glides f0 -> f1 (exponential)."""
    n = len(x); f = f0 * (f1 / f0) ** (np.arange(n) / max(n - 1, 1))
    lo = bp = 0.0; y = np.empty(n)
    for i in range(n):
        g = 2 * np.sin(np.pi * f[i] / SR); hp = x[i] - lo - bp / q; bp += g * hp; lo += g * bp; y[i] = bp
    return y


def env(n, a, d):
    t = np.arange(n) / SR; return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)


def bloop(f0=380, f1=900, dur=0.09, vol=0.5):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f0 * (f1 / f0) ** (t / dur); ph = 2 * np.pi * np.cumsum(f) / SR
    return mono(vol * np.sin(ph) * env(n, 0.003, dur / 3))


def splat(vol=0.8, dur=0.45, low=85):
    n = int(dur * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    body = bandpass_sweep(noise, 1400, 260, 2.2) * env(n, 0.002, 0.07) * 2.2
    thump = np.sin(2 * np.pi * np.cumsum(low * (0.55 + 0.45 * np.exp(-t / 0.05))) / SR) * env(n, 0.002, 0.11) * 1.1
    s = mono(vol * (body + thump))
    for k in range(4):                                        # little droplets thrown off the splat
        b = bloop(rng.uniform(300, 600), rng.uniform(700, 1400), rng.uniform(0.05, 0.08), 0.18)
        at = int(rng.uniform(0.05, 0.3) * SR)
        if at + len(b) < n: s[at:at + len(b)] += b * np.array([rng.uniform(0.4, 1), rng.uniform(0.4, 1)])
    return s


def slurp(dur=0.5, vol=0.6, up=True):
    """gooey suck: wobbling bandpass noise gliding in pitch (up = drain/suck, down = pour)."""
    n = int(dur * SR); t = np.arange(n) / SR
    wob = 1 + 0.35 * np.sin(2 * np.pi * 14 * t)
    noise = rng.standard_normal(n) * wob
    y = bandpass_sweep(noise, 300 if up else 1500, 1500 if up else 300, 6.0)
    shape = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.7
    return mono(vol * 2.4 * y * shape)


def marimba(freq, dur=0.6, vol=0.35):
    n = int(dur * SR); t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * freq * 3.99 * t) * np.exp(-t / 0.03) + 0.12 * np.sin(2 * np.pi * freq * 10 * t) * np.exp(-t / 0.008)
    return mono(vol * tone * env(n, 0.002, 0.16))


def boing(f0=210, dur=0.45, vol=0.3):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f0 * (1 + 0.55 * np.exp(-t / 0.06) * np.cos(2 * np.pi * 9 * t)); ph = 2 * np.pi * np.cumsum(f) / SR
    return mono(vol * np.sin(ph) * env(n, 0.003, 0.14))


NOTE = lambda m: 440 * 2 ** ((m - 69) / 12)
def jingle(vol=0.55):
    """quick playful hook: C-E-G-C up, then a C major 9 hit with a goofy boing."""
    out = np.zeros((int(1.4 * SR), 2))
    for i, m in enumerate((72, 76, 79, 84)):
        at = int(i * 0.075 * SR); x = marimba(NOTE(m), 0.5, 0.30); out[at:at + len(x)] += x * [1 - 0.15 * i, 0.55 + 0.15 * i]
    at = int(0.33 * SR)
    for m in (60, 67, 72, 74, 76, 79):
        x = marimba(NOTE(m), 1.0, 0.16); out[at:at + len(x)] += x
    b = boing(NOTE(55), 0.5, 0.22); out[at:at + len(b)] += b
    return out * vol


def place(track, clip, frame, gain=1.0, pan=0.0):
    at = int(frame / FPS * SR)
    if at >= len(track): return
    clip = clip[:len(track) - at] * gain
    if pan: clip = clip * np.array([min(1, 1 - pan), min(1, 1 + pan)])
    track[at:at + len(clip)] += clip


def master(track, name, peak=-3.0):
    track = np.tanh(track * 1.1) / np.tanh(1.1)               # soft clip to glue layers
    track *= 10 ** (peak / 20) / max(1e-6, np.abs(track).max())
    fade = int(0.02 * SR); track[-fade:] *= np.linspace(1, 0, fade)[:, None]
    raw = (np.clip(track, -1, 1) * 32767).astype('<i2').tobytes()
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 's16le', '-ac', '2', '-ar', str(SR), '-i', '-', os.path.join(OUT, name + '.wav')], input=raw, check=True)
    print(name, f'{len(track) / SR:.2f}s')


os.makedirs(OUT, exist_ok=True)
S = {k: load(k) for k in LIB}

# intro: 112 frames
T = np.zeros((int(112 / FPS * SR) + SR // 2, 2))
place(T, S['approach'], 0, 0.7); place(T, slurp(0.55, 0.35, up=False), 1)
for f in (7, 11, 15): place(T, bloop(rng.uniform(320, 480), rng.uniform(800, 1200)), f, 0.5, rng.uniform(-0.6, 0.6))
place(T, slurp(0.45, 0.3, up=True), 9)
place(T, splat(0.9), 15); place(T, S['pop_hollow'], 15, 0.8); place(T, S['creak'], 16, 0.55); place(T, jingle(), 16)
place(T, S['pop_small'], 27, 0.6, -0.4); place(T, S['pop_small'], 31, 0.6, 0.4); place(T, bloop(250, 700, 0.14, 0.4), 35)
place(T, S['clink'], 48, 0.45)
place(T, S['swoosh_c'], 80, 0.7); place(T, slurp(0.6, 0.45, up=False), 84); place(T, S['boom'], 82, 0.25)
master(T[:int(112 / FPS * SR)], 'intro')

# drip transition: 40 frames, cut on 18
T = np.zeros((int(40 / FPS * SR), 2))
place(T, S['swoosh_a'], 0, 0.8); place(T, slurp(0.4, 0.35, up=False), 2); place(T, splat(0.6, 0.35, 70), 14)
for f in (6, 10): place(T, bloop(rng.uniform(320, 480), rng.uniform(800, 1200)), f, 0.4, rng.uniform(-0.6, 0.6))
place(T, S['swoosh_b'], 19, 0.7); place(T, slurp(0.5, 0.3, up=False), 21)
for f in (30, 34): place(T, bloop(rng.uniform(320, 480), rng.uniform(800, 1200), 0.08, 0.3), f, 0.5, rng.uniform(-0.6, 0.6))
master(T, 'trans_drip')

# splat transition: 40 frames, cut on 18
T = np.zeros((int(40 / FPS * SR), 2))
place(T, splat(1.0, 0.5, 70), 0); place(T, S['boom'], 0, 0.35); place(T, S['creak'], 2, 0.4)
place(T, S['pop_hollow'], 9, 0.9); place(T, boing(220, 0.4, 0.25), 9)
place(T, S['pop_small'], 21, 0.6); place(T, slurp(0.45, 0.55, up=True), 23); place(T, bloop(500, 1500, 0.1, 0.4), 35)
master(T, 'trans_splat')

# sweep transition: 46 frames, cut on 21 (pans left -> right)
T = np.zeros((int(46 / FPS * SR), 2))
place(T, S['trans_23'], 0, 0.6); place(T, S['swoosh_a'], 1, 0.6, -0.5); place(T, slurp(0.5, 0.3, up=False), 3)
place(T, S['pop_small'], 2, 0.6, -0.6)
for f in (8, 15): place(T, boing(330, 0.25, 0.15), f, 1.0, -0.2 + f * 0.04)
place(T, S['swoosh_b'], 22, 0.7, 0.3); place(T, S['pop_small'], 24, 0.6, -0.5); place(T, slurp(0.5, 0.3, up=True), 27)
master(T, 'trans_sweep')

# end card: 20 s, the flood-in sounds play over the first second
T = np.zeros((20 * SR, 2))
place(T, S['approach'], 0, 0.6); place(T, slurp(0.55, 0.3, up=False), 1); place(T, slurp(0.45, 0.25, up=True), 10)
place(T, splat(0.8), 13); place(T, S['pop_hollow'], 13, 0.7); place(T, jingle(0.8), 14)
for f, p in ((18, 0.5), (20, 0.6), (21, -0.3), (23, 0.6), (25, -0.5)): place(T, S['pop_small'], f, 0.45, p)
master(T, 'endcard')
