"""python -m freddy: liga o Freddy (rodar de dentro de backend/).

    python -m freddy              toca na caixa de som deste computador
    python -m freddy --sem-som    finge que toca (pra testar o painel sem som)
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path

from freddy import VERSAO
from freddy.config import PORTA_PADRAO, Config


def vigiar_o_app(pid: int) -> None:
    """Ligado pelo app (FREDDY_PAI): se o app fechar ou cair, o Freddy desliga junto."""
    import os
    import threading
    import time

    def vivo() -> bool:
        if sys.platform == "win32":
            import ctypes

            k = ctypes.windll.kernel32  # type: ignore[attr-defined]
            h = k.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return False
            codigo = ctypes.c_ulong()
            k.GetExitCodeProcess(h, ctypes.byref(codigo))
            k.CloseHandle(h)
            return codigo.value == 259  # STILL_ACTIVE
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True

    def vigiar():
        while vivo():
            time.sleep(2)
        logging.info("O app fechou: desligando o Freddy.")
        os._exit(0)

    threading.Thread(target=vigiar, name="vigia-do-app", daemon=True).start()


def main() -> None:
    p = argparse.ArgumentParser(prog="python -m freddy", description="O som da mesa de RPG.")
    p.add_argument("--porta", type=int, default=PORTA_PADRAO)
    p.add_argument("--sem-som", action="store_true", help="finge que toca: não usa yt-dlp, FFmpeg nem caixa de som")
    p.add_argument("--pasta", type=Path, help="onde guardar playlists e faixas aprendidas")
    # Pros testes de ponta a ponta (contrato.remoto.test.ts): o reprodutor não
    # toca nem finge tocar, como o ReprodutorFalso dos testes do motor.
    p.add_argument("--teste", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("-v", "--detalhes", action="store_true", help="mostra mais coisa no terminal")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.detalhes else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    import os

    if os.environ.get("FREDDY_PAI", "").isdigit():
        vigiar_o_app(int(os.environ["FREDDY_PAI"]))
    config = Config(porta=args.porta, sem_som=args.sem_som or args.teste)
    if args.pasta:
        config.pasta = args.pasta

    if not args.sem_som and shutil.which("ffmpeg") is None:
        logging.warning(
            "FFmpeg não encontrado: o Freddy não vai conseguir tocar. "
            "Fedora: sudo dnf install ffmpeg-free | Windows: winget install ffmpeg"
        )

    # No app instalado, o yt-dlp mais novo que já foi baixado (e procura outro
    # em segundo plano). Tem que ser antes de qualquer import do yt_dlp.
    if getattr(sys, "frozen", False) and not args.teste:
        from freddy.audio.fontes import ytdlp

        ytdlp.atualizar_em_segundo_plano(config.pasta, ytdlp.preparar(config.pasta))

    import uvicorn

    from freddy.api.app import criar_app

    print(f"\n  🐦 Freddy {VERSAO} ligado em http://{config.host}:{config.porta}")
    print(f"     guardando as coisas em {config.pasta}")
    print("     abra o painel (app ou npm run dev); Ctrl+C desliga.\n")
    criar = {}
    if args.teste:
        from freddy.audio.reprodutor_falso import ReprodutorFalso

        criar["criar"] = lambda _config, loop: ReprodutorFalso(agendar=loop.call_soon_threadsafe)
    uvicorn.run(criar_app(config, **criar), host=config.host, port=config.porta, log_level="warning")


if __name__ == "__main__":
    main()
