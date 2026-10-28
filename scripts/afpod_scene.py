"""Blender: AF Pod YouTube package (intro, 3 transitions, end card) built from the 2026 rebrand art, rendered transparent.

  Blender -b -P afpod_scene.py -- <piece> <out dir> [--still F] [--frames a-b] [--pct 50] [--samples 64] [--slow 1.2]
  --slow stretches the timing (1.2 = 20% slower, rendered at full frame rate); --pct 200 renders 4K
  piece: intro | trans_drip | trans_splat | trans_sweep | endcard

Art comes from ../src/art_shapes.json (traced from the rebrand PDF) and ../src/text_shapes.json (Sanurumi Handwritten).
Everything moves from one frame handler, so motion blur sub-frames see the same functions.
Units: 1 unit = 100 px at 1920x1080; x right, y up, camera on +z.
"""
import bpy, json, math, os, random, sys

argv = sys.argv[sys.argv.index('--') + 1:]
PIECE, OUT = argv[0], argv[1]
opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
HERE = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.join(HERE, '..', 'src')
ART = json.load(open(os.path.join(SRC, 'art_shapes.json'))); TXT = json.load(open(os.path.join(SRC, 'text_shapes.json')))
FPS = 30

# brand colors (sRGB -> linear)
def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)
BLUE, MID, LIGHT, WHITE = lin('0061EF'), lin('62B1FF'), lin('B3DBFF'), (1.0, 1.0, 1.0)

# ---------------------------------------------------------------- scene
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE_NEXT'
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.render.resolution_percentage = int(opt('--pct', 100))
sc.render.fps = FPS
sc.render.film_transparent = True
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'; sc.render.image_settings.color_depth = '16'
sc.render.use_lock_interface = True
sc.eevee.taa_render_samples = int(opt('--samples', 64))
sc.eevee.use_raytracing = True
sc.render.use_motion_blur = False   # goo sheets are rebuilt per sub-frame; Eevee deformation blur turned that into streaks
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'

w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
nt = w.node_tree; bg = nt.nodes['Background']
tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); ramp = nt.nodes.new('ShaderNodeValToRGB')
nt.links.new(tc.outputs['Generated'], sep.inputs[0]); nt.links.new(sep.outputs['Y'], ramp.inputs[0]); nt.links.new(ramp.outputs[0], bg.inputs['Color'])   # gradient on +y: our up (camera on +z)
ramp.color_ramp.elements[0].position = 0.45; ramp.color_ramp.elements[0].color = (0.05, 0.07, 0.14, 1)
ramp.color_ramp.elements[1].position = 0.62; ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1)
bg.inputs['Strength'].default_value = 0.55

cd = bpy.data.cameras.new('Cam'); cd.lens = 85; cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36; cd.clip_end = 300
cam = bpy.data.objects.new('Cam', cd); sc.collection.objects.link(cam); sc.camera = cam
CAM_D = 85 / 36 * 19.2
cam.location = (0, 0, CAM_D)

def sun(name, energy, rot, angle=8, col=(1, 1, 1)):
    ld = bpy.data.lights.new(name, 'SUN'); ld.energy = energy; ld.angle = math.radians(angle); ld.color = col
    o = bpy.data.objects.new(name, ld); sc.collection.objects.link(o); o.rotation_euler = [math.radians(a) for a in rot]; return o
sun('key', 2.2, (-38, -32, 0), 14)
sun('rim', 3.0, (-70, 40, 0), 3, (0.85, 0.92, 1.0))
sun('fill', 0.6, (20, 20, 0), 30)
sweep_ld = bpy.data.lights.new('sweep', 'AREA'); sweep_ld.shape = 'RECTANGLE'; sweep_ld.size = 0.6; sweep_ld.size_y = 30; sweep_ld.energy = 0
SWEEP = bpy.data.objects.new('sweep', sweep_ld); sc.collection.objects.link(SWEEP); SWEEP.location = (-30, 0, 8); SWEEP.rotation_euler = (0, math.radians(-20), 0)

