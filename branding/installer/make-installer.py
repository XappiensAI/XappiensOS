#!/usr/bin/env python3
"""Genera la imagen de marca del instalador y del arranque de la ISO.

Todo sale de rejillas de píxeles (el mismo estilo y la misma paleta que la
pantalla de arranque de branding/plymouth/make-theme.py, de la que reutiliza
la burbuja con la bombilla del logo y la fuente pixelada):

  config/xappiens-os/includes.chroot/usr/share/icons/hicolor/scalable/apps/
      distributor-logo-xappiens.svg   logo del sistema (os-release LOGO=)

  packaging/xappiens-installer-branding/files/usr/share/
      xappiens/installer/*.png        ilustraciones de cada paso del instalador
      icons/hicolor/scalable/apps/xappiens-installer.svg   icono del instalador

  config/xappiens-os/includes.chroot/usr/share/pixmaps/faces/
      xappiens.png                    avatar de usuario por defecto

  config/xappiens-os/grub-theme/      tema del menú de arranque de la ISO
      theme.txt, background.png, logo.png, select_*.png

  branding/installer/preview.png      hoja de contactos (no se instala)

Sólo usa la biblioteca estándar:  python3 branding/installer/make-installer.py
"""
import importlib.util
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))

_spec = importlib.util.spec_from_file_location(
    "xappiens_plymouth", os.path.join(REPO, "branding", "plymouth", "make-theme.py"))
pl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pl)

Canvas, mix = pl.Canvas, pl.mix
BUBBLE, PALETTE, FONT = pl.BUBBLE, pl.PALETTE, pl.FONT

LOGO_SVG = os.path.join(REPO, "config", "xappiens-os", "includes.chroot", "usr", "share",
                        "icons", "hicolor", "scalable", "apps", "distributor-logo-xappiens.svg")
PKG_FILES = os.path.join(REPO, "packaging", "xappiens-installer-branding", "files")
ART_DIR = os.path.join(PKG_FILES, "usr", "share", "xappiens", "installer")
INSTALLER_SVG = os.path.join(PKG_FILES, "usr", "share", "icons", "hicolor", "scalable",
                             "apps", "xappiens-installer.svg")
GRUB_DIR = os.path.join(REPO, "config", "xappiens-os", "grub-theme")
AVATAR_PNG = os.path.join(REPO, "config", "xappiens-os", "includes.chroot", "usr", "share",
                          "pixmaps", "faces", "xappiens.png")

# --------------------------------------------------------------------------
# Paleta (la de la marca, ver branding/plymouth/README.md)
# --------------------------------------------------------------------------
OFF = pl.BUBBLE_FILL      # #E0EDED
OUTLINE = pl.OUTLINE      # #738794
INK = pl.INK              # #524B62
BULB = pl.BULB            # #E8C984
SHADE = pl.BULB_SHADE     # #D5A57D
SHINE = pl.BULB_SHINE     # #FAF9C6
METAL = pl.METAL          # #A8B8C2
METAL_SHINE = pl.METAL_SHINE
HOT = pl.RAY_HOT          # #DE9654
WARM = pl.WARM
BG_TOP, BG_BOTTOM = pl.BG_TOP, pl.BG_BOTTOM
# Insignia circular de las ilustraciones (tonos de la tinta del logo)
BADGE = (42, 38, 51)      # #2A2633
BADGE_FLOOR = (51, 46, 62)
BADGE_DOT = (64, 59, 78)
GLASS_OFF = (150, 160, 168)   # bombilla apagada
GLASS_OFF_SHADE = (115, 125, 135)
GLASS_OFF_SHINE = (196, 206, 210)

# --------------------------------------------------------------------------
# Lienzo de módulos (un "píxel" del dibujo) que luego se escala a PNG
# --------------------------------------------------------------------------
N = 48        # módulos por lado de cada ilustración
MOD = 10      # píxeles por módulo -> 480 x 480 px


