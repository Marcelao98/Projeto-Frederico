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


def _certificados_de_dentro() -> None:
    """HTTPS (Discord) com os certificados que vão no pacote.

    O Python empacotado procura os certificados onde o sistema que compilou
    guarda (Ubuntu: /usr/lib/ssl); no Fedora e no Windows não tem nada lá, e
    o bot não conecta ("não alcancei o Discord").
    """
    import os
    import ssl

    import certifi

    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    # E direto no ssl (o aiohttp do discord.py usa create_default_context()):
    # assim não depende do OpenSSL empacotado respeitar a variável.
    original = ssl.create_default_context

    def com_certifi(purpose=ssl.Purpose.SERVER_AUTH, *, cafile=None, capath=None, cadata=None):
        if cafile is None and capath is None and cadata is None:
            cafile = certifi.where()
        return original(purpose, cafile=cafile, capath=capath, cadata=cadata)

    ssl.create_default_context = com_certifi


if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        _log_em_arquivo()
        _certificados_de_dentro()
    from freddy.__main__ import main

    main()
