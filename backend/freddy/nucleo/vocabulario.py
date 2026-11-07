"""O vocabulário de climas: tema cru de uma faixa → as 27 categorias da busca.

Vem do acervo/vocabulario.json. As categorias de uma faixa sempre saem dos
temas dela (categorias_dos_temas), nunca à mão.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from freddy.config import PASTA_ACERVO
from freddy.nucleo.texto import normalizar

NAO_CLASSIFICADO = "não classificado"


@dataclass(frozen=True)
class Vocabulario:
    """vocabulario.json já normalizado.

    sinonimos: palavra que as pessoas digitam → categorias que ela puxa.
    por_tema: tema cru do dataset → categorias que ele dá à faixa.
    """

    sinonimos: dict[str, frozenset[str]]
    por_tema: dict[str, frozenset[str]]


_vocabulario_cache: Vocabulario | None = None


def _com_feminino(palavras: set[str]) -> set[str]:
    """Acrescenta o feminino das palavras soltas: "animado" → "animada", "assustador" → "assustadora".

    O vocabulario.json fica só no masculino; quem digita (ou marca o tema)
    "animada" ou "sombria" cai na mesma categoria.
    """
    femininos = set()
    for p in palavras:
        if " " in p:
            continue
        if p.endswith("o") and not p.endswith("ao"):
            femininos.add(p[:-1] + "a")
        elif p.endswith("or"):
            femininos.add(p + "a")
    return palavras | femininos


def montar_vocabulario(bruto: dict) -> Vocabulario:
    """Monta o Vocabulario a partir do conteúdo do vocabulario.json."""
    sinonimos: dict[str, set[str]] = {}
    por_tema: dict[str, set[str]] = {}
    for categoria, spec in bruto["categorias"].items():
        palavras = _com_feminino({normalizar(p) for p in [categoria, *spec.get("palavras", [])]})
        for p in palavras:
            sinonimos.setdefault(p, set()).add(categoria)
        # Toda palavra também conta como tema; os "temas" só puxam a faixa.
        for t in palavras | _com_feminino({normalizar(t) for t in spec.get("temas", [])}):
            por_tema.setdefault(t, set()).add(categoria)
    return Vocabulario(
        {k: frozenset(v) for k, v in sinonimos.items()},
        {k: frozenset(v) for k, v in por_tema.items()},
    )


def carregar_vocabulario() -> Vocabulario:
    """Carrega (com cache em memória) o vocabulário de categorias."""
    global _vocabulario_cache
    if _vocabulario_cache is None:
        with open(PASTA_ACERVO / "vocabulario.json", encoding="utf-8") as f:
            _vocabulario_cache = montar_vocabulario(json.load(f))
    return _vocabulario_cache


def categorias_dos_temas(temas: list[str], vocabulario: Vocabulario | None = None) -> list[str]:
    """Categorias que os temas crus de uma faixa dão a ela, em ordem alfabética."""
    vocabulario = vocabulario or carregar_vocabulario()
    categorias: set[str] = set()
    for tema in temas:
        categorias |= vocabulario.por_tema.get(normalizar(tema), frozenset())
    return sorted(categorias)
