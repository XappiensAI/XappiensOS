#!/usr/bin/env python3
"""Genera el tema de Plymouth (pantalla de arranque) de XappiensOS.

Todo se dibuja a partir de rejillas de píxeles definidas en este fichero:
  - la burbuja con la bombilla del logo de Xappiens,
  - la fuente pixelada del logotipo (letras de "Xappiens" + "O" y "S"
    diseñadas con las mismas reglas: 1 módulo de trazo, 10 de alto en
    mayúsculas, 8 de altura x, esquinas recortadas).

Salida: config/xappiens-os/includes.chroot/usr/share/plymouth/themes/xappiens/
  watermark.png        logo estático (burbuja + "XappiensOS")
  throbber-NNNN.png    capa animada (2 s en bucle): la bombilla respira y los
                       rayos del logo se encienden en círculo, como indicador
                       de carga. Mismo tamaño que watermark.png para que
                       Plymouth los superponga exactamente.
  lock.png, entry.png, bullet.png, capslock.png   diálogo de contraseña (LUKS)

Sólo usa la biblioteca estándar de Python:  python3 branding/plymouth/make-theme.py
"""
import math
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(REPO, "config", "xappiens-os", "includes.chroot",
                   "usr", "share", "plymouth", "themes", "xappiens")

# --------------------------------------------------------------------------
# Paleta de la marca (extraída del logo de Xappiens)
# --------------------------------------------------------------------------
BUBBLE_FILL = (224, 237, 237)   # #E0EDED  burbuja
OUTLINE     = (115, 135, 148)   # #738794  contorno / rayos apagados
INK         = (82, 75, 98)      # #524B62  texto del logo
BULB        = (232, 201, 132)   # #E8C984  bombilla
BULB_SHADE  = (213, 165, 125)   # #D5A57D  contorno de la bombilla
BULB_SHINE  = (250, 249, 198)   # #FAF9C6  brillo
METAL       = (168, 184, 194)   # #A8B8C2  casquillo
METAL_SHINE = (199, 219, 222)   # #C7DBDE
# Colores propios de la pantalla de arranque (fondo oscuro derivado de INK)
BG_TOP      = (29, 26, 36)      # #1D1A24
BG_BOTTOM   = (18, 16, 22)      # #121016
FIELD       = (36, 33, 45)      # #24212D  campo de contraseña
WARM        = (247, 232, 182)   # halo cálido de la bombilla encendida
RAY_HOT     = (222, 150, 84)    # #DE9654  rayo recién encendido

PALETTE = {
    "o": BUBBLE_FILL, "#": OUTLINE, "D": INK, "y": BULB, "b": BULB_SHADE,
    "h": BULB_SHINE, "m": METAL, "n": METAL_SHINE,
}

# --------------------------------------------------------------------------
# Burbuja + bombilla (28 x 27 módulos), copiada píxel a píxel del logo
# --------------------------------------------------------------------------
BUBBLE = """
...........######...........
.........##oooooo##.........
.......##oooooooooo##.......
.....##oooooooooooooo##.....
....#oooooooooooooooooo#....
...#ooo#oooooooooooo#ooo#...
..#ooooo#ooobbbbooo#ooooo#..
..#oooooooobyyyyboooooooo#..
.#oooooooobyyyhhyboooooooo#.
.#ooooooobyyyyyyhybooooooo#.
#ooooooobbyyyyyyyhybooooooo#
#ooo##oobybyyyyyyhyboo##ooo#
#ooooooobbyyyyyyyyybooooooo#
#ooooooobybyyyyyyhybooooooo#
#oooooooobybyyyyyyboooooooo#
#ooooooooobybyyyybooooooooo#
.#ooooo#ooobyyyybooo#ooooo#.
.#oooo#oooobbyyyboooo#oooo#.
..#oooooooo######oooooooo#..
..#oooooooo#mnnn#oooooooo#..
...#ooooooo#mmmm#ooooooo#...
....#ooooooo####oooooooo#...
.....##ooooooDDooooooooo#...
.......##oooooooooo##oooo#..
.........##oooooo##..##oo#..
...........######......##o#.
.........................##.
""".split()

