"""A versão do Freddy, num comando só.

Ela aparece em 6 arquivos (o app, o instalador, o Rust, o npm e o backend).
Esquecer um deles quebra a Release ou mostra versão errada. Então:

    python3 scripts/versao.py            mostra a versão de cada arquivo
    python3 scripts/versao.py 0.5.5      muda todos pra 0.5.5
    python3 scripts/versao.py --conferir sai com erro se algum estiver diferente

O teste backend/freddy/test_versao.py roda o --conferir no GitHub, antes de
compilar.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def _json(caminho: str, chaves: list[list[str]]):
    def ler() -> list[str]:
        dados = json.loads((RAIZ / caminho).read_text(encoding="utf-8"))
        valores = []
        for c in chaves:
            v = dados
            for k in c:
                v = v[k]
            valores.append(v)
        return valores

    def escrever(nova: str) -> None:
        arquivo = RAIZ / caminho
        texto = arquivo.read_text(encoding="utf-8")
        dados = json.loads(texto)
        for c in chaves:
            alvo = dados
            for k in c[:-1]:
                alvo = alvo[k]
            alvo[c[-1]] = nova
        indent = 2
        arquivo.write_text(json.dumps(dados, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")

    return ler, escrever


def _regex(caminho: str, padrao: str):
    """`padrao` com um grupo (antes) + a versão + o resto: troca só a versão."""
    rx = re.compile(padrao, re.M)

    def ler() -> list[str]:
        m = rx.search((RAIZ / caminho).read_text(encoding="utf-8"))
        return [m.group(2)] if m else ["(não achei)"]

    def escrever(nova: str) -> None:
        arquivo = RAIZ / caminho
        texto = arquivo.read_text(encoding="utf-8")
        novo, n = rx.subn(lambda m: m.group(1) + nova + m.group(3), texto, count=1)
        if n != 1:
            raise SystemExit(f"não achei a versão em {caminho}")
        arquivo.write_text(novo, encoding="utf-8")

    return ler, escrever


ARQUIVOS = {
    "frontend/package.json": _json("frontend/package.json", [["version"]]),
    "frontend/package-lock.json": _json("frontend/package-lock.json", [["version"], ["packages", "", "version"]]),
    "frontend/src-tauri/tauri.conf.json": _json("frontend/src-tauri/tauri.conf.json", [["version"]]),
    "frontend/src-tauri/Cargo.toml": _regex("frontend/src-tauri/Cargo.toml", r'(\[package\][^\[]*?\nversion = ")([^"]+)(")'),
    "frontend/src-tauri/Cargo.lock": _regex("frontend/src-tauri/Cargo.lock", r'(name = "freddy"\nversion = ")([^"]+)(")'),
    "backend/freddy/__init__.py": _regex("backend/freddy/__init__.py", r'^(VERSAO = ")([^"]+)(")'),
}


def versoes() -> dict[str, list[str]]:
    return {nome: ler() for nome, (ler, _) in ARQUIVOS.items()}


def main(args: list[str]) -> int:
    if not args or args == ["--conferir"]:
        todas = versoes()
        unicas = {v for vs in todas.values() for v in vs}
        for nome, vs in todas.items():
            print(f"{', '.join(vs):>12}  {nome}")
        if len(unicas) == 1:
            print(f"\nTudo na {unicas.pop()} ✓")
            return 0
        print("\nVersões diferentes! Rode: python3 scripts/versao.py <versão>", file=sys.stderr)
        return 1
    nova = args[0].lstrip("v")
    if not _SEMVER.match(nova):
        print(f"versão inválida: {nova!r} (use 0.5.5)", file=sys.stderr)
        return 2
    for nome, (_, escrever) in ARQUIVOS.items():
        escrever(nova)
        print(f"{nova:>12}  {nome}")
    return main(["--conferir"])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
