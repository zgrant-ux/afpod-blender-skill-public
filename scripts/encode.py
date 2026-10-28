"""Encode the rendered AF Pod pieces: ProRes 4444 with alpha + SFX (the deliverables) and H.264 previews over a stand-in shot.

  python3 encode.py [piece ...]      (default: all)
  python3 encode.py --src renders_4k_slow --out "out/4K SLOW - NO SOUND" --tag "4K SLOW" --nosound [piece ...]

renders/<piece>/f_####.png (+ sfx/<piece>.wav)  ->  out/AF POD - <Name>.mov  and  out/previews/AF POD - <Name> (preview).mp4
The end card's frames 30-149 are a seamless loop, repeated out to 20 s. Rendered at 30 fps; delivered at 29.97.
"""
import json, os, subprocess, sys, tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
NAMES = {'intro': 'YouTube Intro', 'trans_drip': 'Transition 1 - Drip', 'trans_splat': 'Transition 2 - Splat',
         'trans_sweep': 'Transition 3 - Sweep', 'endcard': 'YouTube End Card'}
RATE = '30000/1001'
args = sys.argv[1:]
def take(flag, default=None, has_value=True):
    if flag not in args: return default
    i = args.index(flag); v = args[i + 1] if has_value else True
    del args[i:i + (2 if has_value else 1)]; return v
SRC = take('--src', 'renders'); OUTDIR = take('--out', 'out'); TAG = take('--tag', ''); NOSOUND = take('--nosound', False, False)
SIZE = take('--size')            # e.g. 1920x1080: scale the frames down (a 4K render scaled to 1080 is supersampled)


def frames_for(piece):
    d = os.path.join(ROOT, SRC, piece)
    slow = json.load(open(os.path.join(d, 'info.json'))).get('slow', 1.0)
    fs = sorted(f for f in os.listdir(d) if f.startswith('f_') and f.endswith('.png'))
    paths = [os.path.join(d, f) for f in fs]
    if piece == 'endcard':
        a, b = round(30 * slow), round(150 * slow)          # in-animation, then the seamless idle loop
        intro, loop = paths[:a], paths[a:b]
        out = list(intro)
        while len(out) < 600: out += loop
        paths = out[:600]
    return paths


def seq_dir(paths):
    tmp = tempfile.mkdtemp(prefix='afpod_')
    for i, p in enumerate(paths): os.symlink(p, os.path.join(tmp, f'{i:05d}.png'))
    return tmp


def encode(piece):
    paths = frames_for(piece); tmp = seq_dir(paths)
    wav = os.path.join(ROOT, 'sfx', piece + '.wav')
    os.makedirs(os.path.join(ROOT, OUTDIR, 'previews'), exist_ok=True)
    label = NAMES[piece] + (f' ({TAG})' if TAG else '')
    mov = os.path.join(ROOT, OUTDIR, f'AF POD - {label}.mov')
    dur = len(paths) * 1001 / 30000
    audio_in = [] if NOSOUND else ['-i', wav]
    audio_map = [] if NOSOUND else ['-map', '1:a', '-c:a', 'pcm_s16le']
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', RATE, '-i', f'{tmp}/%05d.png', *audio_in,
                    '-map', '0:v', *audio_map, *(['-vf', f"scale={SIZE.replace('x', ':')}:flags=lanczos"] if SIZE else []), '-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le',
                    '-vendor', 'apl0', '-alpha_bits', '16', '-t', f'{dur:.3f}', mov], check=True)
    # preview: over a stand-in "podcast" shot (dark studio gradient with a soft vignette) so the transparency reads
    prev = os.path.join(ROOT, OUTDIR, 'previews', f'AF POD - {label} (preview).mp4')
    bg = ("gradients=s=1920x1080:c0=0x24324a:c1=0x0b0f18:x0=0:y0=0:x1=1920:y1=1080:d=60,"
          "drawbox=x=760:y=260:w=400:h=560:color=0x3a4a66@0.6:t=fill,drawtext=text='YOUR VIDEO':fontcolor=0x7f8fa8:fontsize=48:x=(w-tw)/2:y=880")
    pa_in = [] if NOSOUND else ['-i', wav]
    pa_map = [] if NOSOUND else ['-map', '2:a', '-c:a', 'aac', '-b:a', '256k']
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', bg, '-framerate', RATE, '-i', f'{tmp}/%05d.png', *pa_in,
                    '-filter_complex', '[1:v]format=rgba,scale=1920:1080:flags=lanczos[f];[0:v]format=yuv420p,fps=' + RATE + '[b];[b][f]overlay=shortest=1,format=yuv420p[v]',
                    '-map', '[v]', *pa_map, '-c:v', 'libx264', '-crf', '17', '-preset', 'medium',
                    '-t', f'{dur:.3f}', prev], check=True)
    for f in os.listdir(tmp): os.unlink(os.path.join(tmp, f))
    os.rmdir(tmp)
    print(f'{NAMES[piece]}: {len(paths)} frames, {dur:.2f}s -> {os.path.basename(mov)}')


for p in (args or NAMES):
    encode(p)