# Rayos del logo: (fila, columna) de sus dos módulos, en la rejilla BUBBLE.
RAYS = [
    [(5, 7), (6, 8)],      # arriba-izquierda
    [(5, 20), (6, 19)],    # arriba-derecha
    [(11, 22), (11, 23)],  # derecha
    [(16, 20), (17, 21)],  # abajo-derecha
    [(16, 7), (17, 6)],    # abajo-izquierda
    [(11, 4), (11, 5)],    # izquierda
]
BULB_CENTER = (11.0, 14.0)

# --------------------------------------------------------------------------
# Fuente pixelada del logotipo. 12 filas: 10 de altura de mayúsculas y 2 de
# descendente. "X a p i e n s" salen del SVG oficial del logo; "O" y "S"
# son nuevas, dibujadas con las mismas proporciones.
# --------------------------------------------------------------------------
FONT = {
    "X": ["#....#", "#....#", "#....#", ".#..#.", "..##..", ".#..#.",
          "#....#", "#....#", "#....#", "#....#", "......", "......"],
    "a": [".....", ".....", ".###.", "#...#", "....#", ".####", "#...#",
          "#...#", "#...#", ".###.", ".....", "....."],
    "p": [".....", ".....", ".###.", "#...#", "#...#", "#...#", "#...#",
          "#...#", "#...#", "####.", "#....", "#...."],
    "i": ["#", ".", "#", "#", "#", "#", "#", "#", "#", "#", ".", "."],
    "e": [".....", ".....", ".###.", "#...#", "#...#", "#####", "#....",
          "#....", "#...#", ".###.", ".....", "....."],
    "n": [".....", ".....", ".###.", "#...#", "#...#", "#...#", "#...#",
          "#...#", "#...#", "#...#", ".....", "....."],
    "s": [".....", ".....", ".###.", "#...#", "#....", ".###.", "....#",
          "....#", "#...#", ".###.", ".....", "....."],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", "#...#",
          "#...#", "#...#", ".###.", ".....", "....."],
    "S": [".###.", "#...#", "#....", "#....", ".###.", "....#", "....#",
          "....#", "#...#", ".###.", ".....", "....."],
}
# En el logo original el espacio entre letras es 2,37 módulos.
LETTER_GAP = 2.37

WORD = [("Xappiens", BUBBLE_FILL), ("OS", BULB)]

# Escalas (píxeles por módulo) y composición
BUBBLE_PX = 8          # burbuja: 224 x 216 px
TEXT_PX = 5            # texto: 50 px de altura de mayúsculas
GAP_PX = 44            # separación burbuja-texto
FRAMES = 30            # Plymouth reparte los fotogramas en 2 s

# --------------------------------------------------------------------------
# Utilidades de imagen
# --------------------------------------------------------------------------


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = [[(0, 0, 0, 0)] * w for _ in range(h)]

    def rect(self, x, y, w, h, rgb, a=255):
        for yy in range(max(0, y), min(self.h, y + h)):
            row = self.px[yy]
            for xx in range(max(0, x), min(self.w, x + w)):
                row[xx] = (rgb[0], rgb[1], rgb[2], a)

    def save(self, path):
        raw = b"".join(b"\x00" + bytes(c for p in row for c in p) for row in self.px)

        def chunk(tag, data):
            return (struct.pack(">I", len(data)) + tag + data
                    + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

        with open(path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")
            f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 6, 0, 0, 0)))
            f.write(chunk(b"IDAT", zlib.compress(raw, 9)))
            f.write(chunk(b"IEND", b""))


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw_grid(cv, grid, x0, y0, unit, palette):
    for r, line in enumerate(grid):
        for c, ch in enumerate(line):
            if ch in palette:
                cv.rect(x0 + c * unit, y0 + r * unit, unit, unit, palette[ch])


# --------------------------------------------------------------------------
# Composición
# --------------------------------------------------------------------------
bubble_w = len(BUBBLE[0]) * BUBBLE_PX
bubble_h = len(BUBBLE) * BUBBLE_PX


def text_layout():
    """Devuelve [(glifo, x_px, color)] y el ancho total del texto."""
    gap = round(LETTER_GAP * TEXT_PX)
    items, x = [], 0
    for part, color in WORD:
        for ch in part:
            if items:
                x += gap
            items.append((FONT[ch], x, color))
            x += len(FONT[ch][0]) * TEXT_PX
    return items, x


