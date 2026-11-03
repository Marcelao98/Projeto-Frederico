"""Ponto de entrada do backend empacotado (PyInstaller) que o app liga sozinho.

O app desktop (frontend/src-tauri/src/lib.rs) roda este executável como
"sidecar" quando o Freddy não está ligado, e desliga quando fecha. Empacotado,
não tem terminal: o que o Freddy escreveria vai pro freddy.log na pasta do
mestre (~/.local/share/Freddy, %APPDATA%\\Freddy).
"""

from __future__ import annotations

import sys


def _log_em_arquivo() -> None:
    from freddy.config import pasta_padrao

    pasta = pasta_padrao()
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = open(pasta / "freddy.log", "w", encoding="utf-8", buffering=1)  # noqa: SIM115
    sys.stdout = sys.stderr = arquivo


if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        _log_em_arquivo()
    from freddy.__main__ import main

    main()
