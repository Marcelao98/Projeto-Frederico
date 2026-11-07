"""A caixa de som deste computador (PortAudio, via sounddevice; no Fedora vai
pro PipeWire, no Windows pro WASAPI/MME). Sem placa de som, cai na SaidaMuda.
"""

from __future__ import annotations

import logging

from freddy.audio.mesa import Mesa
from freddy.audio.pcm import AMOSTRAS_POR_QUADRO, BYTES_POR_AMOSTRA, CANAIS, TAXA
from freddy.audio.saidas import Saida
from freddy.audio.saidas.muda import SaidaMuda

log = logging.getLogger("freddy.audio")


class SaidaLocal:
    nome = "local"

    def __init__(self, mesa: Mesa, dispositivo: int | str | None = None):
        self.mesa = mesa
        self.dispositivo = dispositivo
        self._stream = None

    def comecar(self) -> None:
        # Importa só aqui: sem PortAudio instalado, o resto do Freddy ainda sobe.
        import sounddevice as sd

        def pedir(saida, quadros, _tempo, status):
            if status.output_underflow:
                log.debug("a caixa de som ficou sem som por um instante")
            saida[:] = self.mesa.ler_para_local(quadros * CANAIS * BYTES_POR_AMOSTRA)

        self._stream = sd.RawOutputStream(
            samplerate=TAXA,
            channels=CANAIS,
            dtype="int16",
            blocksize=AMOSTRAS_POR_QUADRO,
            latency="high",  # folga contra engasgo; o atraso não importa pra música
            device=self.dispositivo,
            callback=pedir,
        )
        self._stream.start()

    def fechar(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None


def abrir_saida_local(mesa: Mesa) -> Saida:
    """A caixa de som; se não der (sem PortAudio, sem placa), avisa e segue mudo."""
    saida = SaidaLocal(mesa)
    try:
        saida.comecar()
        return saida
    except Exception as e:  # noqa: BLE001 — qualquer falha aqui vira "sem som", não queda
        log.warning("Não consegui abrir a caixa de som (%s). Sigo sem som.", e)
        muda = SaidaMuda(mesa)
        muda.comecar()
        return muda