class Pix:
    def __init__(self, w=N, h=N):
        self.w, self.h = w, h
        self.c = [[None] * w for _ in range(h)]

    def put(self, x, y, col):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.c[y][x] = col

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.c[y][x]
        return None

    def rect(self, x, y, w, h, col):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.put(xx, yy, col)

    def box(self, x, y, w, h, fill, line, cut=True):
        """Rectángulo con borde de 1 módulo y esquinas recortadas (pixel-art)."""
        self.rect(x + 1, y + 1, w - 2, h - 2, fill)
        self.rect(x + 1, y, w - 2, 1, line)
        self.rect(x + 1, y + h - 1, w - 2, 1, line)
        self.rect(x, y + 1, 1, h - 2, line)
        self.rect(x + w - 1, y + 1, 1, h - 2, line)
        if not cut:
            for xx, yy in ((x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)):
                self.put(xx, yy, line)

    def disc(self, cx, cy, r, col):
        for y in range(self.h):
            for x in range(self.w):
                if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= r * r:
                    self.c[y][x] = col

    def grid(self, rows, x0, y0, palette):
        for r, line in enumerate(rows):
            for c, ch in enumerate(line):
                if ch in palette:
                    self.put(x0 + c, y0 + r, palette[ch])

    def text(self, s, x, y, col, font=None):
        font = font or MINI
        for ch in s:
            g = font[ch]
            self.grid(g, x, y, {"#": col})
            x += len(g[0]) + 1
        return x

    def copy(self):
        p = Pix(self.w, self.h)
        p.c = [row[:] for row in self.c]
        return p

    def render(self, unit=MOD, pad=0):
        cv = Canvas(self.w * unit + 2 * pad, self.h * unit + 2 * pad)
        for y, row in enumerate(self.c):
            for x, col in enumerate(row):
                if col is not None:
                    cv.rect(pad + x * unit, pad + y * unit, unit, unit, col)
        return cv


def text_width(s, font=None):
    font = font or MINI
    return sum(len(font[ch][0]) for ch in s) + len(s) - 1


# Fuente mínima de 5 módulos de alto para los rótulos de las ilustraciones.
MINI = {
    "H": ["#.#", "#.#", "###", "#.#", "#.#"],
    "i": ["#", ".", "#", "#", "#"],
    "o": ["...", "###", "#.#", "#.#", "###"],
    "l": ["#.", "#.", "#.", "#.", "##"],
    "a": ["...", "##.", "..#", "#.#", "###"],
    "A": [".#.", "#.#", "###", "#.#", "#.#"],
    "!": ["#", "#", "#", ".", "#"],
    "?": ["##.", "..#", ".#.", "...", ".#."],
    ".": [".", ".", ".", ".", "#"],
}

# --------------------------------------------------------------------------
# Piezas comunes
# --------------------------------------------------------------------------
# La bombilla sola, recortada de la burbuja del logo (filas 6-22).
BULB_ROWS = []
for _r in range(6, 23):
    line = ""
    for _c in range(8, 20):
        ch = BUBBLE[_r][_c]
        keep = ch in "ybhmnD" or (ch == "#" and _r >= 18)
        line += ch if keep else "."
    BULB_ROWS.append(line)
BULB_W, BULB_H = len(BULB_ROWS[0]), len(BULB_ROWS)

LIT = {"y": BULB, "b": SHADE, "h": SHINE, "m": METAL, "n": METAL_SHINE, "D": INK, "#": OUTLINE}
UNLIT = dict(LIT, y=GLASS_OFF, b=GLASS_OFF_SHADE, h=GLASS_OFF_SHINE)
BRIGHT = dict(LIT, y=(248, 226, 160), b=(230, 186, 134), h=(255, 255, 238))

# Rayos alrededor de la bombilla suelta: pares de módulos relativos a su
# esquina (mismas direcciones que los del logo).
BULB_RAYS = [
    [(-2, -1), (-1, 0)], [(BULB_W, -1), (BULB_W - 1, 0)],
    [(BULB_W + 1, 5), (BULB_W + 2, 5)], [(BULB_W, 11), (BULB_W + 1, 12)],
    [(-1, 11), (-2, 12)], [(-3, 5), (-2, 5)],
]


def badge(floor=True):
    """Insignia circular oscura sobre la que va cada escena."""
    p = Pix()
    p.disc(24, 24, 23.5, OUTLINE)
    p.disc(24, 24, 22.5, BADGE)
    if floor:
        for y in range(34, N):
            for x in range(N):
                if p.get(x, y) == BADGE:
                    p.put(x, y, BADGE_FLOOR)
    # Puntos de luz tenues (constelación fija, no aleatoria)
    for x, y in ((12, 10), (35, 9), (8, 22), (40, 19), (29, 5), (16, 4), (42, 28), (6, 30)):
        if p.get(x, y) == BADGE:
            p.put(x, y, BADGE_DOT)
    return p


