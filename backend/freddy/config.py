"""Onde o Freddy escuta e onde guarda as coisas do mestre."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PORTA_PADRAO = 47824  # a do lado do painel instalado (47823)

# Quem pode falar com o servidor. Qualquer site aberto no navegador consegue
# tentar abrir ws://localhost: sem essa lista, uma página qualquer mexeria na
# fila. Só o painel (dev, preview e o app instalado) passa.
ORIGENS_PERMITIDAS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost:47823",
    "http://127.0.0.1:47823",
    "tauri://localhost",
    "http://tauri.localhost",
)


def pasta_padrao() -> Path:
    """~/.local/share/Freddy no Linux, %APPDATA%\\Freddy no Windows (ou FREDDY_PASTA)."""
    if os.environ.get("FREDDY_PASTA"):
        return Path(os.environ["FREDDY_PASTA"])
    from platformdirs import user_data_dir

    return Path(user_data_dir("Freddy", appauthor=False, roaming=True))


def pasta_de_downloads() -> Path:
    """Onde a planilha do acervo é salva: a pasta Downloads da pessoa."""
    from platformdirs import user_downloads_dir

    return Path(user_downloads_dir())


@dataclass
class Config:
    pasta: Path = field(default_factory=pasta_padrao)
    host: str = "127.0.0.1"
    porta: int = PORTA_PADRAO
    origens: tuple[str, ...] = ORIGENS_PERMITIDAS
    sem_som: bool = False
    pasta_downloads: Path = field(default_factory=pasta_de_downloads)

    @property
    def arquivo_playlists(self) -> Path:
        return self.pasta / "playlists.json"

    @property
    def arquivo_aprendidas(self) -> Path:
        return self.pasta / "aprendidas.json"
