"""Funções compartilhadas entre os scripts do pipeline de dataset do Bardo
(extração de playlist e merge no musicas.json). Fica em scripts/ porque é
ferramenta de manutenção do dataset, não parte do bot em produção — não é
importado por service.py/cog.py.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

DATASET_PADRAO = (
    Path(__file__).parent.parent / "modules" / "bardo" / "dataset" / "musicas.json"
)

TIPOS_ORIGEM_VALIDOS = {"jogo", "visual novel", "anime", "outro"}
ESCOPOS_VALIDOS = {"faixa_individual", "album_completo"}


def slugify(texto: str) -> str:
    """'Ornstein and Smough' -> 'ornstein-and-smough'. Mesmo esquema já
    usado nos ids existentes do dataset (origem-slug + '-' + nome-slug)."""
    texto = unicodedata.normalize("NFD", texto.lower().strip())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    return texto.strip("-")


def gerar_id(origem_nome: str, nome_faixa: str) -> str:
    return f"{slugify(origem_nome)}-{slugify(nome_faixa)}"[:80].rstrip("-")


def carregar_dataset(caminho: Path = DATASET_PADRAO) -> dict:
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def salvar_dataset(dados: dict, caminho: Path = DATASET_PADRAO) -> None:
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
        f.write("\n")


def validar_entrada(entrada: dict) -> list[str]:
    """Retorna lista de erros (vazia = ok). Não lança exceção — quem chama
    decide se aborta ou só avisa."""
    erros = []
    for campo in ("id", "nome", "link", "escopo", "origem", "temas"):
        if campo not in entrada:
            erros.append(f"falta campo '{campo}'")
    if erros:
        return erros

    if entrada["escopo"] not in ESCOPOS_VALIDOS:
        erros.append(f"escopo inválido: {entrada['escopo']!r}")
    if not isinstance(entrada["origem"], dict) or "nome" not in entrada["origem"] or "tipo" not in entrada["origem"]:
        erros.append("origem precisa ser {'nome': ..., 'tipo': ...}")
    elif entrada["origem"]["tipo"] not in TIPOS_ORIGEM_VALIDOS:
        erros.append(f"origem.tipo inválido: {entrada['origem']['tipo']!r} (use um de {sorted(TIPOS_ORIGEM_VALIDOS)})")
    if not isinstance(entrada["temas"], list) or not entrada["temas"]:
        erros.append("temas precisa ser uma lista não-vazia (use ['não classificado'] se não souber)")
    if "youtube.com" not in entrada["link"] and "youtu.be" not in entrada["link"]:
        erros.append(f"link não parece ser do YouTube: {entrada['link']!r}")
    return erros