def bulb(p, x, y, palette=LIT):
    p.grid(BULB_ROWS, x, y, palette)


def glass_cells(x, y):
    return {(x + c, y + r) for r, line in enumerate(BULB_ROWS) for c, ch in enumerate(line)
            if ch in "ybh"}


def halo(p, x, y, strength=1.0):
    """Halo cálido alrededor del cristal de una bombilla encendida."""
    glass = glass_cells(x, y)
    for yy in range(p.h):
        for xx in range(p.w):
            if (xx, yy) in glass or p.get(xx, yy) not in (BADGE, BADGE_FLOOR, BADGE_DOT):
                continue
            d = min(max(abs(xx - gx), abs(yy - gy)) for gx, gy in glass)
            base = p.get(xx, yy)
            if d == 1:
                p.put(xx, yy, mix(base, WARM, 0.45 * strength))
            elif d == 2:
                p.put(xx, yy, mix(base, WARM, 0.18 * strength))


def rays(p, x, y, colors):
    for ray, col in zip(BULB_RAYS, colors):
        if col is None:
            continue
        for dx, dy in ray:
            p.put(x + dx, y + dy, col)


def logo_bubble(p, x, y, palette=PALETTE):
    p.grid(BUBBLE, x, y, palette)


def speech(p, x, y, w, h, fill, line, tail="left"):
    p.box(x, y, w, h, fill, line)
    if tail == "left":
        tx = x + 3
        p.rect(tx, y + h - 1, 3, 1, fill)
        p.grid(["#..#", "#.#.", "##.."], tx - 1, y + h - 1, {"#": line})
        p.put(tx, y + h, fill)
        p.put(tx + 1, y + h, fill)
        p.put(tx, y + h + 1, line)
    else:
        tx = x + w - 6
        p.rect(tx, y + h - 1, 3, 1, fill)
        p.grid(["#..#", ".#.#", "..##"], tx, y + h - 1, {"#": line})
        p.put(tx + 1, y + h, fill)
        p.put(tx + 2, y + h, fill)
        p.put(tx + 3, y + h + 1, line)


def sparkle(p, x, y, col):
    p.put(x, y, col)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        p.put(x + dx, y + dy, mix(col, BADGE, 0.35))


# --------------------------------------------------------------------------
# Escenas. Cada una devuelve una lista de fotogramas (Pix). El CSS del
# instalador alterna los fotogramas con animaciones de GTK.
# --------------------------------------------------------------------------
def scene_try_install():
    """Bienvenida: el logo, con los rayos encendiéndose en círculo."""
    frames = []
    for k in range(3):
        p = badge()
        logo_bubble(p, 10, 6)
        for i, ray in enumerate(pl.RAYS):
            col = HOT if i % 3 == k else (SHADE if (i - 1) % 3 == k else None)
            if col:
                for r, c in ray:
                    p.put(10 + c, 6 + r, col)
        # suelo: un pendrive de instalación conectado a la burbuja
        p.box(17, 37, 14, 6, METAL, OUTLINE, cut=False)
        p.rect(18, 38, 12, 1, METAL_SHINE)
        p.box(30, 38, 5, 4, INK, OUTLINE, cut=False)
        p.rect(31, 39, 1, 1, OFF)
        p.rect(33, 39, 1, 1, OFF)
        p.put(19, 40, BULB if k != 1 else HOT)
        frames.append(p)
    return frames


def scene_language():
    """Idioma: dos bocadillos que se turnan para hablar."""
    frames = []
    for k in range(2):
        p = badge()
        a_line = BULB if k == 0 else OUTLINE
        b_line = BULB if k == 1 else OUTLINE
        speech(p, 6, 11, 20, 11, OFF, a_line, "left")
        p.text("Hola", 9, 14, INK)
        speech(p, 23, 25, 18, 11, BULB, b_line if k == 1 else SHADE, "right")
        p.text("Hi", 27, 28, INK)
        p.text("!", 33, 28, HOT if k == 1 else INK)
        frames.append(p)
    return frames


