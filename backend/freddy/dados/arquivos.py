"""Gravar arquivo sem corromper (a pasta do mestre)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def gravar_json(arquivo: Path, dados) -> None:
    """Grava inteiro ou nada: escreve num temporário e troca (falta de luz não corrompe)."""
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    fd, temporario = tempfile.mkstemp(dir=arquivo.parent, prefix=f".{arquivo.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(temporario, arquivo)
    except BaseException:
        Path(temporario).unlink(missing_ok=True)
        raise
