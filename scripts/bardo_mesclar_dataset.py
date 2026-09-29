"""Etapa 3 do pipeline de dataset do Bardo: mescla um arquivo de staging
(já taggeado) em modules/bardo/dataset/musicas.json.

- Valida schema de cada entrada antes de mesclar (aborta se achar erro,
  não mescla nada pela metade).
- Nunca sobrescreve uma entrada já existente (mesmo id OU mesmo link) —
  só adiciona o que é novo. Se quiser atualizar uma faixa existente
  (corrigir tema, por exemplo), edite musicas.json direto.
- Idempotente: rodar duas vezes com o mesmo staging não duplica nada.

Uso:
    python scripts/bardo_mesclar_dataset.py staging/dark_souls.json
    python scripts/bardo_mesclar_dataset.py staging/dark_souls.json --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from bardo_dataset_utils import (  # noqa: E402
    DATASET_PADRAO,
    carregar_dataset,
    salvar_dataset,
    validar_entrada,
)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("staging", help="JSON de staging já taggeado (lista de entradas)")
    p.add_argument("--dataset", default=str(DATASET_PADRAO), help="Caminho do musicas.json")
    p.add_argument("--dry-run", action="store_true", help="Só mostra o que faria, não grava nada")
    args = p.parse_args()

    with open(args.staging, encoding="utf-8") as f:
        novas = json.load(f)
    if not isinstance(novas, list):
        print("Staging precisa ser uma lista de entradas.", file=sys.stderr)
        sys.exit(1)

    erros_por_entrada = {}
    for i, entrada in enumerate(novas):
        erros = validar_entrada(entrada)
        if erros:
            erros_por_entrada[i] = erros

    if erros_por_entrada:
        print("Staging com problemas — corrija antes de mesclar:", file=sys.stderr)
        for i, erros in erros_por_entrada.items():
            nome = novas[i].get("nome", f"item {i}")
            print(f"  [{i}] {nome!r}: {', '.join(erros)}", file=sys.stderr)
        sys.exit(1)

    caminho_dataset = Path(args.dataset)
    dados = carregar_dataset(caminho_dataset)
    existentes = dados["musicas"]
    ids_existentes = {m["id"] for m in existentes}
    links_existentes = {m["link"] for m in existentes}

    adicionadas, puladas = [], []
    for entrada in novas:
        if entrada["id"] in ids_existentes or entrada["link"] in links_existentes:
            puladas.append(entrada["nome"])
            continue
        adicionadas.append(entrada)
        ids_existentes.add(entrada["id"])
        links_existentes.add(entrada["link"])

    ainda_nao_classificadas = sum(1 for e in adicionadas if e["temas"] == ["não classificado"])

    print(f"Novas: {len(adicionadas)} | já existiam (puladas): {len(puladas)}")
    if ainda_nao_classificadas:
        print(
            f"⚠️  {ainda_nao_classificadas} entrada(s) ainda com temas=['não classificado'] "
            "— foram mescladas assim mesmo, mas idealmente tagueie antes do merge."
        )
    if puladas:
        print("Puladas por já existir:", ", ".join(puladas[:10]), "..." if len(puladas) > 10 else "")

    if args.dry_run:
        print("(--dry-run: nada foi gravado)")
        return

    if not adicionadas:
        print("Nada novo pra adicionar.")
        return

    dados["musicas"] = existentes + adicionadas
    salvar_dataset(dados, caminho_dataset)
    print(f"Gravado. Dataset agora tem {len(dados['musicas'])} faixas ({caminho_dataset}).")


if __name__ == "__main__":
    main()
