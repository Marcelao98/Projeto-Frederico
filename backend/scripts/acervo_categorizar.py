"""Preenche o campo 'categorias' de cada faixa do acervo (acervo/musicas.json).

As categorias saem dos temas crus da faixa, segundo
acervo/vocabulario.json. Categorias que já estão na faixa
são mantidas (dá pra acrescentar à mão, ex: "taverna" numa faixa que o
vocabulário não pegou); pra tirar uma, apaga à mão no musicas.json.

Rodar de novo sempre que mexer no vocabulário ou acrescentar faixas.
Uso (de dentro de backend/): python scripts/acervo_categorizar.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from freddy.dados.acervo_oficial import CAMINHO, formatar  # noqa: E402
from freddy.nucleo.vocabulario import carregar_vocabulario, categorias_dos_temas  # noqa: E402


def main() -> None:
    dataset = json.loads(CAMINHO.read_text(encoding="utf-8"))
    vocabulario = carregar_vocabulario()
    sem_categoria = []
    for m in dataset["musicas"]:
        m["categorias"] = sorted(set(m.get("categorias", [])) | set(categorias_dos_temas(m["temas"], vocabulario)))
        if not m["categorias"]:
            sem_categoria.append(m["nome"])
    CAMINHO.write_text(formatar(dataset), encoding="utf-8")

    print(f"{len(dataset['musicas'])} faixas categorizadas; {len(sem_categoria)} sem nenhuma categoria.")
    for nome in sem_categoria:
        print(f"  - {nome}")


if __name__ == "__main__":
    main()
