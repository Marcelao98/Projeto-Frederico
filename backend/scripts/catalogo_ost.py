"""Trilhas instrumentais no catálogo do Fredify: um comando por passo. De dentro de backend/.

Guia: docs/etapas/catalogo-ost.md. Precisa do yt-dlp (já vem no requirements).

    python scripts/catalogo_ost.py status                  o que falta (obra por obra e o total)
    python scripts/catalogo_ost.py extrair [ids...]        acha a playlist e tira as faixas reais
    python scripts/catalogo_ost.py mostrar <id>            as faixas da obra, enxutas, pra classificar
    python scripts/catalogo_ost.py marcar <id> <arquivo> [--resto-fora]
                                                   grava a classificação compacta ('-' = stdin)
    python scripts/catalogo_ost.py importar                põe tudo no catálogo, compila e testa
    python scripts/catalogo_ost.py links [--todas]         confere se os vídeos ainda estão no ar

Extrair não gasta token: o nome e o link vêm da playlist do YouTube. Pode parar
e rodar de novo: só faz o que falta.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

RAIZ_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_BACKEND))
from freddy.catalogo import ost  # noqa: E402
from freddy.catalogo.compilar import PASTA_CATALOGO, compilar  # noqa: E402

FILTRO_PLAYLIST = "&sp=EgIQAw%3D%3D"  # a busca do YouTube só com playlists


class _Mudo:
    def debug(self, _): pass
    def warning(self, _): pass
    def error(self, _): pass


def _ydl(fim: int | None = None):
    import yt_dlp

    op = {"quiet": True, "no_warnings": True, "extract_flat": True, "skip_download": True,
          "extractor_retries": 0, "logger": _Mudo()}
    if fim:
        op["playlistend"] = fim
    return yt_dlp.YoutubeDL(op)


def _pedir(ydl, url: str, tentativas: int = 8):
    """O YouTube recusa (403) de vez em quando: insiste um pouco."""
    for i in range(tentativas):
        try:
            return ydl.extract_info(url, download=False)
        except Exception:  # noqa: BLE001
            time.sleep(1 + i)
    return None


def _candidatas(obra: dict) -> list[str]:
    if obra.get("playlist"):
        return [obra["playlist"]]
    if obra["tipo"] == "álbum":  # artista ou estilo (música épica, taverna): busca pelo nome
        termos = [obra["nome"], f"{obra['nome']} playlist"]
    else:
        termos = [f"{obra['nome']} original soundtrack", f"{obra['nome']} OST"]
        termos += [f"{a} soundtrack" for a in obra["_proprios"][1:3] if len(a) >= 5]
    urls = []
    with _ydl(fim=12) as ydl:
        for t in termos:
            r = _pedir(ydl, "https://www.youtube.com/results?search_query=" + urllib.parse.quote(t) + FILTRO_PLAYLIST)
            for e in (r or {}).get("entries") or []:
                if e.get("id") and e["id"] not in urls and ost.nota_da_playlist(
                        obra, e.get("title") or "", 1, e.get("channel") or e.get("uploader") or ""):
                    urls.append(e["id"])
    return [f"https://www.youtube.com/playlist?list={i}" for i in urls[:5]]


def extrair(ids: list[str]) -> None:
    todas = ost.obras()
    alvo = [o for o in todas if (o["id"] in ids if ids else not ost.faixas_de(o["id"]))]
    for o in todas:
        o["_proprios"] = ost.nomes_proprios(o, todas)
    print(f"Extraindo {len(alvo)} obra(s).")
    for o in alvo:
        melhor, nota, faixas = None, 0, []
        for url in _candidatas(o):
            with _ydl() as ydl:
                pl = _pedir(ydl, url)
            if not pl:
                continue
            validas = ost.faixas_validas(o, list(pl.get("entries") or []))
            canal = pl.get("channel") or pl.get("uploader") or ""
            n = ost.nota_da_playlist(o, pl.get("title") or "", len(validas), canal) if not o.get("playlist") else len(validas)
            if n > nota:
                melhor, nota, faixas = url, n, validas
        if not faixas:
            print(f"  {o['id']}: NÃO achei playlist (ponha o link na coluna playlist do obras.csv)")
            continue
        ost.gravar(ost.PASTA_FAIXAS / f"{o['id']}.csv", ost.COLUNAS_FAIXA, faixas)
        if not o.get("playlist"):
            o["playlist"] = melhor
        print(f"  {o['id']}: {len(faixas)} faixas  ({melhor})")
        ost.gravar(ost.PASTA_OST / "obras.csv", ost.COLUNAS_OBRA, todas)


def mostrar(obra_id: str) -> None:
    o = next((x for x in ost.obras() if x["id"] == obra_id), None)
    if not o:
        sys.exit(f"obra {obra_id!r} não está no obras.csv")
    faixas = ost.faixas_de(obra_id)
    print(f"# {o['nome']} ({o['tipo']}, {o['ano']}; {o['compositor']}) meta {o['meta']} | {len(faixas)} faixas")
    print(f"# marque assim: {ost.MARCA}")
    for f in faixas:
        feita = "*" if f.get("climas") or f.get("fora") == "1" else " "
        dur = f"{int(f['duracao']) // 60}:{int(f['duracao']) % 60:02d}" if f["duracao"] else "?"
        print(f"{feita}{f['ordem']}|{f['titulo']}|{dur}")


def marcar(obra_id: str, arquivo: str, resto_fora: bool = False) -> None:
    faixas = ost.faixas_de(obra_id)
    if not faixas:
        sys.exit(f"{obra_id}: extraia antes")
    linhas = sys.stdin.read().splitlines() if arquivo == "-" else Path(arquivo).read_text("utf-8").splitlines()
    n, erros = ost.aplicar_marcas(faixas, linhas)
    if resto_fora:  # escolheu as boas: o resto da playlist (repetida, vinheta, excesso) fica de fora
        for f in faixas:
            if not f.get("climas") and f.get("fora") != "1":
                f["fora"] = "1"
    tags = {x["id"]: x["gaveta"] for x in ost.ler(PASTA_CATALOGO / "tags.csv")}
    erros += ost.conferir_faixas(faixas, tags)
    ost.gravar(ost.PASTA_FAIXAS / f"{obra_id}.csv", ost.COLUNAS_FAIXA, faixas)
    o = next((x for x in ost.obras() if x["id"] == obra_id), {})
    print(f"{obra_id}: {n} marcadas; {ost.situacao(o, faixas)}; {len(erros)} erro(s)")
    for e in erros[:30]:
        print("  ERRO", e)


def status() -> None:
    legado = sum(1 for m in ost.ler(PASTA_CATALOGO / "musicas.csv") if m["lote"] == "rpg-legado")
    total, por_grupo = 0, {}
    print(f"{'obra':40} {'faixas':>6} {'boas':>5} situação")
    for o in ost.obras():
        f = ost.faixas_de(o["id"])
        boas = sum(1 for x in f if x.get("climas") and x.get("fora") != "1")
        total += boas
        g = por_grupo.setdefault(o.get("grupo") or "?", [0, 0])
        g[0], g[1] = g[0] + 1, g[1] + boas
        print(f"{o['id'][:40]:40} {len(f):6} {boas:5} {ost.situacao(o, f)}")
    print("\npor grupo: " + ", ".join(f"{k} {v[1]} ({v[0]} obras)" for k, v in sorted(por_grupo.items())))
    print(f"Instrumentais: {total} classificadas + {legado} do RPG antigo = {total + legado} (meta 5000)")


def _viva(link: str) -> bool | None:
    """True no ar, False fora (removido/privado), None = não deu pra saber agora."""
    url = "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(link, safe="")
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Fredify"}), timeout=20) as r:
                json.load(r)
                return True
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 404):  # removido, privado ou sem incorporação
                return False
            # 403/429: o YouTube segurando a gente; tenta de novo
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1 + i)
    return None


def links(todas: bool) -> None:
    """Confere as fontes do catálogo (e das faixas de OST) e marca viva=0 nas que caíram."""
    caminho = PASTA_CATALOGO / "fontes.csv"
    fontes = ost.ler(caminho)
    hoje = date.today().isoformat()
    fila = [f for f in fontes if f["tipo"].startswith("youtube") and (todas or not f["conferida_em"])]
    print(f"Conferindo {len(fila)} links (8 por vez)...")
    caidas = 0
    with ThreadPoolExecutor(8) as ex:
        for i, (f, ok) in enumerate(zip(fila, ex.map(lambda f: _viva(f["endereco"]), fila)), 1):
            if ok is None:
                continue
            f["viva"], f["conferida_em"] = ("1" if ok else "0"), hoje
            caidas += not ok
            if i % 500 == 0:
                print(f"  {i}/{len(fila)} ({caidas} fora do ar)")
                ost.gravar(caminho, list(fontes[0].keys()), fontes)
    ost.gravar(caminho, list(fontes[0].keys()), fontes)
    print(f"Pronto: {caidas} fora do ar (viva=0). Elas saem da busca até ganhar outro link.")


def importar() -> int:
    rel = ost.importar(PASTA_CATALOGO)
    print(f"{rel.entraram} faixas entraram de {rel.obras} obras ({rel.fora} fora, "
          f"{rel.repetidas_do_legado} já estavam no RPG antigo, {rel.sem_classificar} sem classificar)")
    for e in rel.erros[:30]:
        print("  ERRO", e)
    r = compilar()
    print("compilação", "OK" if not r.erros else f"com {len(r.erros)} ERROS: {r.erros[:5]}")
    t = subprocess.run([sys.executable, "-m", "unittest", "freddy.catalogo.test_catalogo"], cwd=RAIZ_BACKEND,
                       capture_output=True, text=True)
    print("pedidos de ouro", "OK" if t.returncode == 0 else "com falhas:\n" + t.stderr[-2500:])
    return 0 if not r.erros and t.returncode == 0 and not rel.erros else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    p = sub.add_parser("extrair"); p.add_argument("ids", nargs="*")  # noqa: E702
    p = sub.add_parser("mostrar"); p.add_argument("id")  # noqa: E702
    p = sub.add_parser("marcar"); p.add_argument("id"); p.add_argument("arquivo")  # noqa: E702
    p.add_argument("--resto-fora", action="store_true", help="o que não foi marcado fica de fora")
    sub.add_parser("importar")
    p = sub.add_parser("links"); p.add_argument("--todas", action="store_true")  # noqa: E702
    a = ap.parse_args()
    if a.cmd == "status":
        status()
    elif a.cmd == "extrair":
        extrair(a.ids)
    elif a.cmd == "mostrar":
        mostrar(a.id)
    elif a.cmd == "marcar":
        marcar(a.id, a.arquivo, a.resto_fora)
    elif a.cmd == "importar":
        return importar()
    elif a.cmd == "links":
        links(a.todas)
    return 0


if __name__ == "__main__":
    sys.exit(main())
