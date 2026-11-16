"""Enche o catálogo do Fredify: confere TODOS os blocos e põe no catálogo. Um comando só.

Roda no computador do Marcelo, ou na nuvem no ambiente "Projeto-Frederico" (que
libera o MusicBrainz e o YouTube).
De dentro de backend/ (só precisa do yt-dlp instalado):

    python scripts/catalogo_bloco.py

O que ele faz, sozinho, em ordem:
 1. Confere cada música de acervo/catalogo/blocos/bloco-NN.csv no MusicBrainz
    (ano de verdade, mbid, duração) e acha o upload oficial no YouTube (canal
    Topic, VEVO, do artista). Os dois ao mesmo tempo. Grava ao lado de cada
    bloco: bloco-NN.musicbrainz.csv e bloco-NN.youtube.csv.
 2. Põe no catálogo as que têm link oficial (as outras vão pro pendentes.csv),
    com o ano corrigido pelo MusicBrainz.
 3. Compila o catálogo e roda os pedidos de ouro.
 4. Escreve acervo/catalogo/blocos/relatorio.md e manda tudo pro GitHub
    (commit + push no main), se você não passar --sem-enviar.

Demora umas 3 horas pra 5 mil músicas (dá pra deixar rodando de noite). Pode
parar (Ctrl+C) e rodar de novo: continua de onde parou, não refaz nada.
--so-importar pula a conferência (refaz só os passos 2 a 4).
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_BACKEND))
from freddy.catalogo.bloco import (  # noqa: E402
    chave_musica, escolher_gravacao, escolher_video, escolher_video_reserva)
from freddy.catalogo.compilar import compilar  # noqa: E402
from freddy.catalogo.importar import PASTA_BLOCOS, importar, listas_de_blocos  # noqa: E402

AGENTE = "Fredify/0.6 (https://github.com/Marcelao98/Projeto-Frederico)"
CAB_MB = ["artista", "titulo", "ano_lista", "ano_mb", "confere", "mbid", "duracao", "motivo"]
CAB_YT = ["artista", "titulo", "endereco", "canal", "oficial", "duracao", "motivo"]
parar = threading.Event()
trava_print = threading.Lock()
trava_arquivo = threading.Lock()


def diga(texto: str) -> None:
    with trava_print:
        print(texto, flush=True)


def ler(caminho: Path) -> list[dict]:
    if not caminho.exists():
        return []
    with open(caminho, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def anexar(saida: Path, cabecalho: list[str], linha: list) -> None:
    novo = not saida.exists()
    with open(saida, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n")
        if novo:
            w.writerow(cabecalho)
        w.writerow(["" if v is None else v for v in linha])


def tarefas(sufixo: str) -> list[tuple[dict, Path]]:
    """(música, arquivo de saída) de tudo que ainda não foi conferido."""
    falta = []
    for lista in listas_de_blocos():
        saida = Path(f"{lista.with_suffix('')}.{sufixo}.csv")
        feitas = {chave_musica(l["artista"], l["titulo"]) for l in ler(saida)}
        falta += [(m, saida) for m in ler(lista) if chave_musica(m["artista"], m["titulo"]) not in feitas]
    return falta


def conferir_musicbrainz() -> None:
    fila = tarefas("musicbrainz")
    for i, (m, saida) in enumerate(fila, 1):
        if parar.is_set():
            return
        consulta = f'recording:"{m["titulo"]}" AND artist:"{m["artista"]}"'
        url = "https://musicbrainz.org/ws/2/recording/?" + urllib.parse.urlencode(
            {"query": consulta, "fmt": "json", "limit": 25})
        gravacoes = None
        for tentativa in range(8):  # o MusicBrainz recusa (503) quando está cheio: insiste na mesma música
            try:
                req = urllib.request.Request(url, headers={"User-Agent": AGENTE})
                with urllib.request.urlopen(req, timeout=30) as r:
                    gravacoes = json.load(r).get("recordings", [])
                break
            except Exception:
                time.sleep(1.5 + tentativa)
        if gravacoes is None:
            diga(f"  MusicBrainz: desisti de {m['artista']} - {m['titulo']} (fica pra próxima rodada)")
            continue
        g, motivo = escolher_gravacao(m["artista"], m["titulo"], gravacoes)
        ano_mb = (g.get("first-release-date") or "")[:4] if g else ""
        composicao = "ano =" in m.get("nota", "")
        confere = "sim" if composicao or ano_mb == m["ano"] else ("?" if not ano_mb else "NÃO")
        duracao = round(g["length"] / 1000) if g and g.get("length") else ""
        with trava_arquivo:
            anexar(saida, CAB_MB, [m["artista"], m["titulo"], m["ano"], ano_mb, confere,
                                   g["id"] if g else "", duracao, motivo])
        if i % 100 == 0 or i == len(fila):
            diga(f"  MusicBrainz: {i}/{len(fila)}")
        time.sleep(1.1)  # o MusicBrainz pede no máximo 1 por segundo


def _buscar_youtube(ydl, consulta: str) -> list[dict] | None:
    for tentativa in range(6):  # o YouTube recusa (403) de vez em quando: insiste
        try:
            return (ydl.extract_info(consulta, download=False) or {}).get("entries", []) or []
        except Exception:
            time.sleep(1 + tentativa)
    return None


def _fio_youtube(fila, total: int) -> None:
    import yt_dlp

    opcoes = {"quiet": True, "no_warnings": True, "extract_flat": True, "skip_download": True,
              "extractor_retries": 0, "logger": _Mudo()}
    with yt_dlp.YoutubeDL(opcoes) as ydl:
        while not parar.is_set():
            try:
                i, m, saida = fila.pop()
            except IndexError:
                return
            videos = _buscar_youtube(ydl, f"ytsearch10:{m['artista']} - {m['titulo']}")
            if videos is None:
                diga(f"  YouTube: desisti de {m['artista']} - {m['titulo']} (fica pra próxima rodada)")
                continue
            nota = m.get("nota", "").lower()
            ao_vivo = m.get("ao_vivo") == "1" or "ao vivo" in nota or "acústico" in nota
            v, motivo = escolher_video(m["artista"], m["titulo"], videos, ao_vivo)
            oficial = 1 if v else 0
            if not v:  # sem oficial: tenta de novo pedindo o áudio oficial, depois aceita o mais visto
                mais = _buscar_youtube(ydl, f"ytsearch10:{m['artista']} {m['titulo']} áudio oficial") or []
                v, motivo = escolher_video(m["artista"], m["titulo"], mais, ao_vivo)
                oficial = 1 if v else 0
                if not v:
                    v, motivo = escolher_video_reserva(m["artista"], m["titulo"], videos + mais, ao_vivo)
            with trava_arquivo:
                anexar(saida, CAB_YT, [
                    m["artista"], m["titulo"], f"https://www.youtube.com/watch?v={v['id']}" if v else "",
                    (v.get("channel") or v.get("uploader") or "") if v else "", oficial,
                    int(v["duration"]) if v and v.get("duration") else "", motivo])
            feitas = total - len(fila)
            if feitas % 100 == 0:
                diga(f"  YouTube: {feitas}/{total}")
            time.sleep(0.3)


class _Mudo:
    def debug(self, _): pass
    def warning(self, _): pass
    def error(self, _): pass


def conferir_youtube(fios: int = 3) -> None:
    tarefas_yt = tarefas("youtube")
    fila = [(i, m, saida) for i, (m, saida) in enumerate(tarefas_yt, 1)][::-1]
    total = len(fila)
    grupo = [threading.Thread(target=_fio_youtube, args=(fila, total), daemon=True) for _ in range(fios)]
    for t in grupo:
        t.start()
    for t in grupo:
        while t.is_alive():
            t.join(1)


def conferir(fios_youtube: int = 3) -> None:
    n_mb, n_yt = len(tarefas("musicbrainz")), len(tarefas("youtube"))
    if not n_mb and not n_yt:
        diga("1. Tudo já conferido.")
        return
    diga(f"1. Conferindo: {n_mb} no MusicBrainz e {n_yt} no YouTube (os dois juntos). "
         f"Uns {max(n_mb * 1.2, n_yt * 2.2) / 3600:.1f} h. Ctrl+C pra parar; rodando de novo, continua.")
    fios = [threading.Thread(target=conferir_musicbrainz, daemon=True),
            threading.Thread(target=conferir_youtube, args=(fios_youtube,), daemon=True)]
    for t in fios:
        t.start()
    try:
        while any(t.is_alive() for t in fios):
            time.sleep(1)
    except KeyboardInterrupt:
        parar.set()
        diga("\nParando... rode o mesmo comando depois que ele continua de onde parou.")
        sys.exit(130)
    faltam = len(tarefas("musicbrainz")) + len(tarefas("youtube"))
    if faltam:
        diga(f"   {faltam} conferências falharam (rede); rode de novo no fim pra completar.")


def pedidos_de_ouro() -> tuple[bool, str]:
    r = subprocess.run([sys.executable, "-m", "unittest", "freddy.catalogo.test_catalogo"],
                       cwd=RAIZ_BACKEND, capture_output=True, text=True)
    falhas = [l for l in r.stderr.splitlines()
              if l.startswith(("FAIL:", "ERROR:", "AssertionError", "AttributeError", "KeyError"))]
    return r.returncode == 0, "\n".join(falhas[:80])


def relatorio(rel, erros_compilar: list[str], ouro_ok: bool, ouro_txt: str) -> str:
    linhas = ["# Relatório da conferência dos blocos", "",
              "| Bloco | Na lista | Entraram | Pendentes |", "|---|---|---|---|"]
    tot = [0, 0, 0]
    for b, c in sorted(rel.por_bloco.items()):
        v = [c.get("na lista", 0), c.get("entrou", 0), c.get("pendente", 0)]
        tot = [a + b2 for a, b2 in zip(tot, v)]
        linhas.append(f"| {b} | {v[0]} | {v[1]} | {v[2]} |")
    linhas += [f"| **total** | {tot[0]} | {tot[1]} | {tot[2]} |", "",
               f"- Anos corrigidos pelo MusicBrainz: {len(rel.anos_corrigidos)}",
               f"- Sem resultado no MusicBrainz (ficou o ano da lista): {rel.sem_musicbrainz}",
               "- Pendentes (sem link oficial): `pendentes.csv`",
               f"- Compilação: {'OK' if not erros_compilar else f'{len(erros_compilar)} ERROS'}",
               f"- Pedidos de ouro: {'todos passam' if ouro_ok else 'há falhas (abaixo)'}", ""]
    if erros_compilar:
        linhas += ["## Erros da compilação", "", "```", *erros_compilar[:100], "```", ""]
    if not ouro_ok:
        linhas += ["## Pedidos de ouro que falharam", "", "```", ouro_txt, "```", ""]
    linhas += ["## Anos corrigidos", "", *[f"- {a}" for a in rel.anos_corrigidos], ""]
    return "\n".join(linhas)


def enviar() -> None:
    raiz = RAIZ_BACKEND.parent
    git = lambda *a: subprocess.run(["git", *a], cwd=raiz, capture_output=True, text=True)  # noqa: E731
    git("add", "acervo/catalogo")
    if git("diff", "--cached", "--quiet").returncode == 0:
        diga("4. Nada novo pra enviar.")
        return
    git("commit", "-m", "Catálogo: blocos conferidos no MusicBrainz e no YouTube")
    r = git("pull", "--rebase", "origin", "main")
    r = git("push", "origin", "HEAD:main") if r.returncode == 0 else r
    if r.returncode == 0:
        diga("4. Enviado pro GitHub (main). Avise o Claude.")
    else:
        diga(f"4. NÃO consegui enviar ({r.stderr.strip()[:200]}).\n"
             f"   O commit está feito aqui; rode depois: git push origin HEAD:main")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--so-importar", action="store_true", help="não confere nada, só importa/compila/testa")
    ap.add_argument("--sem-enviar", action="store_true", help="não faz commit nem push")
    ap.add_argument("--fios", type=int, default=3, help="buscas no YouTube ao mesmo tempo (padrão 3)")
    ap.add_argument("--so-conferir", action="store_true", help="só confere no MusicBrainz e no YouTube (não importa)")
    args = ap.parse_args()
    if not listas_de_blocos():
        diga(f"Nenhum bloco em {PASTA_BLOCOS}")
        return 1
    if not args.so_importar:
        conferir(args.fios)
    if args.so_conferir:
        return 0
    diga("2. Pondo no catálogo...")
    rel = importar()
    entraram = sum(c.get("entrou", 0) for c in rel.por_bloco.values())
    diga(f"   {entraram} entraram, {len(rel.pendentes)} pendentes, {len(rel.anos_corrigidos)} anos corrigidos")
    diga("3. Compilando e rodando os pedidos de ouro...")
    r = compilar()
    ouro_ok, ouro_txt = pedidos_de_ouro() if not r.erros else (False, "não rodou: a compilação falhou")
    (PASTA_BLOCOS / "relatorio.md").write_text(relatorio(rel, r.erros, ouro_ok, ouro_txt), encoding="utf-8")
    diga(f"   compilação {'OK' if not r.erros else 'com ERROS'}; pedidos de ouro "
         f"{'OK' if ouro_ok else 'com falhas'} (detalhes em acervo/catalogo/blocos/relatorio.md)")
    if not args.sem_enviar:
        enviar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
