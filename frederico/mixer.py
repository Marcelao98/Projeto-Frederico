"""Soma o microfone com a música, com ducking: a música abaixa enquanto você fala.

Funções puras sobre blocos numpy (float32, estéreo, -1..1), sem placa de som,
pra dar pra testar em qualquer lugar.
"""

from __future__ import annotations

import numpy as np

LIMIAR_VOZ = 0.02  # RMS do mic acima disso = falando (~ -34 dBFS)
GANHO_DUCKING = 0.35  # quanto sobra da música enquanto você fala
SEGUNDOS_SOLTAR = 0.6  # quanto tempo a música leva pra voltar depois que você para


def em_estereo(bloco: np.ndarray) -> np.ndarray:
    if bloco.ndim == 1:
        bloco = bloco[:, None]
    if bloco.shape[1] == 1:
        return np.repeat(bloco, 2, axis=1)
    return bloco[:, :2]


def rms(bloco: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(bloco)))) if len(bloco) else 0.0


class Ducker:
    """Ganho da música bloco a bloco: cai na hora quando a voz entra, volta devagar."""

    def __init__(self, segundos_por_bloco: float):
        self.ganho = 1.0
        self._subida = segundos_por_bloco / SEGUNDOS_SOLTAR

    def proximo(self, nivel_voz: float, ligado: bool = True) -> float:
        if ligado and nivel_voz > LIMIAR_VOZ:
            self.ganho = GANHO_DUCKING
        else:
            self.ganho = min(1.0, self.ganho + self._subida)
        return self.ganho


def misturar(musica: np.ndarray, mic: np.ndarray | None, ganho_mic: float, ganho_musica: float) -> np.ndarray:
    """musica*ganho_musica + mic*ganho_mic, com limitador suave pra soma nunca estourar."""
    saida = musica * ganho_musica
    if mic is not None:
        saida = saida + em_estereo(mic) * ganho_mic
    return limitar(saida)


def limitar(x: np.ndarray, joelho: float = 0.8) -> np.ndarray:
    """Intacto até `joelho`; acima disso curva suave até no máximo 1.0 (sem clipe seco)."""
    a = np.abs(x)
    curvado = np.sign(x) * (joelho + (1 - joelho) * np.tanh((a - joelho) / (1 - joelho)))
    return np.where(a <= joelho, x, curvado).astype(np.float32)