def scene_keyboard():
    """Teclado: teclas que se iluminan."""
    lit_sets = [{(0, 1), (2, 4), (1, 7)}, {(1, 2), (0, 6), (2, 8)}, {(2, 0), (1, 5), (0, 9)}]
    frames = []
    for lit in lit_sets:
        p = badge()
        bulb(p, 18, 3)
        halo(p, 18, 3, 0.6)
        x0, y0 = 8, 22
        p.box(x0, y0, 33, 15, INK, OUTLINE)
        p.rect(x0 + 1, y0 + 1, 31, 1, mix(INK, OUTLINE, 0.5))
        for row in range(3):
            for col in range(10):
                kx, ky = x0 + 2 + col * 3, y0 + 2 + row * 3
                c = BULB if (row, col) in lit else OFF
                p.rect(kx, ky, 2, 2, c)
                p.put(kx, ky + 1, SHADE if (row, col) in lit else METAL)
                p.put(kx + 1, ky + 1, SHADE if (row, col) in lit else METAL)
        p.rect(x0 + 8, y0 + 11, 17, 2, OFF)
        p.rect(x0 + 8, y0 + 12, 17, 1, METAL)
        p.rect(x0 + 2, y0 + 11, 5, 2, METAL)
        p.rect(x0 + 26, y0 + 11, 5, 2, METAL)
        frames.append(p)
    return frames


def drive(p, x, y, led):
    p.box(x, y, 26, 8, METAL, OUTLINE)
    p.rect(x + 1, y + 1, 24, 1, METAL_SHINE)
    p.rect(x + 3, y + 4, 14, 1, OUTLINE)
    p.rect(x + 3, y + 5, 14, 1, mix(METAL, OUTLINE, 0.4))
    p.rect(x + 21, y + 4, 2, 2, led)


def scene_disks():
    p = badge()
    bulb(p, 18, 6)
    halo(p, 18, 6, 0.6)
    rays(p, 18, 6, [SHADE, SHADE, None, None, None, None])
    drive(p, 11, 25, BULB)
    drive(p, 11, 34, HOT)
    return [p]


LOCK_BODY = """
..bbbbbbbbbbbbbb..
.byyyyyyyyyyyyyyb.
byyhyyyyyyyyyyyyyb
byhyyyyyyyyyyyyyyb
byyyyyyyDDyyyyyyyb
byyyyyyDDDDyyyyyyb
byyyyyyDDDDyyyyyyb
byyyyyyyDDyyyyyyyb
byyyyyyyDDyyyyyyyb
byyyyyyyDDyyyyyyyb
byyyyyyyyyyyyyyyyb
.byyyyyyyyyyyyyyb.
..bbbbbbbbbbbbbb..
""".split()


def scene_encrypt():
    """Cifrado: el candado se cierra."""
    frames = []
    for lift in (4, 2, 0):
        p = badge()
        x0, y0 = 15, 22
        # arco del candado (metal, 2 módulos de grosor)
        sx, sy = x0 + 3, y0 - 11 - lift
        h = 12 + lift
        p.rect(sx, sy + 3, 2, h - 3, METAL)
        p.rect(sx + 10, sy + 3, 2, h - 3 - (lift if lift else 0), METAL)
        p.rect(sx + 2, sy, 8, 2, METAL)
        p.rect(sx + 1, sy + 1, 1, 2, METAL)
        p.rect(sx + 10, sy + 1, 1, 2, METAL)
        p.rect(sx + 2, sy + 2, 8, 1, METAL_SHINE)
        p.rect(sx, sy + 3, 1, h - 3, METAL_SHINE)
        p.grid(LOCK_BODY, x0, y0, {"b": SHADE, "y": BULB, "h": SHINE, "D": INK})
        if lift == 0:
            sparkle(p, x0 + 20, y0 - 3, SHINE)
            sparkle(p, x0 - 3, y0 + 2, SHINE)
        frames.append(p)
    return frames


def progress_bar(p, x, y, w, filled, col, shine):
    p.box(x, y, w, 5, BADGE, OUTLINE, cut=False)
    for i in range(filled):
        sx = x + 1 + i * 3
        if sx + 2 > x + w - 1:
            break
        p.rect(sx + 1, y + 1, 2, 3, col)
        p.put(sx + 1, y + 1, shine)


