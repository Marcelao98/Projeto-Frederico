"""O assobio do Frederico: o som de teste do Discord ("fiu-fiuuu" de calopsita).

Gerado aqui mesmo (sem arquivo, sem YouTube), então toca na hora e não
engasga: se você ouviu o assobio pela call, o caminho Freddy → Discord
funciona. Duas frases do assobio de lobo que calopsita adora imitar: uma
subidinha curta e uma subida longa que desce no fim, com o tremido do bico.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from freddy.audio.pcm import BYTES_POR_QUADRO, TAXA

VOLUME = 0.35


def _nota(duracao: float, freq_de: float, freq_meio: float, freq_ate: float, vibrato: float = 18) -> np.ndarray:
    n = int(TAXA * duracao)
    t = np.linspace(0, 1, n, endpoint=False)
    # Sobe até o meio e vai pro fim (curva suave, como assobio de verdade).
    subida = np.clip(t / 0.6, 0, 1)
    descida = np.clip((t - 0.6) / 0.4, 0, 1)
    freq = freq_de + (freq_meio - freq_de) * np.sin(subida * np.pi / 2) + (freq_ate - freq_meio) * descida**2
    freq = freq * (1 + 0.012 * np.sin(2 * np.pi * vibrato * t * duracao))
    fase = 2 * np.pi * np.cumsum(freq) / TAXA
    som = np.sin(fase) + 0.18 * np.sin(2 * fase) + 0.05 * np.sin(3 * fase)
    # Entra e sai sem estalo.
    env = np.minimum(1, np.minimum(t * duracao / 0.02, (1 - t) * duracao / 0.05))
    return som * env


def _silencio(duracao: float) -> np.ndarray:
    return np.zeros(int(TAXA * duracao))


@lru_cache(maxsize=1)
def quadros_do_assobio() -> tuple[bytes, ...]:
    """O assobio (duas vezes) em quadros de 20 ms prontos pra Mesa."""
    frase = np.concatenate(
        [
            _nota(0.22, 1700, 2900, 2900),  # fiu
            _silencio(0.12),
            _nota(0.65, 1500, 3300, 1900),  # fiuuu
        ]
    )
    mono = np.concatenate([_silencio(0.1), frase, _silencio(0.45), frase, _silencio(0.2)])
    mono = np.clip(mono / np.abs(mono).max() * VOLUME, -1, 1)
    estereo = np.repeat((mono * 32767).astype(np.int16), 2).tobytes()
    estereo += bytes(-len(estereo) % BYTES_POR_QUADRO)
    return tuple(estereo[i : i + BYTES_POR_QUADRO] for i in range(0, len(estereo), BYTES_POR_QUADRO))
