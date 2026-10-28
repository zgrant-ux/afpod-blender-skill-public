"""Set lines of Sanurumi Handwritten (the subset embedded in the AF Pod rebrand PDF) as flattened polygons for Blender.

  python3 text_shapes.py <src dir>   ->  <src>/text_shapes.json  {line: {"w": em-units width, "rings": [{"pts": ...}]}}
Units are font units (1000/em), y up. The subset has A-I K-P R-W Y, 1, 8, '-', '/', space (no J, Q, X, Z, 0, 2-7).
"""
import io, json, sys
from fontTools.cffLib import CFFFontSet
from fontTools.pens.basePen import BasePen

SRC = sys.argv[1]
LINES = ['NEW EPISODES EVERY THURSDAY', '8AM PT/11AM ET', 'SUBSCRIBE', 'KEEP WATCHING', 'ALMOST FRIDAY PODCAST']
NAMES = {' ': 'space', '8': 'eight', '1': 'one', '/': 'slash', '-': 'hyphenminus'}
TRACK = 40   # extra letter spacing, font units


class Flat(BasePen):
    def __init__(self, gs, dx):
        super().__init__(gs); self.rings = []; self.cur = []; self.dx = dx
    def _moveTo(self, p): self.cur = [self.p(p)]
    def _lineTo(self, p): self.cur.append(self.p(p))
    def _curveToOne(self, a, b, c):
        p0 = self.cur[-1]; q0 = (p0[0] - self.dx, p0[1])
        for i in range(1, 9):
            t = i / 8; u = 1 - t
            x = u**3 * q0[0] + 3 * u * u * t * a[0] + 3 * u * t * t * b[0] + t**3 * c[0]
            y = u**3 * q0[1] + 3 * u * u * t * a[1] + 3 * u * t * t * b[1] + t**3 * c[1]
            self.cur.append(self.p((x, y)))
    def _closePath(self):
        if len(self.cur) > 2: self.rings.append({'pts': self.cur})
        self.cur = []
    _endPath = _closePath
    def p(self, q): return [round(q[0] + self.dx, 2), round(q[1], 2)]


cff = CFFFontSet(); cff.decompile(io.BytesIO(open(f'{SRC}/SanurumiHandwrittenRegular.otf', 'rb').read()), None)
font = cff[cff.fontNames[0]]; cs = font.CharStrings
out = {}
for line in LINES:
    x = 0; rings = []
    for ch in line:
        g = cs[NAMES.get(ch, ch)]; g.decompile()
        pen = Flat(cs, x); g.draw(pen); rings += pen.rings
        x += (g.width if g.width is not None else font.Private.defaultWidthX) + TRACK
    out[line] = {'w': x - TRACK, 'rings': rings}
    print(line, round(x), len(rings))
json.dump(out, open(f'{SRC}/text_shapes.json', 'w'))