def scene_progress():
    frames = []
    for k in range(2):
        p = badge()
        bulb(p, 18, 5, BRIGHT if k else LIT)
        halo(p, 18, 5, 1.0 if k else 0.5)
        rays(p, 18, 5, [HOT, SHADE, HOT, SHADE, HOT, SHADE] if k else
             [SHADE, HOT, SHADE, HOT, SHADE, HOT])
        progress_bar(p, 9, 32, 30, 6 + k, BULB, SHINE)
        frames.append(p)
    return frames


CHECK = """
.......##
......###
#....###.
##..###..
#######..
.#####...
..###....
""".split()


def scene_success():
    frames = []
    for k in range(2):
        p = badge()
        bulb(p, 18, 8, BRIGHT)
        halo(p, 18, 8, 1.0)
        rays(p, 18, 8, [HOT] * 6)
        p.disc(34.5, 31.5, 6, SHADE)
        p.disc(34.5, 31.5, 5, BULB)
        p.grid(CHECK, 30, 28, {"#": INK})
        for (x, y), on in zip(((10, 10), (38, 8), (8, 30), (13, 38)), (k, 1 - k, 1 - k, k)):
            if on:
                sparkle(p, x, y, SHINE)
        frames.append(p)
    return frames


WARN = """
......##......
.....#yy#.....
.....#yy#.....
....#yyyy#....
....#yDDy#....
...#yyDDyy#...
...#yyDDyy#...
..#yyyDDyyy#..
..#yyyyyyyy#..
.#yyyyDDyyyy#.
.#yyyyyyyyyy#.
##############
""".split()


def scene_issue():
    frames = []
    for k in range(2):
        p = badge()
        bulb(p, 12, 9, UNLIT)
        p.grid(WARN, 26, 22, {"#": HOT if k else SHADE, "y": BULB if k else SHADE, "D": INK})
        frames.append(p)
    return frames


def scene_error():
    p = badge()
    bulb(p, 18, 9, UNLIT)
    # grieta en el cristal
    for x, y in ((22, 11), (23, 12), (22, 13), (23, 14), (24, 15), (23, 16)):
        p.put(x, y, INK)
    for x, y in ((12, 12), (35, 14), (34, 30)):
        p.put(x, y, OUTLINE)
        p.put(x + 1, y + 1, OUTLINE)
        p.put(x - 1, y + 1, OUTLINE)
        p.put(x + 1, y - 1, OUTLINE)
        p.put(x - 1, y - 1, OUTLINE)
    return [p]


def scene_account():
    """Cuenta de usuario: una silueta dentro del bocadillo del logo."""
    p = badge()
    speech(p, 12, 9, 24, 22, OFF, OUTLINE, "left")
    person = Pix()
    person.disc(24, 16.5, 4.1, INK)
    person.disc(24, 29.5, 7.5, INK)
    for y in range(10, 30):         # sólo dentro del bocadillo
        for x in range(13, 35):
            if person.get(x, y) is not None:
                p.put(x, y, INK)
    p.disc(34.5, 31.5, 5, SHADE)
    p.disc(34.5, 31.5, 4, BULB)
    p.rect(34, 29, 1, 5, INK)
    p.rect(32, 31, 5, 1, INK)
    return [p]


SCENES = {
    "try-install": scene_try_install,
    "language": scene_language,
    "keyboard": scene_keyboard,
    "disks": scene_disks,
    "encrypt": scene_encrypt,
    "progress": scene_progress,
    "success": scene_success,
    "issue": scene_issue,
    "error": scene_error,
    "create-account": scene_account,
}


# --------------------------------------------------------------------------
# SVG (logo e icono del instalador)
# --------------------------------------------------------------------------
def hexcol(c):
    return "#%02X%02X%02X" % c


def svg_from_cells(cells, w, h, title):
    """cells: {(x, y): color}. Une los módulos en tiras horizontales."""
    by_color = {}
    for y in range(h):
        x = 0
        while x < w:
            col = cells.get((x, y))
            if col is None:
                x += 1
                continue
            start = x
            while x < w and cells.get((x, y)) == col:
                x += 1
            by_color.setdefault(col, []).append("M%d %dh%dv1h-%dz" % (start, y, x - start, x - start))
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="0 0 %d %d" shape-rendering="crispEdges">' % (w * 8, h * 8, w, h),
           "  <title>%s</title>" % title]
    for col, parts in by_color.items():
        out.append('  <path fill="%s" d="%s"/>' % (hexcol(col), "".join(parts)))
    out.append("</svg>")
    return "\n".join(out) + "\n"