def mat(name, col, rough=0.16, coat=1.0, emit=0.5, spec=0.6):
    m = bpy.data.materials.new(name); m.use_nodes = True; p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*col, 1); p.inputs['Roughness'].default_value = rough
    p.inputs['Coat Weight'].default_value = coat; p.inputs['Coat Roughness'].default_value = 0.03
    p.inputs['Specular IOR Level'].default_value = spec
    p.inputs['Emission Color'].default_value = (*col, 1); p.inputs['Emission Strength'].default_value = emit
    return m
M_BLUE = mat('goo_blue', BLUE, emit=0.55); M_LIGHT = mat('goo_light', LIGHT, emit=0.45)
M_MID = mat('shine', MID, rough=0.1, emit=0.8); M_WHITE = mat('white', WHITE, rough=0.3, coat=0.6, emit=0.55)
M_SLOT = mat('slot', BLUE, rough=0.4, coat=0.2, emit=0.75)

# ---------------------------------------------------------------- helpers
clamp = lambda x, a=0.0, b=1.0: max(a, min(b, x))
def seg(t, a, b): return clamp((t - a) / (b - a)) if b != a else float(t >= a)
def ease_in(u): return u ** 3
def ease_out(u): return 1 - (1 - u) ** 3
def ease_io(u): return 3 * u * u - 2 * u ** 3
def ease_out_back(u, k=1.7): u -= 1; return 1 + u * u * ((k + 1) * u + k)
def spring(t, t0, k=6.5, wf=13.0):
    """0 before t0, then a jelly overshoot settling at 1 (t in frames)."""
    u = (t - t0) / FPS
    return 0.0 if u <= 0 else 1 - math.exp(-k * u) * math.cos(wf * u)
def squash(t, t0, amt=0.10, k=6.5, wf=13.0):
    u = (t - t0) / FPS
    return 0.0 if u <= 0 else amt * math.exp(-k * u) * math.sin(wf * u)

