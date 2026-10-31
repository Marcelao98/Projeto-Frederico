"""Recorta a ave de uma arte gerada (fundo escuro ou xadrez "falso") e salva PNG transparente.

O Gemini costuma desenhar o xadrez de transparência dentro da imagem e salvar
em JPG. Este script tira esse fundo escuro, joga fora o que estiver solto
(ex.: notinha musical), suaviza a borda e centraliza num quadrado 1024x1024.
Precisa de Pillow e numpy. De dentro de frontend/:

    python scripts/recortar_ave.py arte.jpg public/aves/lutino.png

Depois, o rosto (pros tamanhos pequenos) é um recorte quadrado da cabeça,
salvo como public/aves/<tema>-rosto.png.
"""
import sys
from collections import deque
import numpy as np
from PIL import Image

entrada, saida = sys.argv[1], sys.argv[2]
rgb = np.array(Image.open(entrada).convert("RGB")).astype(np.float32)
h, w, _ = rgb.shape
mx = rgb.max(axis=2)

ESCURO = 60  # fundo tem canal máximo <= ~43

# 1) fundo = pixels escuros ligados à borda (o olho preto fica de fora: está cercado de branco)
fundo = np.zeros((h, w), bool)
fila = deque()
for x in range(w):
    for y in (0, h - 1):
        if mx[y, x] <= ESCURO and not fundo[y, x]:
            fundo[y, x] = True; fila.append((y, x))
for y in range(h):
    for x in (0, w - 1):
        if mx[y, x] <= ESCURO and not fundo[y, x]:
            fundo[y, x] = True; fila.append((y, x))
while fila:
    y, x = fila.popleft()
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ny, nx = y + dy, x + dx
        if 0 <= ny < h and 0 <= nx < w and not fundo[ny, nx] and mx[ny, nx] <= ESCURO:
            fundo[ny, nx] = True; fila.append((ny, nx))

# 2) só o maior pedaço que não é fundo (a ave); tira a nota musical solta
objeto = ~fundo
rotulo = np.zeros((h, w), np.int32); atual = 0; tamanhos = {}
for y0 in range(h):
    for x0 in range(w):
        if objeto[y0, x0] and not rotulo[y0, x0]:
            atual += 1; rotulo[y0, x0] = atual; fila.append((y0, x0)); n = 0
            while fila:
                y, x = fila.popleft(); n += 1
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and objeto[ny, nx] and not rotulo[ny, nx]:
                            rotulo[ny, nx] = atual; fila.append((ny, nx))
            tamanhos[atual] = n
maior = max(tamanhos, key=tamanhos.get)
print("pedaços:", sorted(tamanhos.values(), reverse=True)[:5])
ave = rotulo == maior

# 3) borda suave: perto do fundo, a transparência vem do brilho (o JPEG mistura com o preto)
def dilatar(m, r):
    out = m.copy()
    for _ in range(r):
        n = out.copy()
        n[1:] |= out[:-1]; n[:-1] |= out[1:]; n[:, 1:] |= out[:, :-1]; n[:, :-1] |= out[:, 1:]
        out = n
    return out
borda = ave & dilatar(~ave, 3)
alfa = ave.astype(np.float32)
rampa = np.clip((mx - ESCURO) / (150 - ESCURO), 0, 1)
alfa[borda] = rampa[borda]
# tira o "preto" misturado na borda (fundo era ~preto): cor = cor / alfa
cor = rgb.copy()
m = borda & (alfa > 0)
cor[m] = np.clip(rgb[m] / alfa[m][:, None], 0, 255)

rgba = np.dstack([cor, alfa * 255]).astype(np.uint8)
img = Image.fromarray(rgba, "RGBA")

# 4) enquadra: corta no contorno da ave e centraliza num quadrado com margem
caixa = img.getbbox()
img = img.crop(caixa)
lado = int(max(img.size) * 1.06)
quadro = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
quadro.paste(img, ((lado - img.width) // 2, (lado - img.height) // 2), img)
quadro.resize((1024, 1024), Image.LANCZOS).save(saida, optimize=True)
print("salvo", saida, "caixa original", caixa)
