"""O yt-dlp que se atualiza sozinho (só no app instalado).

O YouTube muda direto e o yt-dlp precisa de versão nova a cada poucas
semanas. O app leva um yt-dlp dentro, mas congelado; sem isto, um dia o
Freddy de todo mundo para de tocar até sair um app novo.

Como funciona (o mesmo caminho do `yt-dlp -U`):
- Ao ligar, se tem um yt-dlp baixado na pasta do Freddy (yt-dlp/yt-dlp.zip),
  usa ele no lugar do que veio no app. Se ele não carregar, apaga e volta
  pro que veio no app.
- Uma vez por dia, em segundo plano, olha a última versão no GitHub oficial
  do yt-dlp. Se for mais nova, baixa o arquivo e a lista de SHA-256 da mesma
  versão, confere, e troca o arquivo. Vale a partir da próxima vez que o
  Freddy ligar.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import tempfile
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

log = logging.getLogger("freddy.ytdlp")

REPOSITORIO = "https://github.com/yt-dlp/yt-dlp/releases"
NOME_DO_ARQUIVO = "yt-dlp"  # o "zipapp" do yt-dlp: um .zip com o pacote yt_dlp dentro
SOMAS = "SHA2-256SUMS"
INTERVALO = 24 * 3600  # segundos entre uma olhada e outra
PRAZO = 60  # segundos por download


def pasta_do_ytdlp(pasta_do_freddy: Path) -> Path:
    return pasta_do_freddy / "yt-dlp"


def preparar(pasta_do_freddy: Path) -> str:
    """Escolhe qual yt-dlp usar. Chamar ANTES de qualquer `import yt_dlp`. Devolve a versão."""
    arquivo = pasta_do_ytdlp(pasta_do_freddy) / "yt-dlp.zip"
    if arquivo.exists():
        sys.path.insert(0, str(arquivo))
        try:
            import yt_dlp.version

            # Arquivo que não é zip o Python ignora calado e carrega o do app:
            # confere de onde veio de verdade.
            if not str(yt_dlp.version.__file__).startswith(str(arquivo)):
                raise ImportError("o arquivo baixado não é um yt-dlp")
            log.info("yt-dlp atualizado: %s", yt_dlp.version.__version__)
            return yt_dlp.version.__version__
        except Exception as e:  # noqa: BLE001 — qualquer problema: volta pro que veio no app
            log.warning("O yt-dlp baixado não carregou (%s); uso o que veio no app.", e)
            sys.path.remove(str(arquivo))
            for nome in [m for m in sys.modules if m == "yt_dlp" or m.startswith("yt_dlp.")]:
                del sys.modules[nome]
            arquivo.unlink(missing_ok=True)
    import yt_dlp.version

    return yt_dlp.version.__version__


def atualizar_em_segundo_plano(pasta_do_freddy: Path, versao_atual: str, abrir=urllib.request.urlopen) -> threading.Thread:
    t = threading.Thread(target=atualizar, args=(pasta_do_freddy, versao_atual, abrir), name="ytdlp", daemon=True)
    t.start()
    return t


def atualizar(pasta_do_freddy: Path, versao_atual: str, abrir=urllib.request.urlopen, agora: float | None = None) -> str | None:
    """Baixa o yt-dlp novo se tiver. Devolve a versão baixada, ou None se não baixou nada."""
    pasta = pasta_do_ytdlp(pasta_do_freddy)
    controle = pasta / "controle.json"
    agora = time.time() if agora is None else agora
    try:
        anterior = json.loads(controle.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        anterior = {}
    if "olhado_em" in anterior and agora - anterior["olhado_em"] < INTERVALO:
        return None
    try:
        ultima = _ultima_versao(abrir)
        if not ultima or ultima == versao_atual or ultima == anterior.get("baixada"):
            _guardar(controle, {**anterior, "olhado_em": agora})
            return None
        base = f"{REPOSITORIO}/download/{ultima}/"
        somas = _baixar(abrir, base + SOMAS).decode("utf-8", "replace")
        esperado = next((l.split()[0] for l in somas.splitlines() if l.strip().endswith(" " + NOME_DO_ARQUIVO)), None)
        if not esperado:
            raise ValueError("a lista de SHA-256 não tem o arquivo")
        conteudo = _baixar(abrir, base + NOME_DO_ARQUIVO)
        if hashlib.sha256(conteudo).hexdigest() != esperado.lower():
            raise ValueError("SHA-256 não confere")
        _conferir_zip(conteudo)
        pasta.mkdir(parents=True, exist_ok=True)
        fd, temporario = tempfile.mkstemp(dir=pasta, suffix=".tmp")
        with os.fdopen(fd, "wb") as f:
            f.write(conteudo)
        os.replace(temporario, pasta / "yt-dlp.zip")
        _guardar(controle, {"olhado_em": agora, "baixada": ultima})
        log.info("Baixei o yt-dlp %s (vale na próxima vez que o Freddy ligar).", ultima)
        return ultima
    except Exception as e:  # noqa: BLE001 — sem internet, GitHub fora: tenta amanhã
        log.info("Não consegui atualizar o yt-dlp agora (%s).", e)
        _guardar(controle, {**anterior, "olhado_em": agora})
        return None


def _ultima_versao(abrir) -> str | None:
    """A última versão, pelo redirecionamento de /releases/latest → /releases/tag/<versão>."""
    with abrir(urllib.request.Request(f"{REPOSITORIO}/latest", method="HEAD"), timeout=PRAZO) as r:
        final = r.geturl()
    return final.rstrip("/").rsplit("/tag/", 1)[1] if "/tag/" in final else None


def _baixar(abrir, url: str) -> bytes:
    with abrir(url, timeout=PRAZO) as r:
        return r.read()


def _conferir_zip(conteudo: bytes) -> None:
    import io

    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        nomes = set(z.namelist())
        if "yt_dlp/__init__.py" not in nomes or "yt_dlp/version.py" not in nomes:
            raise ValueError("o arquivo baixado não é o yt-dlp")


def _guardar(controle: Path, dados: dict) -> None:
    try:
        controle.parent.mkdir(parents=True, exist_ok=True)
        controle.write_text(json.dumps(dados), encoding="utf-8")
    except OSError:
        pass