TEXT_ITEMS, text_w = text_layout()
text_h = 12 * TEXT_PX

W = max(bubble_w, text_w)
W += W % 2
H = bubble_h + GAP_PX + text_h
H += H % 2
BX = (W - bubble_w) // 2
TX = (W - text_w) // 2
TY = bubble_h + GAP_PX


def cell_rect(r, c):
    return BX + c * BUBBLE_PX, r * BUBBLE_PX


def watermark():
    cv = Canvas(W, H)
    draw_grid(cv, BUBBLE, BX, 0, BUBBLE_PX, PALETTE)
    for glyph, x, color in TEXT_ITEMS:
        draw_grid(cv, glyph, TX + x, TY, TEXT_PX, {"#": color})
    return cv


def halo_cells():
    """Módulos de la burbuja a distancia 1 y 2 del cristal de la bombilla."""
    glass = {(r, c) for r, line in enumerate(BUBBLE) for c, ch in enumerate(line)
             if ch in "ybh" and r <= 17}
    ring1, ring2 = set(), set()
    for r, line in enumerate(BUBBLE):
        for c, ch in enumerate(line):
            if ch != "o" or r > 18:
                continue
            d = min(max(abs(r - gr), abs(c - gc)) for gr, gc in glass)
            if d == 1:
                ring1.add((r, c))
            elif d == 2:
                ring2.add((r, c))
    return ring1, ring2


RING1, RING2 = halo_cells()


def quant(v, steps):
    return round(max(0.0, min(1.0, v)) * steps) / steps


def throbber_frame(i):
    t = i / FRAMES
    cv = Canvas(W, H)
    unit = BUBBLE_PX

    def paint(r, c, rgb):
        x, y = cell_rect(r, c)
        cv.rect(x, y, unit, unit, rgb)

    # 1) La bombilla "respira": brillo y halo cálido (4 niveles, pixel-art).
    p = quant(0.5 - 0.5 * math.cos(2 * math.pi * t), 3)
    if p > 0:
        for r, line in enumerate(BUBBLE):
            for c, ch in enumerate(line):
                if r > 17:
                    continue
                if ch == "y":
                    paint(r, c, mix(BULB, (248, 226, 160), p))
                elif ch == "b":
                    paint(r, c, mix(BULB_SHADE, (230, 186, 134), p))
                elif ch == "h":
                    paint(r, c, mix(BULB_SHINE, (255, 255, 238), p))
        for r, c in RING1:
            paint(r, c, mix(BUBBLE_FILL, WARM, 0.85 * p))
        for r, c in RING2:
            paint(r, c, mix(BUBBLE_FILL, WARM, 0.40 * p))
        # "OS" se ilumina a la vez que la bombilla.
        for glyph, x, color in TEXT_ITEMS:
            if color == BULB:
                draw_grid(cv, glyph, TX + x, TY, TEXT_PX,
                          {"#": mix(BULB, (250, 230, 168), p)})

    # 2) Los rayos se encienden en círculo, como un indicador de carga:
    #    un haz gira (una vuelta cada 2 s) y cada rayo se apaga poco a poco.
    beam = 2 * math.pi * t
    for ray in RAYS:
        rr = sum(r for r, _ in ray) / 2 - BULB_CENTER[0]
        cc = sum(c for _, c in ray) / 2 - BULB_CENTER[1]
        angle = math.atan2(rr, cc) + math.pi / 2  # 0 = arriba, sentido horario
        since = (beam - angle) % (2 * math.pi)
        level = 1 - since / (1.1 * math.pi)
        if level > 0.72:
            color = RAY_HOT
        elif level > 0.42:
            color = BULB_SHADE
        elif level > 0.12:
            color = BULB
        else:
            continue
        for r, c in ray:
            paint(r, c, color)
    return cv


# --------------------------------------------------------------------------
# Diálogo de contraseña (cifrado de disco), mismo estilo pixel-art
# --------------------------------------------------------------------------
UI_PX = 3

LOCK = """
...mmmmm...
..m.....m..
.m.......m.
.m.......m.
.m.......m.
.m.......m.
.bbbbbbbbb.
byyyyyyyyyb
byyyDDDyyyb
byyyyDyyyyb
byyyyDyyyyb
byyyyyyyyyb
bbbbbbbbbbb
.bbbbbbbbb.
""".split()