def curve_obj(name, material, extrude, bevel, z=0.0, parent=None, inset=False):
    """inset=True keeps the outline where it was (fine for broad goo sheets); art with thin parts must not inset
    or its fill collapses, so it rounds outward by the bevel instead."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '2D'; cu.fill_mode = 'BOTH'
    cu.extrude = extrude; cu.bevel_depth = bevel; cu.bevel_resolution = 5; cu.offset = -bevel if inset else 0.0
    cu.materials.append(material)
    o = bpy.data.objects.new(name, cu); sc.collection.objects.link(o); o.location.z = z
    if parent: o.parent = parent
    return o

def _area(r): return 0.5 * sum(r[i][0] * r[i - 1][1] - r[i - 1][0] * r[i][1] for i in range(len(r)))
def _inside(pt, r):
    x, y = pt; c = False; j = len(r) - 1
    for i in range(len(r)):
        if (r[i][1] > y) != (r[j][1] > y) and x < (r[j][0] - r[i][0]) * (y - r[i][1]) / (r[j][1] - r[i][1] + 1e-12) + r[i][0]: c = not c
        j = i
    return c
def orient(rings):
    """Outer rings counter-clockwise, holes clockwise (by nesting depth), so every fill faces the camera."""
    rings = [list(r) for r in rings if len(r) >= 3]; out = []
    for i, r in enumerate(rings):
        depth = sum(1 for j, q in enumerate(rings) if j != i and abs(_area(q)) > abs(_area(r)) and _inside(r[0], q))
        want_ccw = depth % 2 == 0
        out.append(r if (_area(r) > 0) == want_ccw else r[::-1])
    return out

def set_rings(o, rings):
    cu = o.data; cu.splines.clear()
    for r in orient(rings):
        if len(r) < 3: continue
        sp = cu.splines.new('POLY'); sp.points.add(len(r) - 1)
        for i, (x, y) in enumerate(r): sp.points[i].co = (x, y, 0, 1)
        sp.use_cyclic_u = True

def empty(name, loc=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None); sc.collection.objects.link(e); e.location = loc
    if parent: e.parent = parent
    return e

def art_rings(rings, s, cx, cy):
    return [[((x - cx) * s, -(y - cy) * s) for x, y in r['pts']] for r in rings]

def build_logo(name, width, with_bugs=True):
    """3D primary logo: puffy goo blob, raised white letters, shine streaks, bugs as line art on white bodies.
    Returns (root, parts) with pivots: parts['letters'], parts['beetle'|'hopper'|'sinker'] (bugs pivot at their feet)."""
    A = ART['logo']; W, H = A['size']; s = width / W; cx, cy = W / 2, H / 2
    root = empty(name); parts = {}
    blob = curve_obj(name + '_goo', M_BLUE, 0.36, 0.14, 0, root); set_rings(blob, art_rings(A['goo'], s, cx, cy))
    let = empty(name + '_letters_piv', (0, -(1790 + (H - 1790) / 2 - cy) * s, 0.58), root)
    lo = curve_obj(name + '_letters', M_WHITE, 0.07, 0.03, 0, let)
    set_rings(lo, [[(x, y - let.location.y) for x, y in r] for r in art_rings(A['letters'], s, cx, cy)])
    sh = curve_obj(name + '_shine', M_MID, 0.015, 0.012, 0.56, root); set_rings(sh, art_rings(A['shine'], s, cx, cy))
    parts['letters'] = let; parts['blob'] = blob
    if with_bugs:
        for bug in ('beetle', 'hopper', 'sinker'):
            x0, y0, x1, y1 = A[bug + '_bbox']; px, py = (x0 + x1) / 2, y1
            piv = empty(f'{name}_{bug}', ((px - cx) * s, -(py - cy) * s, -0.05 if bug == 'sinker' else 0.05), root)
            fill = curve_obj(f'{name}_{bug}_fill', M_WHITE, 0.03, 0.01, 0.0, piv)
            line = curve_obj(f'{name}_{bug}_line', M_BLUE, 0.06, 0.015, 0.09, piv)
            set_rings(fill, art_rings(A[bug + '_fill'], s, px, py)); set_rings(line, art_rings(A[bug + '_line'], s, px, py))
            parts[bug] = piv
    return root, parts

def build_bug(name, bug, height):
    A = ART['logo']; x0, y0, x1, y1 = A[bug + '_bbox']; s = height / (y1 - y0); px, py = (x0 + x1) / 2, y1
    piv = empty(name)
    set_rings(curve_obj(name + '_fill', M_WHITE, 0.03, 0.01, 0.0, piv), art_rings(A[bug + '_fill'], s, px, py))
    set_rings(curve_obj(name + '_line', M_BLUE, 0.06, 0.015, 0.09, piv), art_rings(A[bug + '_line'], s, px, py))
    return piv

def build_afpod(name, width):
    A = ART['afpod']; W, H = A['size']; s = width / W; cx, cy = W / 2, H / 2
    root = empty(name)
    set_rings(curve_obj(name + '_goo', M_BLUE, 0.36, 0.14, 0, root), art_rings(A['goo'], s, cx, cy))
    let = empty(name + '_let', (0, 0, 0.58), root)
    set_rings(curve_obj(name + '_letters', M_WHITE, 0.07, 0.03, 0, let), art_rings(A['letters'], s, cx, cy))
    set_rings(curve_obj(name + '_shine', M_MID, 0.015, 0.012, 0.56, root), art_rings(A['shine'], s, cx, cy))
    return root, let

def build_text(name, line, height, material, align='center', z=0.0):
    d = TXT[line]; s = height / 720.0
    ox = {'center': -d['w'] / 2, 'left': 0, 'right': -d['w']}[align]
    piv = empty(name)
    o = curve_obj(name + '_txt', material, 0.04, 0.015, z, piv)
    set_rings(o, [[((x + ox) * s, (y - 360) * s) for x, y in r['pts']] for r in d['rings']])
    return piv

def rounded_rect(cx, cy, w, h, r, n=10):
    pts = []
    for (qx, qy, a0) in ((cx + w / 2 - r, cy + h / 2 - r, 0), (cx - w / 2 + r, cy + h / 2 - r, 90), (cx - w / 2 + r, cy - h / 2 + r, 180), (cx + w / 2 - r, cy - h / 2 + r, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n); pts.append((qx + r * math.cos(a), qy + r * math.sin(a)))
    return pts

# ---------------------------------------------------------------- goo sheets
class Drips:
    """Rounded goo fingers along an edge. lengths scale with a per-frame factor (speed, idle sway)."""
    def __init__(self, seed, span, n, wmin=0.22, wmax=0.55, lmin=0.3, lmax=1.6):
        R = random.Random(seed)
        xs = sorted(R.uniform(-span, span) for _ in range(n))
        self.d = [(x, R.uniform(wmin, wmax), R.uniform(lmin, lmax), R.uniform(0, 6.28)) for x in xs]
    def depth(self, a, scale, t=0.0, sway=0.0):
        best = 0.0
        for x, wd, L, ph in self.d:
            L2 = L * scale * (1 + sway * math.sin(t * 0.0523 + ph))
            dx = a - x
            if abs(dx) < wd:   # superellipse: full, rounded tips like the brand's drips
                best = max(best, L2 * (1 - abs(dx / wd) ** 2.6) ** (1 / 2.6) + 0.10 * L2 * (1 - abs(dx) / wd))
            sk = 0.30 * min(L2, 1.0) * math.exp(-(dx / (2.0 * wd)) ** 2)
            best = max(best, sk)
        return best

class Sheet:
    """A goo sheet travelling along dir. lead(a,t) / tail(a,t) give the b coordinate of each edge (b along dir)."""
    def __init__(self, name, material, z, direction, span, lead, tail, thick=0.24, bevel=0.12, step=0.04):
        self.o = curve_obj(name, material, thick, bevel, z, inset=True); self.dir = direction; self.span = span
        try: self.o.cycles.use_deform_motion = False   # rebuilt every sub-frame: deformation blur can't match points
        except Exception: pass
        self.lead, self.tail, self.step = lead, tail, step
    def update(self, t):
        n = int(2 * self.span / self.step) + 1
        As = [-self.span + i * self.step for i in range(n)]
        L = [self.lead(a, t) for a in As]; T = [self.tail(a, t) for a in As]
        if max(l - tt for l, tt in zip(L, T)) <= 0.01: set_rings(self.o, []); self.o.hide_render = True; return
        self.o.hide_render = False
        dx, dy = self.dir; px, py = -dy, dx            # perp (a axis)
        to = lambda a, b: (a * px + b * dx, a * py + b * dy)
        # one ring per stretch where the sheet still has thickness: pinched zero-width parts made streak artifacts
        rings, run = [], []
        for a, l, tt in zip(As + [None], L + [0], T + [1]):
            if a is not None and l - tt > 0.03: run.append((a, l, tt)); continue
            if len(run) >= 3:
                rings.append([to(a_, l_) for a_, l_, _ in run] + [to(a_, t_) for a_, _, t_ in reversed(run)])
            run = []
        set_rings(self.o, rings)

def speed(f, t, h=0.5): return abs(f(t + h) - f(t - h))

def drip_sheet(name, material, z, seed, enter, exit_, direction=(0, -1), span=10.6, n=16, lmax=1.4, hang=0.0, hang_drips=None, sway=0.0):
    """enter(t) / exit_(t): b positions of lead / tail edge levels. Drip length grows with speed; hang adds a resting length."""
    dl = Drips(seed, span, n, lmax=lmax); dt = Drips(seed + 99, span, n - 3, lmin=0.2, lmax=1.0)
    hd = hang_drips or dl
    def lead(a, t):
        v = speed(enter, t)
        return enter(t) + dl.depth(a, min(2.2, 0.15 + v * 2.2)) + (hd.depth(a, hang, t, sway) if hang else 0)
    def tail(a, t):
        v = speed(exit_, t)
        return exit_(t) - dt.depth(a, min(2.0, v * 2.0))
    return Sheet(name, material, z, direction, span, lead, tail)

def lerp(a, b, u): return a + (b - a) * u

# ---------------------------------------------------------------- pieces
ANIM = []                      # callables f(t)
FRAMES = {'intro': 112, 'trans_drip': 40, 'trans_splat': 40, 'trans_sweep': 46, 'endcard': 150}[PIECE]
INFO = {}

if PIECE == 'trans_drip':
    # light-blue sheet then brand-blue sheet fall over the frame; blue leaves first, then light blue. Cut on frame 18.
    lb = drip_sheet('lb', M_LIGHT, 0.0, 11, lambda t: lerp(-6.6, 7.6, ease_in(seg(t, 0, 14))), lambda t: lerp(-22, 8.6, 0) if t < 20 else lerp(-6.9, 8.6, ease_in(seg(t, 21, 37))))
    bl = drip_sheet('bl', M_BLUE, 0.7, 23, lambda t: lerp(-6.6, 7.6, ease_in(seg(t, 3, 17))), lambda t: -22 if t < 18 else lerp(-6.9, 8.6, ease_in(seg(t, 18, 33))))
    ANIM += [lb.update, bl.update]
    INFO = {'cut': 18, 'full_cover': '17-20'}

elif PIECE == 'trans_splat':
    # a light-blue then brand-blue goo blob splats out to fill the frame, the AF POD mark pops in the middle, then it all sucks back.
    A = ART['afpod']
    def blob_sheet(name, material, z):
        o = curve_obj(name, material, 0.4, 0.3, z); W, H = A['size']; s = 34.0 / W
        set_rings(o, art_rings(A['goo'], s, W / 2, H / 2)); return o
    b1 = blob_sheet('blob_lb', M_LIGHT, 0.0); b2 = blob_sheet('blob_bl', M_BLUE, 0.8)
    mark, mlet = build_afpod('mark', 4.6); mark.location.z = 1.9
    def f(t):
        g1 = spring(t, 0, 7, 11) * (1 - ease_in(seg(t, 26, 37)))
        g2 = spring(t, 3, 7, 11) * (1 - ease_in(seg(t, 23, 33)))
        for o, g, r0 in ((b1, g1, -12), (b2, g2, 10)):
            sq = squash(t, 0, 0.12)
            o.scale = (max(g, 0.0001) * (1 + sq), max(g, 0.0001) * (1 - sq), 1)
            o.rotation_euler.z = math.radians(r0 * (1 - seg(t, 0, 30)))
            o.hide_render = g < 0.002
        m = spring(t, 9, 6, 14) * (1 - ease_in(seg(t, 21, 28)))
        sq = squash(t, 9, 0.14, 6, 14)
        mark.scale = (max(m, 0.0001) * (1 + sq), max(m, 0.0001) * (1 - sq), max(m, 0.0001))
        mark.rotation_euler = (0, math.radians(8 * math.sin(t * 0.25) * (1 - seg(t, 9, 24))), math.radians(-6 + 6 * seg(t, 9, 20)))
        mark.hide_render = m < 0.002
    ANIM.append(f)
    INFO = {'cut': 18, 'full_cover': '12-24'}

elif PIECE == 'trans_sweep':
    # goo floods across left to right with Liam (sunglasses grasshopper) riding the front; Angus (wizard beetle) rides the back.
    enter_l = lambda t: lerp(-11.2, 11.2, ease_io(seg(t, 0, 17)))
    enter_b = lambda t: lerp(-11.2, 11.2, ease_io(seg(t, 3, 20)))
    exit_b = lambda t: -30 if t < 22 else lerp(-11.4, 11.6, ease_io(seg(t, 22, 38)))
    exit_l = lambda t: -30 if t < 25 else lerp(-11.4, 11.6, ease_io(seg(t, 25, 42)))
    lb = drip_sheet('lb', M_LIGHT, 0.0, 41, enter_l, exit_l, direction=(1, 0), span=6.4, n=10, lmax=1.1)
    bl = drip_sheet('bl', M_BLUE, 0.7, 53, enter_b, exit_b, direction=(1, 0), span=6.4, n=10, lmax=1.1)
    liam = build_bug('liam', 'hopper', 3.6); angus = build_bug('angus', 'beetle', 3.4)
    def f(t):
        lb.update(t); bl.update(t)
        x = enter_b(t) - 1.4; hop = abs(math.sin(t * 0.42)) * 1.1
        liam.location = (x, -1.6 + hop, 1.6); liam.rotation_euler = (0, 0, math.radians(-12 * math.cos(t * 0.42)))
        s = spring(t, 2, 7, 12) * (1 - ease_in(seg(t, 17, 22)))
        liam.scale = (s, s, s); liam.hide_render = s < 0.002
        xa = exit_l(t) + 1.3 if t >= 25 else -14
        angus.location = (xa, -1.7 + abs(math.sin(t * 0.38)) * 0.7, 1.6)
        sa = spring(t, 24, 7, 12) * (1 - ease_in(seg(t, 38, 44)))
        angus.scale = (sa, sa, sa); angus.hide_render = sa < 0.002
        angus.rotation_euler = (0, 0, math.radians(8 * math.sin(t * 0.38)))
    ANIM.append(f)
    INFO = {'cut': 21, 'full_cover': '20-22'}

elif PIECE == 'intro':
    # light-blue flood, brand-blue drips land at the top and a goo pool rises, the logo splashes up out of the pool,
    # bugs pop on, a light sweep crosses the letters, then everything drains away down the frame.
    lb = drip_sheet('lb', M_LIGHT, 0.0, 7, lambda t: lerp(-6.6, 7.8, ease_in(seg(t, 0, 16))),
                    lambda t: -22 if t < 84 else lerp(-6.9, 8.8, ease_in(seg(t, 86, 106))))
    hang = Drips(77, 10.6, 14, wmin=0.18, wmax=0.42, lmin=0.25, lmax=1.5)
    fall = lambda t: 15.5 * ease_in(seg(t, 82, 100))        # the band and its drips fall away together
    top = drip_sheet('top', M_BLUE, 0.9, 19, lambda t: lerp(-7.5, -4.75, ease_out_back(seg(t, 5, 22), 1.4)) + fall(t),
                     lambda t: -22 if t < 82 else -6.9 + fall(t), hang=1.0, hang_drips=hang, sway=0.12)
    pool_lvl = lambda t: lerp(-7.2, -4.2, ease_out_back(seg(t, 9, 27), 1.5)) if t < 84 else lerp(-4.2, -8.0, ease_in(seg(t, 84, 100)))
    pool = Sheet('pool', M_BLUE, 0.9, (0, 1), 10.6,
                 lambda a, t: pool_lvl(t) + 0.16 * math.sin(a * 1.3 + t * 0.21) + 0.09 * math.sin(a * 2.9 - t * 0.33) + 0.6 * math.exp(-(a / 3.0) ** 2) * seg(t, 16, 26) * (1 - seg(t, 26, 40)),
                 lambda a, t: -20)
    logo, P = build_logo('logo', 11.2); LOGO_Y = 0.15
    def f(t):
        lb.update(t); top.update(t); pool.update(t)
        g = spring(t, 15, 6.0, 12.0); sq = squash(t, 15, 0.12, 6, 12)
        rise = (1 - ease_out_back(seg(t, 15, 30), 1.2)) * -4.5
        drop = ease_in(seg(t, 84, 100)) * -12
        push = 1 + 0.045 * ease_io(seg(t, 30, 84))
        logo.location = (0, LOGO_Y + rise + drop, 2.0)
        logo.scale = (max(g, 1e-4) * push * (1 + sq), max(g, 1e-4) * push * (1 - sq), max(g, 1e-4) * push)
        logo.rotation_euler = (math.radians(-6 * (1 - seg(t, 15, 40)) + 2 * math.sin(t * 0.05)), math.radians(-5 + 8 * ease_io(seg(t, 18, 84))), math.radians(-3 * squash(t, 15, 1, 5, 9) - 6 * ease_in(seg(t, 84, 100))))
        lg = spring(t, 21, 7, 15); P['letters'].scale = (0.55 + 0.45 * lg, 0.55 + 0.45 * lg, 1)
        for bug, t0 in (('beetle', 27), ('hopper', 31)):
            s = spring(t, t0, 6.5, 14); sqb = squash(t, t0, 0.18, 6.5, 14)
            P[bug].scale = (max(s, 1e-4) * (1 - sqb), max(s, 1e-4) * (1 + sqb), max(s, 1e-4))
            P[bug].hide_render = s < 0.002
        s = spring(t, 35, 5.5, 11); P['sinker'].location.y = P['sinker']['y0'] - 1.6 * (1 - s)
        P['hopper'].rotation_euler.z = math.radians(3 * math.sin(t * 0.18)); P['beetle'].rotation_euler.z = math.radians(-3 * math.sin(t * 0.15 + 1))
        u = seg(t, 44, 70); SWEEP.location.x = lerp(-16, 16, ease_io(u)); sweep_ld.energy = 260 * math.sin(math.pi * u)
        cam.location = (0.3 * math.sin(t * 0.03), 0.15 * math.sin(t * 0.021), CAM_D)
    P['sinker']['y0'] = P['sinker'].location.y
    ANIM.append(f)
    INFO = {'covered_from': 16, 'clear_from': 106}

elif PIECE == 'endcard':
    # floods in like the intro, then holds an end screen with room for YouTube's elements; frames 30-149 loop seamlessly.
    LOOP = 120; om = lambda t: 2 * math.pi * (t - 30) / LOOP
    lb = drip_sheet('lb', M_LIGHT, 0.0, 9, lambda t: lerp(-6.6, 7.8, ease_in(seg(t, 0, 16))), lambda t: -22)
    hang = Drips(5, 10.6, 13, wmin=0.18, wmax=0.40, lmin=0.25, lmax=1.1)
    # band across the top right: the KEEP WATCHING label sits on it
    def band(a, t):
        base = lerp(-7.5, -4.25, ease_out_back(seg(t, 6, 22), 1.4))
        right = 1 / (1 + math.exp(-(a - 0.8) * 3))          # 0 on the left, 1 on the right
        idle = 0.08 * math.sin(om(t) + a) if t >= 30 else 0
        return lerp(-7.5, base, right) - 0.55 * right + hang.depth(a, right * 1.0) * (0.85 if abs(a - 4.97) > 3.8 else 0.25) + idle
    top = Sheet('top', M_BLUE, 0.9, (0, -1), 10.6, band, lambda a, t: -22)
    def pool_top(a, t):
        a = -a                                              # this sheet's a axis runs right to left
        lvl = lerp(-7.2, -3.25, ease_out_back(seg(t, 10, 28), 1.5))
        mound = lerp(lvl, -6.5, 1 / (1 + math.exp(-(a - 0.75) * 2.2)))
        idle = (0.10 * math.sin(a * 1.3 + om(t)) + 0.05 * math.sin(a * 2.7 - 2 * om(t))) if t >= 30 else 0.10 * math.sin(a * 1.3)
        return mound + idle
    pool = Sheet('pool', M_BLUE, 0.9, (0, 1), 10.6, pool_top, lambda a, t: -20)
    logo, P = build_logo('logo', 7.9)
    LX, LY = (520 - 960) / 100, (540 - 330) / 100
    t1 = build_text('t1', 'NEW EPISODES EVERY THURSDAY', 0.33, M_WHITE); t1.location = ((520 - 960) / 100, (540 - 905) / 100, 1.3)
    t2 = build_text('t2', '8AM PT/11AM ET', 0.30, M_WHITE); t2.location = ((520 - 960) / 100, (540 - 958) / 100, 1.3)
    kw = build_text('kw', 'KEEP WATCHING', 0.50, M_WHITE); kw.location = ((1470 - 960) / 100, (540 - 62) / 100, 1.3)
    sub = build_text('sub', 'SUBSCRIBE', 0.56, M_BLUE, align='left'); sub.location = ((440 - 960) / 100, (540 - 745) / 100, 0.6)
    # placeholders where YouTube's end-screen elements go: two 16:9 video slots and the subscribe circle
    slots = []
    for i, cy in enumerate((352, 788)):
        sl = empty(f'slot{i}', ((1470 - 960) / 100, (540 - cy) / 100, 0.5))
        rr = rounded_rect(0, 0, 7.36, 4.14, 0.32); inner = rounded_rect(0, 0, 7.2, 3.98, 0.26)
        set_rings(curve_obj(f'slot{i}_rim', M_BLUE, 0.06, 0.05, 0, sl), [rr, inner])
        set_rings(curve_obj(f'slot{i}_fill', M_SLOT, 0.01, 0.0, -0.05, sl), [inner])
        slots.append(sl)
    circ = empty('subcircle', ((300 - 960) / 100, (540 - 745) / 100, 0.5))
    ring = lambda r: [(r * math.cos(2 * math.pi * i / 96), r * math.sin(2 * math.pi * i / 96)) for i in range(96)]
    set_rings(curve_obj('circ_rim', M_BLUE, 0.06, 0.05, 0, circ), [ring(1.14), ring(1.02)])
    set_rings(curve_obj('circ_fill', M_SLOT, 0.01, 0.0, -0.05, circ), [ring(1.02)])
    def f(t):
        lb.update(t); top.update(t); pool.update(t)
        g = spring(t, 13, 6, 12); sq = squash(t, 13, 0.12, 6, 12)
        fl = 0.06 * math.sin(om(t)) if t >= 30 else 0
        logo.location = (LX, LY + fl - (1 - ease_out_back(seg(t, 13, 26), 1.2)) * 3.0, 1.6)
        logo.scale = (max(g, 1e-4) * (1 + sq), max(g, 1e-4) * (1 - sq), max(g, 1e-4))
        logo.rotation_euler = (0, math.radians(3 * math.sin(om(t))) if t >= 30 else 0, 0)
        lg = spring(t, 17, 7, 15); P['letters'].scale = (0.55 + 0.45 * lg, 0.55 + 0.45 * lg, 1)
        for bug, t0, ph in (('beetle', 19, 0), ('hopper', 22, 2)):
            s = spring(t, t0, 6.5, 14); sqb = squash(t, t0, 0.18, 6.5, 14)
            P[bug].scale = (max(s, 1e-4) * (1 - sqb), max(s, 1e-4) * (1 + sqb), max(s, 1e-4)); P[bug].hide_render = s < 0.002
            P[bug].rotation_euler.z = math.radians(3 * math.sin(om(t) * 2 + ph)) if t >= 30 else 0
        s = spring(t, 24, 5.5, 11); P['sinker'].location.y = P['sinker']['y0'] - 1.4 * (1 - s) + (0.08 * math.sin(om(t) * 3) if t >= 30 else 0)
        for o, t0 in ((t1, 21), (t2, 23), (kw, 18), (sub, 25)):
            s = spring(t, t0, 7, 14); o.scale = (max(s, 1e-4),) * 3; o.hide_render = s < 0.002
        for o, t0 in ((slots[0], 20), (slots[1], 23), (circ, 25)):
            s = spring(t, t0, 7, 13); o.scale = (max(s, 1e-4),) * 3; o.hide_render = s < 0.002
        u = ((t - 30) % LOOP) / LOOP if t >= 30 else 0; SWEEP.location.x = lerp(-16, 16, u); sweep_ld.energy = 160 * math.sin(math.pi * u) ** 2
    P['sinker']['y0'] = P['sinker'].location.y
    ANIM.append(f)
    INFO = {'in_frames': '0-29', 'loop': '30-149 (seamless, repeat to length)'}

SLOW = float(opt('--slow', 1.0))
def handler(scene, *_):
    t = (scene.frame_current + scene.frame_subframe) / SLOW
    for f in ANIM: f(t)
bpy.app.handlers.frame_change_pre.append(handler)

FRAMES = int(round(FRAMES * SLOW))
sc.frame_start, sc.frame_end = 0, FRAMES - 1
if opt('--frames'): a, b = opt('--frames').split('-'); sc.frame_start, sc.frame_end = int(a), int(b)
os.makedirs(OUT, exist_ok=True)
json.dump({'piece': PIECE, 'frames': FRAMES, 'fps': FPS, 'slow': SLOW, **INFO}, open(os.path.join(OUT, 'info.json'), 'w'))
if opt('--still'):
    for fr in opt('--still').split(','):
        sc.frame_set(int(fr)); handler(sc)
        sc.render.filepath = os.path.join(OUT, f'still_{int(fr):03d}.png'); bpy.ops.render.render(write_still=True)
else:
    sc.render.filepath = os.path.join(OUT, 'f_')
    bpy.ops.render.render(animation=True)