def logo_cells(x0=0, y0=0):
    cells = {}
    for r, line in enumerate(BUBBLE):
        for c, ch in enumerate(line):
            if ch in PALETTE:
                cells[(x0 + c, y0 + r)] = PALETTE[ch]
    return cells


def logo_svg():
    # 28 x 27 módulos: se centra en un cuadrado de 28 (medio módulo arriba no
    # se puede; se deja la fila libre abajo, donde ya acaba la cola).
    return svg_from_cells(logo_cells(), 28, 28, "XappiensOS")


ARROW = """
...##...
...##...
...##...
######..
.####...
..##....
""".split()


def installer_svg():
    """Icono del instalador: el logo con un círculo ámbar y una flecha."""
    p = Pix(32, 32)
    for (x, y), col in logo_cells().items():
        p.put(x, y, col)
    p.disc(25, 25, 7, INK)
    p.disc(25, 25, 6, BULB)
    p.grid(["...##...", "...##...", "...##...", ".######.", "..####..", "...##..."],
           21, 21, {"#": INK})
    p.rect(21, 28, 8, 1, INK)
    cells = {(x, y): p.c[y][x] for y in range(32) for x in range(32) if p.c[y][x] is not None}
    return svg_from_cells(cells, 32, 32, "Instalar XappiensOS")


def avatar():
    """Avatar de usuario por defecto (512 x 512): el logo sobre un círculo."""
    p = Pix(32, 32)
    p.disc(16, 16, 16, BADGE)
    for (x, y), col in logo_cells(2, 3).items():
        p.put(x, y, col)
    return p.render(16)


# --------------------------------------------------------------------------
# Tema de GRUB del menú de arranque de la ISO
# --------------------------------------------------------------------------
GRUB_BUBBLE_PX = 5
GRUB_TEXT_PX = 3
GRUB_GAP_PX = 26


