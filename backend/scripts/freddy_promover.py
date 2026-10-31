"""Leva o que o mestre mudou no Freddy pro acervo oficial (o musicas.json do git).

O Freddy guarda na pasta do mestre (fora do git):
- ajustes.json: correções nas faixas do acervo (nome, temas, comentário),
  feitas pelo chat ("temas", "revisar"), pelo modo Acervo ou pela planilha;
- aprendidas.json: faixas novas ("era essa?", linha nova na planilha).

Este script aplica os dois no modules/bardo/dataset/musicas.json (as
categorias são recalculadas dos temas) e esvazia os arquivos do mestre. Depois
é revisar o git diff e commitar: os outros mestres ganham na próxima versão.

Rodar de dentro de backend/:
    python scripts/freddy_promover.py --so-mostrar   # só lista, não mexe em nada
    python scripts/freddy_promover.py                # aplica (pasta padrão do Freddy)
    python scripts/freddy_promover.py --pasta X      # outra pasta
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from freddy.config import pasta_padrao  # noqa: E402
from freddy.dados.acervo import Acervo  # noqa: E402
from freddy.dados.playlists import gravar_json  # noqa: E402
from modules.bardo import service  # noqa: E402


def promover_ajustes(acervo: Acervo, dataset_path: Path, so_mostrar: bool) -> int:
    ajustes = acervo.ajustes()
    if not ajustes:
        return 0
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    por_id = {m["id"]: m for m in dataset["musicas"]}
    for id_, campos in ajustes.items():
        faixa = por_id.get(id_)
        if faixa is None:
            print(f"? {id_} não existe mais no acervo (ignorado)")
            continue
        mudou = ", ".join(f"{k}: {faixa.get(k)!r} → {v!r}" for k, v in campos.items())
        print(f"~ {faixa['nome']}  ({mudou})")
        if not so_mostrar:
            faixa.update(campos)
            if "temas" in campos:
                faixa["categorias"] = service.categorias_dos_temas(faixa["temas"])
    if not so_mostrar:
        dataset_path.write_text(service.formatar_dataset(dataset), encoding="utf-8")
        gravar_json(acervo.arquivo_ajustes, {"faixas": {}})
    return len(ajustes)


def promover_aprendidas(acervo: Acervo, so_mostrar: bool) -> int:
    aprendidas = acervo.aprendidas()
    for faixa in aprendidas:
        temas = [t for t in faixa["temas"] if t != service.NAO_CLASSIFICADO]
        if so_mostrar:
            print(f"+ {faixa['nome']}  ({', '.join(faixa['temas'])})  {faixa['link']}")
            continue
        try:
            entrada = service.adicionar_descoberta_ao_dataset(faixa["nome"], faixa["link"], temas)
            print(f"+ {entrada['nome']}  → {entrada['id']}")
        except service.MusicaJaNoDataset as e:
            print(f"= {faixa['nome']} já estava no acervo como {e.musica['id']}")
    if aprendidas and not so_mostrar:
        gravar_json(acervo.arquivo_aprendidas, {"musicas": []})  # todas entraram (ou já estavam lá)
    return len(aprendidas)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pasta", type=Path, default=None, help="pasta do Freddy (padrão: a do sistema)")
    p.add_argument("--so-mostrar", action="store_true", help="só lista o que seria levado")
    args = p.parse_args()

    pasta = args.pasta or pasta_padrao()
    acervo = Acervo(pasta / "aprendidas.json")
    dataset_path = acervo.pasta_dataset / "musicas.json"
    ajustes = promover_ajustes(acervo, dataset_path, args.so_mostrar)
    novas = promover_aprendidas(acervo, args.so_mostrar)

    if not ajustes and not novas:
        print(f"Nada pra levar em {pasta}.")
    elif not args.so_mostrar:
        print(f"\nPronto: {ajustes} faixa(s) corrigida(s), {novas} nova(s).")
        print("Confira com: git diff modules/bardo/dataset/musicas.json")


if __name__ == "__main__":
    main()
