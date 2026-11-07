"""Busca booleana em português no acervo: "triste e bloodborne",
"boss fight e elden ring ou hollow knight", "calmo e fire emblem sem batalha".

"e" combina (AND), "ou" separa grupos alternativos (OR), "sem"/"não" na
frente de um termo nega ele. O "ou" tem precedência menor: "a e b ou c" é
"(a e b) ou c". Um termo bate com a faixa se aparece (sem acento) no nome,
na franquia, nos temas ou nas categorias, ou se é sinônimo de uma categoria
da faixa ("tragico" acha as da categoria "triste").

Porta fiel em TypeScript: frontend/src/navegador/busca.ts.
"""

from __future__ import annotations

import random
import re

from freddy.nucleo.texto import normalizar
from freddy.nucleo.vocabulario import Vocabulario, carregar_vocabulario

# Se a busca achar mais que isso, sorteia: algumas franquias do acervo têm
# 200+ faixas, e enfileirar tudo prenderia a mesa numa franquia por horas.
MAX_RESULTADOS_DA_BUSCA = 15

_FILLER_WORDS = {
    "musica", "musicas", "som", "sons", "faixa", "faixas", "trilha", "sonora",
    "algo", "alguma", "algum", "uma", "um", "umas", "uns",
    "de", "do", "da", "dos", "das", "a", "o", "as", "os",
    "para", "pra", "pro", "com", "no", "na", "nos", "nas", "em",
    "tipo", "bem", "muito", "mais", "clima", "cena", "hora", "estilo", "vibe",
}

_dataset_cache: list[dict] | None = None



def _texto_buscavel(musica: dict) -> str:
    partes = [
        musica["nome"], musica["origem"]["nome"], musica["origem"]["tipo"],
        *musica["temas"], *musica.get("categorias", []),
    ]
    return normalizar(" ".join(partes))


def _parse_query(texto: str) -> list[list[tuple[bool, str]]]:
    """'triste e bloodborne ou calmo sem triste' ->
    [[(F,'triste'),(F,'bloodborne')], [(F,'calmo'),(T,'triste')]]

    Formato: lista de grupos OR; cada grupo é uma lista de termos AND,
    cada termo é (negado: bool, termo: str). 'e' separa termo normal,
    'sem'/'nao' separa termo negado — ambos funcionam como ponto de corte
    dentro do grupo (não precisam vir logo no início dele).
    """
    texto = normalizar(texto)
    grupos = []
    for bruto_ou in re.split(r"\bou\b", texto):
        # captura o separador junto: ['termo0', 'e'|'sem'|'nao', 'termo1', ...]
        pedacos = re.split(r"\b(e|sem|nao)\b", bruto_ou)
        termos = []
        negado_atual = False
        for pedaco in pedacos:
            pedaco = pedaco.strip()
            if pedaco in ("e", "sem", "nao"):
                negado_atual = pedaco in ("sem", "nao")
                continue
            palavras = [p for p in pedaco.split() if p not in _FILLER_WORDS]
            termo_limpo = " ".join(palavras).strip()
            if termo_limpo:
                termos.append((negado_atual, termo_limpo))
            negado_atual = False
        if termos:
            grupos.append(termos)
    return grupos


def _contem(alvo: str, categorias: set[str], termo: str, vocabulario: Vocabulario) -> bool:
    return termo in alvo or bool(vocabulario.sinonimos.get(termo, frozenset()) & categorias)


def _termo_bate(alvo: str, categorias: set[str], negado: bool, termo: str, vocabulario: Vocabulario) -> bool:
    # Primeiro a frase inteira ("boss fight", "hollow knight"); se não bater,
    # cada palavra por si ("luta chefe" = luta e chefe).
    contido = _contem(alvo, categorias, termo, vocabulario) or (
        " " in termo and all(_contem(alvo, categorias, p, vocabulario) for p in termo.split())
    )
    return (not contido) if negado else contido


def _musica_bate(musica: dict, grupos_ou: list[list[tuple[bool, str]]], vocabulario: Vocabulario) -> bool:
    alvo = _texto_buscavel(musica)
    categorias = set(musica.get("categorias", []))
    return any(
        all(_termo_bate(alvo, categorias, negado, termo, vocabulario) for negado, termo in grupo_and)
        for grupo_and in grupos_ou
    )


def buscar_por_tags(texto_busca: str, dataset: list[dict], vocabulario: Vocabulario | None = None) -> list[dict]:
    """Busca booleana em linguagem natural no dataset de músicas.

    Retorna as entradas do dataset que batem com a query; lista vazia se
    nada bate ou se a query só tinha palavras de preenchimento.
    """
    grupos = _parse_query(texto_busca)
    if not grupos:
        return []
    vocabulario = vocabulario or carregar_vocabulario()
    return [m for m in dataset if _musica_bate(m, grupos, vocabulario)]


def sortear_da_busca(texto: str, faixas: list[dict], vocabulario: Vocabulario | None = None) -> tuple[list[dict], int]:
    """buscar_por_tags() sorteando até MAX_RESULTADOS_DA_BUSCA (pra fila). Devolve (escolhidas, total)."""
    achadas = buscar_por_tags(texto, faixas, vocabulario)
    if len(achadas) > MAX_RESULTADOS_DA_BUSCA:
        return random.sample(achadas, MAX_RESULTADOS_DA_BUSCA), len(achadas)
    return achadas, len(achadas)