def grub_logo():
    bw, bh = len(BUBBLE[0]) * GRUB_BUBBLE_PX, len(BUBBLE) * GRUB_BUBBLE_PX
    gap = round(pl.LETTER_GAP * GRUB_TEXT_PX)
    items, x = [], 0
    for part, color in pl.WORD:
        for ch in part:
            if items:
                x += gap
            items.append((FONT[ch], x, color))
            x += len(FONT[ch][0]) * GRUB_TEXT_PX
    tw, th = x, 12 * GRUB_TEXT_PX
    w = max(bw, tw)
    w += w % 2
    h = bh + GRUB_GAP_PX + th
    cv = Canvas(w, h)
    pl.draw_grid(cv, BUBBLE, (w - bw) // 2, 0, GRUB_BUBBLE_PX, PALETTE)
    for glyph, gx, color in items:
        pl.draw_grid(cv, glyph, (w - tw) // 2 + gx, bh + GRUB_GAP_PX, GRUB_TEXT_PX,
                     {"#": color})
    return cv


def grub_background():
    w, h = 64, 360
    cv = Canvas(w, h)
    for y in range(h):
        cv.rect(0, y, w, 1, mix(BG_TOP, BG_BOTTOM, y / (h - 1)))
    return cv


def grub_select():
    """Pastilla de la entrada seleccionada: ámbar, esquinas pixeladas (4 px)."""
    s = 4
    parts = {}
    full = Canvas(s, s)
    full.rect(0, 0, s, s, BULB)
    parts["c"] = parts["n"] = parts["s"] = parts["e"] = parts["w"] = full
    corner = [  # esquina superior izquierda; el resto son reflejos
        "..##",
        ".###",
        "####",
        "####",
    ]

    def corner_img(flip_x, flip_y):
        cv = Canvas(s, s)
        for r in range(s):
            for c in range(s):
                rr = s - 1 - r if flip_y else r
                cc = s - 1 - c if flip_x else c
                if corner[rr][cc] == "#":
                    cv.rect(c, r, 1, 1, BULB)
        return cv

    parts["nw"] = corner_img(False, False)
    parts["ne"] = corner_img(True, False)
    parts["sw"] = corner_img(False, True)
    parts["se"] = corner_img(True, True)
    return parts


GRUB_THEME_TXT = """\
# Tema de GRUB de XappiensOS (menú de arranque de la ISO).
# Generado por branding/installer/make-installer.py: no lo edites a mano.

title-text: ""
desktop-image: "background.png"
desktop-image-scale-method: "stretch"
desktop-color: "{bg}"
terminal-font: "Unifont Regular 16"
terminal-left: "0"
terminal-top: "0"
terminal-width: "100%"
terminal-height: "100%"
terminal-border: "0"

+ image {{
  left = 50%-{half_w}
  top = 46%-{logo_h}
  file = "logo.png"
}}

+ boot_menu {{
  left = 50%-220
  top = 54%
  width = 440
  height = 24%
  item_font = "Unifont Regular 16"
  item_color = "{fg}"
  selected_item_color = "{ink}"
  item_height = 32
  item_padding = 8
  item_spacing = 12
  selected_item_pixmap_style = "select_*.png"
}}

+ label {{
  top = 84%
  left = 25%
  width = 50%
  align = "center"
  id = "__timeout__"
  text = "Booting in %d seconds"
  color = "{dim}"
  font = "Unifont Regular 16"
}}
"""


# --------------------------------------------------------------------------
# Hoja de contactos para revisar el resultado (no se instala)
# --------------------------------------------------------------------------
def contact_sheet(scenes):
    cell = N * 4 + 16
    cols = max(len(f) for f in scenes.values())
    rows = len(scenes)
    w, h = cols * cell + 16, rows * cell + 16
    cv = Canvas(w, h)
    cv.rect(0, 0, w, h, (29, 26, 36))
    for r, (name, frames) in enumerate(scenes.items()):
        for c, frame in enumerate(frames):
            img = frame.render(4)
            ox, oy = 16 + c * cell, 16 + r * cell
            for y in range(img.h):
                for x in range(img.w):
                    px = img.px[y][x]
                    if px[3]:
                        cv.px[oy + y][ox + x] = px
    return cv


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(data)


def main():
    write(LOGO_SVG, logo_svg())
    write(INSTALLER_SVG, installer_svg())
    os.makedirs(os.path.dirname(AVATAR_PNG), exist_ok=True)
    avatar().save(AVATAR_PNG)

    os.makedirs(ART_DIR, exist_ok=True)
    for name in os.listdir(ART_DIR):
        if name.endswith(".png"):
            os.remove(os.path.join(ART_DIR, name))
    scenes = {}
    for name, fn in SCENES.items():
        frames = fn()
        scenes[name] = frames
        for i, frame in enumerate(frames, 1):
            frame.render().save(os.path.join(ART_DIR, "%s-%d.png" % (name, i)))
    contact_sheet(scenes).save(os.path.join(HERE, "preview.png"))

    os.makedirs(GRUB_DIR, exist_ok=True)
    logo = grub_logo()
    logo.save(os.path.join(GRUB_DIR, "logo.png"))
    grub_background().save(os.path.join(GRUB_DIR, "background.png"))
    for part, img in grub_select().items():
        img.save(os.path.join(GRUB_DIR, "select_%s.png" % part))
    write(os.path.join(GRUB_DIR, "theme.txt"), GRUB_THEME_TXT.format(
        bg=hexcol(BG_BOTTOM), fg=hexcol(OFF), ink=hexcol(BG_TOP), dim=hexcol(OUTLINE),
        half_w=logo.w // 2, logo_h=logo.h))

    n = sum(len(f) for f in scenes.values())
    print("Logo:          %s" % os.path.relpath(LOGO_SVG, REPO))
    print("Instalador:    %d ilustraciones (%d fotogramas) en %s"
          % (len(scenes), n, os.path.relpath(ART_DIR, REPO)))
    print("Menú GRUB:     %s (logo %dx%d)" % (os.path.relpath(GRUB_DIR, REPO), logo.w, logo.h))
    print("Vista previa:  %s" % os.path.relpath(os.path.join(HERE, "preview.png"), REPO))


if __name__ == "__main__":
    sys.exit(main())
