"""python -m frederico.diagnostico [link] — confere, no PC de quem roda, cada peça do Frederico.

Testa Python, ffmpeg, yt-dlp (resolvendo um link de verdade), placa de som
(lista tudo, procura o VB-Cable) e grava 3 s do microfone padrão medindo o
volume. Imprime o erro inteiro de cada peça que falhar.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
import traceback

LINK_PADRAO = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo", o 1º vídeo do YouTube


def secao(titulo: str) -> None:
    print(f"\n=== {titulo} ===")


def main() -> None:
    link = sys.argv[1] if len(sys.argv) > 1 else LINK_PADRAO

    secao("Python")
    print(sys.version, "|", platform.platform())

    secao("ffmpeg")
    ffmpeg = shutil.which("ffmpeg")
    print("achado em:", ffmpeg)
    if ffmpeg:
        print(subprocess.run([ffmpeg, "-version"], capture_output=True, text=True).stdout.splitlines()[0])

    secao("yt-dlp")
    try:
        import yt_dlp

        print("versão:", yt_dlp.version.__version__)
        print("deno (runtime JS que o yt-dlp novo usa pro YouTube):", shutil.which("deno") or "NÃO ACHEI")
        from frederico import youtube

        print("resolvendo", link, "...")
        info = youtube.resolver_stream(link)
        print("OK:", info["titulo"])
    except Exception:
        print("FALHOU:")
        traceback.print_exc()

    secao("Placa de som")
    try:
        import sounddevice as sd

        apis = sd.query_hostapis()
        cable = False
        for i, d in enumerate(sd.query_devices()):
            tipo = ("entrada " if d["max_input_channels"] else "") + ("saída" if d["max_output_channels"] else "")
            print(f"[{i}] {d['name']} | {apis[d['hostapi']]['name']} | {tipo}")
            cable = cable or "CABLE" in d["name"].upper()
        print("VB-Cable:", "achado" if cable else "NÃO ACHEI (instala e reinicia o PC)")
        print("padrão (entrada, saída):", sd.default.device)
    except Exception:
        print("FALHOU:")
        traceback.print_exc()
        return

    secao("Microfone padrão (fale durante 3 segundos)")
    try:
        import numpy as np

        gravado = sd.rec(int(3 * 48000), samplerate=48000, channels=1, dtype="float32")
        sd.wait()
        pico = float(np.abs(gravado).max())
        print(f"pico: {pico:.4f}", "-> OK, o mic chega" if pico > 0.01 else "-> SILÊNCIO: confere a privacidade do microfone no Windows")
    except Exception:
        print("FALHOU:")
        traceback.print_exc()


if __name__ == "__main__":
    main()
