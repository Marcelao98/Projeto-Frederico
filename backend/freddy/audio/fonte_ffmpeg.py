"""Uma fonte de som: o FFmpeg decodifica um link (ou arquivo) em quadros PCM.

Uma thread lê a saída do FFmpeg e enche um buffer de alguns segundos; quem
toca (a Mesa) tira um quadro por vez, sem nunca esperar. Pular pra um ponto
da música = abrir outra fonte com `inicio` (o -ss do FFmpeg).
"""

from __future__ import annotations

import queue
import subprocess
import sys
import threading
from collections import deque

from freddy.audio.pcm import BYTES_POR_QUADRO, CANAIS, TAXA

SEGUNDOS_DE_BUFFER = 5


def comando_ffmpeg(url: str, http_headers: dict[str, str] | None = None, inicio: float = 0.0, ffmpeg: str = "ffmpeg") -> list[str]:
    cmd = [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error"]
    if url.startswith(("http://", "https://")):
        # As mesmas flags de reconexão do Bardo: um soluço de rede não derruba a música.
        cmd += ["-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5"]
        if http_headers:
            cmd += ["-headers", "".join(f"{k}: {v}\r\n" for k, v in http_headers.items())]
    if inicio > 0:
        cmd += ["-ss", f"{inicio:.2f}"]
    cmd += ["-i", url, "-vn", "-f", "s16le", "-ar", str(TAXA), "-ac", str(CANAIS), "pipe:1"]
    return cmd


class FonteFfmpeg:
    def __init__(self, url: str, http_headers: dict[str, str] | None = None, inicio: float = 0.0, ffmpeg: str = "ffmpeg"):
        self.cmd = comando_ffmpeg(url, http_headers, inicio, ffmpeg)
        self.inicio = inicio
        self._buffer: queue.Queue[bytes] = queue.Queue(maxsize=SEGUNDOS_DE_BUFFER * 50)
        self._proc: subprocess.Popen | None = None
        self._acabou = threading.Event()
        self._fechada = False
        self._erros: deque[str] = deque(maxlen=5)
        self.codigo_saida: int | None = None

    def comecar(self) -> None:
        extras = {}
        if sys.platform == "win32":
            extras["creationflags"] = subprocess.CREATE_NO_WINDOW  # sem janela preta piscando
        self._proc = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, **extras)
        threading.Thread(target=self._ler_saida, name="ffmpeg-saida", daemon=True).start()
        threading.Thread(target=self._ler_erros, name="ffmpeg-erros", daemon=True).start()

    def ler_quadro(self) -> bytes | None:
        """O próximo quadro, ou None se ainda não chegou (ou acabou)."""
        try:
            return self._buffer.get_nowait()
        except queue.Empty:
            return None

    @property
    def esgotada(self) -> bool:
        """O FFmpeg terminou e o buffer já foi todo tocado."""
        return self._acabou.is_set() and self._buffer.empty()

    @property
    def erro(self) -> str:
        return " ".join(self._erros)

    def fechar(self) -> None:
        self._fechada = True
        if self._proc and self._proc.poll() is None:
            self._proc.kill()
        # Esvazia o buffer pra destravar a thread que espera espaço nele.
        while self.ler_quadro() is not None:
            pass

    def _ler_saida(self) -> None:
        assert self._proc and self._proc.stdout
        saida = self._proc.stdout
        try:
            while not self._fechada:
                quadro = saida.read(BYTES_POR_QUADRO)
                if not quadro:
                    break
                if len(quadro) < BYTES_POR_QUADRO:
                    quadro += bytes(BYTES_POR_QUADRO - len(quadro))
                while not self._fechada:
                    try:
                        self._buffer.put(quadro, timeout=0.2)
                        break
                    except queue.Full:
                        continue
        finally:
            saida.close()
            self.codigo_saida = self._proc.wait()
            self._acabou.set()

    def _ler_erros(self) -> None:
        assert self._proc and self._proc.stderr
        with self._proc.stderr as erros:
            for linha in erros:
                texto = linha.decode("utf-8", "replace").strip()
                if texto:
                    self._erros.append(texto)
