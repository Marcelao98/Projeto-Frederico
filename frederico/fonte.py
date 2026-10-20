"""Decodifica qualquer coisa que o FFmpeg abre (URL do YouTube, arquivo local)
em PCM 48 kHz estéreo, o formato que o motor mistura e que o Discord usa.

Uma thread lê o pipe do FFmpeg e enche um buffer; quem toca (o callback de
áudio) só pega o que já está pronto, sem nunca esperar rede ou disco.
"""

from __future__ import annotations

import shlex
import subprocess
import threading
from collections import deque

import numpy as np

TAXA = 48000
CANAIS = 2
BYTES_POR_QUADRO = 2 * CANAIS  # s16le
BLOCO_LEITURA = 960  # quadros (20 ms) por leitura do pipe
MAX_BLOCOS_NO_BUFFER = 100  # ~2 s adiantados


def comando_ffmpeg(origem: str, opcoes: dict[str, str] | None = None) -> list[str]:
    """Linha de comando do FFmpeg que solta PCM cru no stdout.

    `opcoes` é o dict de service.opcoes_ffmpeg() (reconexão + headers), que só
    vale pra URL: num arquivo local o FFmpeg recusa as opções de HTTP.
    """
    antes = shlex.split(opcoes["before_options"]) if opcoes else []
    depois = [o for o in shlex.split(opcoes["options"])] if opcoes else ["-vn"]
    return [
        "ffmpeg", "-nostdin", "-loglevel", "error", *antes, "-i", origem, *depois,
        "-f", "s16le", "-ar", str(TAXA), "-ac", str(CANAIS), "pipe:1",
    ]


class FonteFFmpeg:
    def __init__(self, comando: list[str]):
        self._proc = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self._blocos: deque[np.ndarray] = deque()
        self._sobra: np.ndarray | None = None
        self._cheio = threading.Condition()
        self._acabou_leitura = False
        self._fechada = False
        threading.Thread(target=self._ler_pipe, daemon=True).start()

    def _ler_pipe(self) -> None:
        tamanho = BLOCO_LEITURA * BYTES_POR_QUADRO
        try:
            while not self._fechada:
                dados = self._proc.stdout.read(tamanho)
                if not dados:
                    break
                dados = dados[: len(dados) - len(dados) % BYTES_POR_QUADRO]
                bloco = np.frombuffer(dados, dtype=np.int16).reshape(-1, CANAIS).astype(np.float32) / 32768
                with self._cheio:
                    while len(self._blocos) >= MAX_BLOCOS_NO_BUFFER and not self._fechada:
                        self._cheio.wait(0.1)
                    self._blocos.append(bloco)
        finally:
            self._acabou_leitura = True

    @property
    def terminou(self) -> bool:
        """Acabou de verdade: o FFmpeg fechou o pipe e tudo que ele soltou já foi tocado."""
        return self._acabou_leitura and not self._blocos and self._sobra is None

    def ler(self, quadros: int) -> np.ndarray:
        """Até `quadros` quadros já decodificados (pode vir menos, ou vazio se ainda está carregando)."""
        partes, faltam = [], quadros
        while faltam > 0:
            if self._sobra is not None:
                bloco, self._sobra = self._sobra, None
            else:
                try:
                    bloco = self._blocos.popleft()
                except IndexError:
                    break
            if len(bloco) > faltam:
                bloco, self._sobra = bloco[:faltam], bloco[faltam:]
            partes.append(bloco)
            faltam -= len(bloco)
        if partes:
            with self._cheio:
                self._cheio.notify()
        return np.concatenate(partes) if partes else np.zeros((0, CANAIS), np.float32)

    def fechar(self) -> None:
        self._fechada = True
        with self._cheio:
            self._cheio.notify_all()
        if self._proc.poll() is None:
            self._proc.kill()
        self._proc.wait()
