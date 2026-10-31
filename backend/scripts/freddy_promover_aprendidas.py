"""Leva as faixas que a mesa ensinou ("era essa?") pro acervo oficial.

O Freddy grava o que aprende em aprendidas.json, na pasta do mestre (fora
do git). Este script passa essas faixas pro modules/bardo/dataset/musicas.json
(o acervo versionado) e tira do aprendidas.json as que entraram. Depois é
revisar o diff, ajustar origem/temas se quiser, e commitar.

Rodar de dentro de backend/:
    python scripts/freddy_promover_aprendidas.py              # pasta padrão do Freddy
    python scripts/freddy_promover_aprendidas.py --pasta X    # outra pasta
    python scripts/freddy_promover_aprendidas.py --so-mostrar # não mexe em nada
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from freddy.config import pasta_padrao  # noqa: E402
from freddy.dados.acervo import Acervo  # noqa: E402
from freddy.dados.playlists import gravar_json  # noqa: E402
from modules.bardo import service  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pasta", type=Path, default=None, help="pasta do Freddy (padrão: a do sistema)")
    p.add_argument("--so-mostrar", action="store_true", help="só lista o que seria levado")
    args = p.parse_args()

    arquivo = (args.pasta or pasta_padrao()) / "aprendidas.json"
    aprendidas = Acervo(arquivo).aprendidas()
    if not aprendidas:
        print(f"Nada aprendido em {arquivo}.")
        return

    for faixa in aprendidas:
        temas = [t for t in faixa["temas"] if t != service.NAO_CLASSIFICADO]
        if args.so_mostrar:
            print(f"- {faixa['nome']}  ({', '.join(faixa['temas'])})  {faixa['link']}")
            continue
        try:
            entrada = service.adicionar_descoberta_ao_dataset(faixa["nome"], faixa["link"], temas)
            print(f"+ {entrada['nome']}  → {entrada['id']}")
        except service.MusicaJaNoDataset as e:
            print(f"= {faixa['nome']} já estava no acervo como {e.musica['id']}")

    if not args.so_mostrar:
        gravar_json(arquivo, {"musicas": []})  # todas entraram (ou já estavam lá)
        print("\nPronto. Confira com: git diff modules/bardo/dataset/musicas.json")


if __name__ == "__main__":
    main()