CAPSLOCK = """
....y....
...yyy...
..yyyyy..
.yyyyyyy.
yyyyyyyyy
..yyyyy..
..yyyyy..
..yyyyy..
.........
..yyyyy..
""".split()

BULLET = """
.yy.
yyyy
yyyy
.yy.
""".split()

UI_PALETTE = {"m": METAL, "b": BULB_SHADE, "y": BULB, "D": INK, "#": OUTLINE}


def ui_image(grid):
    cv = Canvas(len(grid[0]) * UI_PX, len(grid) * UI_PX)
    draw_grid(cv, grid, 0, 0, UI_PX, UI_PALETTE)
    return cv


def entry_image(cols=100, rows=12):
    grid = []
    for r in range(rows):
        line = ""
        for c in range(cols):
            edge_r = r in (0, rows - 1)
            edge_c = c in (0, cols - 1)
            if edge_r and edge_c:
                line += "."
            elif edge_r or edge_c:
                line += "#"
            else:
                line += "f"
        grid.append(line)
    cv = Canvas(cols * UI_PX, rows * UI_PX)
    draw_grid(cv, grid, 0, 0, UI_PX, {"#": OUTLINE, "f": FIELD})
    return cv


def composite(layers, pad_x=96, pad_y=72):
    """Simula la pantalla: degradado de fondo + capas centradas (opacas o vacías)."""
    pw, ph = W + 2 * pad_x, H + 2 * pad_y
    out = []
    for y in range(ph):
        bg = mix(BG_TOP, BG_BOTTOM, y / (ph - 1)) + (255,)
        out.append([bg] * pw)
    for cv in layers:
        for y in range(cv.h):
            row, dst = cv.px[y], out[y + pad_y]
            for x in range(cv.w):
                if row[x][3]:
                    dst[x + pad_x] = row[x]
    return pw, ph, out


def save_apng(path, frames, delay_ms):
    """APNG (PNG animado, lo muestran navegadores y GitHub) sin dependencias."""
    w, h = len(frames[0][0]), len(frames[0])

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    parts = [b"\x89PNG\r\n\x1a\n",
             chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)),
             chunk(b"acTL", struct.pack(">II", len(frames), 0))]
    seq = 0
    for i, px in enumerate(frames):
        raw = b"".join(b"\x00" + bytes(c for p in row for c in p) for row in px)
        data = zlib.compress(raw, 9)
        parts.append(chunk(b"fcTL", struct.pack(">IIIIIHHBB", seq, w, h, 0, 0,
                                                 delay_ms, 1000, 0, 0)))
        seq += 1
        if i == 0:
            parts.append(chunk(b"IDAT", data))
        else:
            parts.append(chunk(b"fdAT", struct.pack(">I", seq) + data))
            seq += 1
    parts.append(chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(b"".join(parts))


def main():
    os.makedirs(OUT, exist_ok=True)
    for name in os.listdir(OUT):
        if name.startswith("throbber-") and name.endswith(".png"):
            os.remove(os.path.join(OUT, name))

    wm = watermark()
    wm.save(os.path.join(OUT, "watermark.png"))
    preview = []
    for i in range(FRAMES):
        frame = throbber_frame(i)
        frame.save(os.path.join(OUT, "throbber-%04d.png" % (i + 1)))
        preview.append(composite([wm, frame])[2])
    # Vista previa para el README (no se instala en el sistema).
    save_apng(os.path.join(HERE, "preview.png"), preview, round(2000 / FRAMES))
    ui_image(LOCK).save(os.path.join(OUT, "lock.png"))
    ui_image(CAPSLOCK).save(os.path.join(OUT, "capslock.png"))
    ui_image(BULLET).save(os.path.join(OUT, "bullet.png"))
    entry_image().save(os.path.join(OUT, "entry.png"))

    total = sum(os.path.getsize(os.path.join(OUT, n)) for n in os.listdir(OUT))
    print("Tema generado en %s (%dx%d, %d fotogramas, %.0f KiB)"
          % (os.path.relpath(OUT, REPO), W, H, FRAMES, total / 1024))


if __name__ == "__main__":
    sys.exit(main())
