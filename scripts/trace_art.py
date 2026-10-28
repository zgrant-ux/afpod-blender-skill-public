"""Trace the AF Pod brand art (rendered from the 2026 rebrand PDF at 8000px) into layered polygons for Blender.

  python3 trace_art.py <src dir>   ->  <src>/art_shapes.json

Layers (px, y down, each layer = list of {"pts": [[x,y],...]} outer rings and holes; Blender fills even-odd):
  logo:  goo, letters, shine, beetle_line/fill, sinker_line/fill, hopper_line/fill   (page 1 primary logo)
  afpod: goo, letters, shine                                                         (page 3 primary social logo)
"""
import cv2, json, sys, numpy as np

SRC = sys.argv[1]
BLUE, LB = (0, 97, 239), (98, 177, 255)


def near(img, c, t):
    b, g, r = [img[..., i].astype(int) for i in range(3)]
    return (abs(r - c[0]) + abs(g - c[1]) + abs(b - c[2])) < t


def fill_holes(m):
    m = m.astype(np.uint8) * 255
    ff = np.pad(m, 1); h, w = ff.shape
    cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 128)
    return (ff[1:-1, 1:-1] != 128)


def clean(m, k=3):
    m = m.astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    return m > 0


def rings(mask, eps=1.2, min_area=40):
    cs, hier = cv2.findContours(mask.astype(np.uint8) * 255, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    out = []
    for c in cs:
        if abs(cv2.contourArea(c)) < min_area: continue
        a = cv2.approxPolyDP(c, eps, True)[:, 0, :]
        if len(a) >= 3: out.append({'pts': a.tolist()})
    return out


def goo_layers(img, bg_white=True):
    blue = clean(near(img, BLUE, 70)); lb = clean(near(img, LB, 70))
    return blue, lb


shapes = {}
# ---- page 1: primary logo ----
p1 = cv2.imread(f'{SRC}/page1.png', cv2.IMREAD_UNCHANGED)[1100:4700, 400:4900, :3]
blue, lb = goo_layers(p1)
H, W = blue.shape
yy = np.arange(H)[:, None] * np.ones((1, W))
GOO_TOP = 1790
goo_body = fill_holes((blue | lb) & (yy > GOO_TOP))
letters = goo_body & ~blue & ~lb
art = (blue | lb) & (yy <= GOO_TOP + 60) & ~goo_body | (blue & (yy <= GOO_TOP))
shapes['logo'] = {'size': [W, H], 'goo': rings(goo_body), 'letters': rings(letters), 'shine': rings(lb & goo_body)}
xx = np.ones((H, 1)) * np.arange(W)[None, :]
for name, (x0, x1) in {'beetle': (0, 1650), 'sinker': (1650, 2700), 'hopper': (2700, W)}.items():
    line = art & (xx >= x0) & (xx < x1)
    shapes['logo'][name + '_line'] = rings(line)
    shapes['logo'][name + '_fill'] = rings(fill_holes(line) & ~line | line)
    ys, xs = np.where(line)
    shapes['logo'][name + '_bbox'] = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]

# ---- page 3: AF POD social mark (blob on a light-blue tile) ----
p3 = cv2.imread(f'{SRC}/page3.png', cv2.IMREAD_UNCHANGED)[840:2520, 5040:6760, :3]
blue3, lb3 = goo_layers(p3)
g3 = fill_holes(blue3 | lb3)
shapes['afpod'] = {'size': [p3.shape[1], p3.shape[0]], 'goo': rings(g3), 'letters': rings(g3 & ~blue3 & ~lb3, min_area=200),
                   'shine': rings(lb3 & g3)}

json.dump(shapes, open(f'{SRC}/art_shapes.json', 'w'))
dbg = np.zeros((H, W, 3), np.uint8)
dbg[goo_body] = (239, 97, 0); dbg[letters] = (255, 255, 255); dbg[lb & goo_body] = (255, 177, 98); dbg[art] = (0, 200, 255)
cv2.imwrite(f'{SRC}/trace_debug.png', cv2.resize(dbg, None, fx=0.25, fy=0.25))
for k, v in shapes.items():
    print(k, {n: len(r) for n, r in v.items() if isinstance(r, list) and r and isinstance(r[0], dict)})
