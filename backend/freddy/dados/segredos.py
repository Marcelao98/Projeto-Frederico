"""O token do bot do Discord, guardado na pasta do mestre (nunca no git).

O painel manda o token uma vez (como no Kenku FM) e ele fica em
discord.json, legível só pelo dono do arquivo. A variável de ambiente
FREDDY_DISCORD_TOKEN, se existir, ganha (e aí o painel não apaga).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from freddy.dados.playlists import gravar_json

VARIAVEL = "FREDDY_DISCORD_TOKEN"


class Segredos:
    def __init__(self, arquivo: Path):
        self.arquivo = arquivo

    @property
    def do_ambiente(self) -> bool:
        return bool(os.environ.get(VARIAVEL))

    def token(self) -> str | None:
        if self.do_ambiente:
            return os.environ[VARIAVEL].strip()
        if not self.arquivo.exists():
            return None
        return json.loads(self.arquivo.read_text(encoding="utf-8")).get("token") or None

    def guardar(self, token: str) -> None:
        gravar_json(self.arquivo, {"token": token.strip()})
        try:
            os.chmod(self.arquivo, 0o600)  # só o dono lê (no Windows não faz nada)
        except OSError:
            pass

    def esquecer(self) -> None:
        self.arquivo.unlink(missing_ok=True)
