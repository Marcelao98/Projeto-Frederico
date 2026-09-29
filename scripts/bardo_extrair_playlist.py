"""Etapa 1 do pipeline de dataset do Bardo: extrai uma playlist do YouTube
em um arquivo de staging (JSON) pronto pra ser taggeado.

Não toca em modules/bardo/dataset/musicas.json — só gera um arquivo novo
pra revisão/tagueamento antes do merge (bardo_mesclar_dataset.py).

Uso:
    python scripts/bardo_extrair_playlist.py "<url da playlist>" \
        --origem-nome "Dark Souls" --origem-tipo jogo \
        --saida staging/dark_souls.json

Requer yt-dlp instalado (já é dependência do bot, ver requirements.txt).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from bardo_dataset_utils import TIPOS_ORIGEM_VALIDOS, gerar_id  # noqa: E402


def extrair_tracklist(url_playlist: str) -> list[tuple[str, str]]:
    """Roda yt-dlp --flat-playlist (sem baixar nada, só lista metadados) e
    devolve [(titulo, video_id), ...] na ordem da playlist."""
    resultado = subprocess.run(
        [
            "yt-dlp",
            "--flat-playlist",
            "--print",
            "%(title)s|||%(id)s",
            url_playlist,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    faixas = []
    for linha in resultado.stdout.splitlines():
        linha = linha.strip()
        if not linha or "|||" not in linha:
            continue
        titulo, video_id = linha.rsplit("|||", 1)
        if titulo == "NA" or video_id == "NA":
            # yt-dlp usa "NA" quando o item da playlist não é um vídeo de
            # verdade (separador de seção, vídeo removido, etc.) — pula.
            continue
        faixas.append((titulo, video_id))
    return faixas


def montar_staging(
    faixas: list[tuple[str, str]], origem_nome: str, origem_tipo: str
) -> list[dict]:
    entradas = []
    for titulo, video_id in faixas:
        entradas.append(
            {
                "id": gerar_id(origem_nome, titulo),
                "nome": titulo,
                "link": f"https://www.youtube.com/watch?v={video_id}",
                "escopo": "faixa_individual",
                "origem": {"nome": origem_nome, "tipo": origem_tipo},
                # Placeholder — a etapa 2 (tagueamento) troca isso por temas
                # reais antes do merge. Quem tagueia deve reusar o vocabulário
                # já existente no dataset (ver skill "chips" pra lista).
                "temas": ["não classificado"],
                "comentario_pessoal": "",
            }
        )
    return entradas


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("url_playlist")
    p.add_argument("--origem-nome", required=True, help='Ex: "Dark Souls"')
    p.add_argument(
        "--origem-tipo",
        required=True,
        choices=sorted(TIPOS_ORIGEM_VALIDOS),
        help="jogo, visual novel, anime ou outro",
    )
    p.add_argument(
        "--saida",
        required=True,
        help="Caminho do JSON de staging a criar (ex: staging/dark_souls.json)",
    )
    args = p.parse_args()

    print(f"Extraindo tracklist de {args.url_playlist} ...", file=sys.stderr)
    faixas = extrair_tracklist(args.url_playlist)
    if not faixas:
        print("Nenhuma faixa encontrada — playlist errada ou privada?", file=sys.stderr)
        sys.exit(1)

    entradas = montar_staging(faixas, args.origem_nome, args.origem_tipo)

    caminho_saida = Path(args.saida)
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho_saida, "w", encoding="utf-8") as f:
        json.dump(entradas, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"{len(entradas)} faixas extraídas -> {caminho_saida}", file=sys.stderr)
    print(
        "Próximo passo: tagueie 'temas' de cada entrada (troque "
        "['não classificado']) e rode bardo_mesclar_dataset.py.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
