"""python -m frederico — liga o player, o motor de áudio e o painel web."""

from __future__ import annotations

import argparse
import logging
import webbrowser

from frederico.audio import Motor
from frederico.player import Player
from frederico.web import App, carregar_config, criar_servidor


def main() -> None:
    parser = argparse.ArgumentParser(description="Frederico: música por cima do seu microfone.")
    parser.add_argument("--porta", type=int, default=8765)
    parser.add_argument("--sem-navegador", action="store_true", help="não abre o painel sozinho")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    player = Player()
    motor = Motor(player)
    salvos = carregar_config().get("dispositivos")
    if salvos and salvos.get("saida") is not None:
        try:
            motor.ligar(salvos["saida"], salvos.get("mic"), salvos.get("monitor"))
            print("🎧 Som ligado com os dispositivos da última vez.")
        except Exception as e:
            print(f"⚠️  Não consegui ligar o som da última vez ({e}). Escolhe de novo no painel.")

    servidor = criar_servidor(App(player, motor), args.porta)
    url = f"http://127.0.0.1:{args.porta}"
    print(f"🦜 Frederico no ar: {url}  (Ctrl+C pra sair)")
    if not args.sem_navegador:
        webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        motor.desligar()
        player.parar()


if __name__ == "__main__":
    main()
