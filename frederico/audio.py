"""Placa de som: lê o microfone, mistura com a música e toca na saída escolhida.

A saída principal (normalmente o VB-Cable, "CABLE Input") é o relógio: a cada
bloco de 20 ms ela pede música ao player, junta com o mic e o ducking. O
monitor (seu fone) recebe só a música, pra você não se ouvir com atraso.

O sounddevice (PortAudio) só é importado quando o motor liga: o resto do
Frederico, e os testes, rodam sem ele.
"""

from __future__ import annotations

import logging
import sys
import threading
from collections import deque

import numpy as np

from frederico import mixer
from frederico.fonte import CANAIS, TAXA

log = logging.getLogger(__name__)

QUADROS_POR_BLOCO = 960  # 20 ms
MAX_ATRASO = TAXA * 3 // 10  # 300 ms: mais que isso no buffer, joga fora o mais velho


class Buffer:
    """Fila de quadros entre duas threads de áudio com relógios diferentes."""

    def __init__(self, maximo: int = MAX_ATRASO, canais: int = CANAIS):
        self._blocos: deque[np.ndarray] = deque()
        self._total = 0
        self._maximo = maximo
        self._canais = canais
        self._trava = threading.Lock()

    def __len__(self) -> int:
        return self._total

    def colocar(self, bloco: np.ndarray) -> None:
        with self._trava:
            self._blocos.append(bloco)
            self._total += len(bloco)
            while self._total > self._maximo and self._blocos:
                self._total -= len(self._blocos.popleft())

    def tirar(self, quadros: int) -> np.ndarray:
        """Exatamente `quadros` quadros; completa com silêncio se não tem o bastante."""
        saida = np.zeros((quadros, self._canais), np.float32)
        feito = 0
        with self._trava:
            while feito < quadros and self._blocos:
                bloco = self._blocos.popleft()
                usar = min(len(bloco), quadros - feito)
                saida[feito : feito + usar] = bloco[:usar]
                if usar < len(bloco):
                    self._blocos.appendleft(bloco[usar:])
                feito += usar
                self._total -= usar
        return saida


def _sd():
    import sounddevice

    return sounddevice


def listar_dispositivos() -> dict:
    """{"entradas": [...], "saidas": [...]}, cada um {"id", "nome"}.

    No Windows só os do MME: aparecem uma vez cada (sem as cópias de
    WASAPI/DirectSound) e aceitam 48 kHz em qualquer placa (o Windows converte).
    """
    sd = _sd()
    apis = sd.query_hostapis()
    preferida = None
    if sys.platform == "win32":
        preferida = next((i for i, a in enumerate(apis) if a["name"] == "MME"), None)
    entradas, saidas = [], []
    for i, d in enumerate(sd.query_devices()):
        if preferida is not None and d["hostapi"] != preferida:
            continue
        if d["max_input_channels"] > 0:
            entradas.append({"id": i, "nome": d["name"]})
        if d["max_output_channels"] > 0:
            saidas.append({"id": i, "nome": d["name"]})
    return {"entradas": entradas, "saidas": saidas}


class Motor:
    def __init__(self, player):
        self.player = player
        self.mic_ligado = True
        self.ganho_mic = 1.0
        self.ducking = True
        # Teste: o monitor (fone) recebe o mesmo que a saída (mic + música),
        # pra ouvir o que os outros vão ouvir.
        self.ouvir_saida = False
        self.nivel_mic = 0.0
        self.nivel_saida = 0.0
        self.config: dict = {"mic": None, "saida": None, "monitor": None}
        self.erro: str | None = None
        self._streams: list = []
        self._mic = Buffer(canais=1)
        self._monitor = Buffer()
        self._ducker = mixer.Ducker(QUADROS_POR_BLOCO / TAXA)

    @property
    def ligado(self) -> bool:
        return bool(self._streams)

    def processar(self, quadros: int) -> tuple[np.ndarray, np.ndarray]:
        """Um bloco: (o que vai pra saída principal, o que vai pro monitor). Sem placa de som."""
        musica = self.player.ler(quadros)
        mic = self._mic.tirar(quadros) if self.config["mic"] is not None else None
        if mic is not None:
            self.nivel_mic = mixer.rms(mic)
        ganho = self._ducker.proximo(self.nivel_mic if mic is not None else 0.0, self.ducking)
        musica = musica * ganho
        ganho_mic = self.ganho_mic if self.mic_ligado else 0.0
        saida = mixer.misturar(musica, mic, ganho_mic, 1.0)
        self.nivel_saida = mixer.rms(saida)
        return saida, musica

    def ligar(self, saida: int, mic: int | None = None, monitor: int | None = None) -> None:
        """(Re)abre a placa de som com esses dispositivos (ids de listar_dispositivos())."""
        self.desligar()
        sd = _sd()
        self.config = {"mic": mic, "saida": saida, "monitor": monitor}
        self._mic = Buffer(canais=1)
        self._monitor = Buffer()
        comum = {"samplerate": TAXA, "blocksize": QUADROS_POR_BLOCO, "dtype": "float32", "latency": "high"}

        def ao_tocar(outdata, quadros, _tempo, status):
            if status:
                log.debug("saída: %s", status)
            principal, so_musica = self.processar(quadros)
            outdata[:] = principal
            if monitor is not None:
                self._monitor.colocar(principal if self.ouvir_saida else so_musica)

        def ao_gravar(indata, _quadros, _tempo, status):
            self._mic.colocar(indata.copy())

        def ao_monitorar(outdata, quadros, _tempo, status):
            outdata[:] = self._monitor.tirar(quadros)

        try:
            if mic is not None:
                self._streams.append(sd.InputStream(device=mic, channels=1, callback=ao_gravar, **comum))
            if monitor is not None:
                self._streams.append(sd.OutputStream(device=monitor, channels=CANAIS, callback=ao_monitorar, **comum))
            self._streams.append(sd.OutputStream(device=saida, channels=CANAIS, callback=ao_tocar, **comum))
            for s in self._streams:
                s.start()
            self.erro = None
        except Exception as e:
            log.exception("não consegui abrir a placa de som")
            self.desligar()
            self.erro = str(e)
            raise

    def desligar(self) -> None:
        for s in self._streams:
            try:
                s.stop()
                s.close()
            except Exception:
                log.exception("erro fechando stream")
        self._streams = []
