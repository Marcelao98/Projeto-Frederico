"""Etapa 3 do banco: confere um bloco de músicas no MusicBrainz e acha o link oficial no YouTube.

Roda no computador do Marcelo (a nuvem não alcança o MusicBrainz nem o
YouTube). De dentro de backend/, com o requirements.txt instalado:

    python scripts/catalogo_bloco.py ../acervo/catalogo/blocos/bloco-01.csv

Faz as duas coisas (ou só uma: --so musicbrainz / --so youtube) e grava, do
lado do bloco:
    bloco-01.musicbrainz.csv  ano conferido, mbid, duração
    bloco-01.youtube.csv      o link oficial escolhido e por quê
Pode parar no meio (Ctrl+C) e rodar de novo: continua de onde parou.
O MusicBrainz pede no máximo 1 pedido por segundo; 500 músicas ≈ 9 minutos.
O YouTube leva uns 20–30 minutos pra 500.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from freddy.catalogo.bloco import escolher_gravacao, escolher_video  # noqa: E402

AGENTE = "Fredify/0.6 (https://github.com/Marcelao98/Projeto-Frederico)"


def ler_bloco(caminho: Path) -> list[dict]:
    with open(caminho, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def ja_feitas(saida: Path) -> set[tuple[str, str]]:
    if not saida.exists():
        return set()
    with open(saida, encoding="utf-8") as f:
        return {(l["artista"], l["titulo"]) for l in csv.DictReader(f, delimiter=";")}


def anexar(saida: Path, cabecalho: list[str], linha: list) -> None:
    novo = not saida.exists()
    with open(saida, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n")
        if novo:
            w.writerow(cabecalho)
        w.writerow(["" if v is None else v for v in linha])


def musicbrainz(bloco: list[dict], saida: Path) -> None:
    feitas = ja_feitas(saida)
    cab = ["artista", "titulo", "ano_lista", "ano_mb", "confere", "mbid", "duracao", "motivo"]
    for i, m in enumerate(bloco, 1):
        if (m["artista"], m["titulo"]) in feitas:
            continue
        consulta = f'recording:"{m["titulo"]}" AND artist:"{m["artista"]}"'
        url = "https://musicbrainz.org/ws/2/recording/?" + urllib.parse.urlencode(
            {"query": consulta, "fmt": "json", "limit": 25})
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENTE})
            with urllib.request.urlopen(req, timeout=30) as r:
                gravacoes = json.load(r).get("recordings", [])
        except Exception as e:  # rede caiu ou o MusicBrainz recusou: anota e segue
            print(f"[{i}] erro no MusicBrainz ({e}); rode de novo depois pra completar")
            time.sleep(5)
            continue
        g, motivo = escolher_gravacao(m["artista"], m["titulo"], gravacoes)
        ano_mb = (g.get("first-release-date") or "")[:4] if g else ""
        composicao = "ano =" in m.get("nota", "")  # clássica: o ano da lista é o da composição
        confere = "sim" if composicao or ano_mb == m["ano"] else ("?" if not ano_mb else "NÃO")
        duracao = round(g["length"] / 1000) if g and g.get("length") else ""
        anexar(saida, cab, [m["artista"], m["titulo"], m["ano"], ano_mb, confere,
                            g["id"] if g else "", duracao, motivo])
        print(f"[{i}/{len(bloco)}] {m['artista']} - {m['titulo']}: {ano_mb or '?'} ({confere})")
        time.sleep(1.1)


def youtube(bloco: list[dict], saida: Path) -> None:
    import yt_dlp

    feitas = ja_feitas(saida)
    cab = ["artista", "titulo", "endereco", "canal", "oficial", "duracao", "motivo"]
    opcoes = {"quiet": True, "extract_flat": True, "skip_download": True, "noprogress": True}
    with yt_dlp.YoutubeDL(opcoes) as ydl:
        for i, m in enumerate(bloco, 1):
            if (m["artista"], m["titulo"]) in feitas:
                continue
            busca = f"ytsearch10:{m['artista']} - {m['titulo']}"
            try:
                videos = ydl.extract_info(busca, download=False).get("entries", [])
            except Exception as e:  # YouTube recusou ou caiu: anota e segue
                print(f"[{i}] erro no YouTube ({e}); rode de novo depois pra completar")
                time.sleep(10)
                continue
            ao_vivo = "ao vivo" in m.get("nota", "").lower() or "acústico" in m.get("nota", "").lower()
            v, motivo = escolher_video(m["artista"], m["titulo"], videos, ao_vivo)
            linha = [m["artista"], m["titulo"], f"https://www.youtube.com/watch?v={v['id']}" if v else "",
                     (v.get("channel") or v.get("uploader") or "") if v else "", 1 if v else 0,
                     int(v["duration"]) if v and v.get("duration") else "", motivo]
            anexar(saida, cab, linha)
            print(f"[{i}/{len(bloco)}] {m['artista']} - {m['titulo']}: {motivo}")
            time.sleep(1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("bloco", type=Path)
    ap.add_argument("--so", choices=["musicbrainz", "youtube"])
    args = ap.parse_args()
    bloco = ler_bloco(args.bloco)
    base = args.bloco.with_suffix("")
    if args.so in (None, "musicbrainz"):
        musicbrainz(bloco, Path(f"{base}.musicbrainz.csv"))
    if args.so in (None, "youtube"):
        youtube(bloco, Path(f"{base}.youtube.csv"))
    print("Pronto. Faça o commit dos arquivos .musicbrainz.csv e .youtube.csv (ou mande pro Claude).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
