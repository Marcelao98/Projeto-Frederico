"""python -m freddy: liga o Freddy (rodar de dentro de backend/).

    python -m freddy              toca na caixa de som deste computador
    python -m freddy --sem-som    finge que toca (pra testar o painel sem som)
"""

from __future__ import annotations

import argparse
import logging
import shutil
from pathlib import Path

from freddy import VERSAO
from freddy.config import PORTA_PADRAO, Config


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
    config = Config(porta=args.porta, sem_som=args.sem_som or args.teste)
    if args.pasta:
        config.pasta = args.pasta

    if not args.sem_som and shutil.which("ffmpeg") is None:
        logging.warning(
            "FFmpeg não encontrado: o Freddy não vai conseguir tocar. "
            "Fedora: sudo dnf install ffmpeg-free | Windows: winget install ffmpeg"
        )

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
