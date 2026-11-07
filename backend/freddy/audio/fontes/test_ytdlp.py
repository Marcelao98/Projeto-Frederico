"""O yt-dlp que se atualiza sozinho: escolher o baixado, conferir o SHA-256, voltar se quebrar.

Sem internet: o "yt-dlp do GitHub" é um zip montado aqui com o yt_dlp
instalado (com a versão trocada pra dar pra saber qual carregou).
"""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import yt_dlp

from freddy.audio.fontes import ytdlp

BACKEND = Path(__file__).resolve().parents[3]
VERSAO_FALSA = "2099.01.01"


def zip_do_ytdlp(versao: str = VERSAO_FALSA) -> bytes:
    """Um zipapp do yt-dlp (como o do GitHub: com #! na frente), a partir do instalado."""
    origem = Path(yt_dlp.__file__).parent
    memoria = io.BytesIO()
    memoria.write(b"#!/usr/bin/env python3\n")
    with zipfile.ZipFile(memoria, "a") as z:
        for arq in origem.rglob("*.py"):
            nome = "yt_dlp/" + arq.relative_to(origem).as_posix()
            texto = arq.read_text(encoding="utf-8")
            if nome == "yt_dlp/version.py":
                texto += f"\n__version__ = {versao!r}\n"
            z.writestr(nome, texto)
    return memoria.getvalue()


def versao_que_carrega(pasta: Path) -> str:
    """Roda preparar() num Python separado (o import do yt_dlp não "desfaz")."""
    codigo = f"from pathlib import Path; from freddy.audio.fontes import ytdlp; print(ytdlp.preparar(Path({str(pasta)!r})))"
    r = subprocess.run([sys.executable, "-c", codigo], cwd=BACKEND, capture_output=True, text=True, check=True)
    return r.stdout.strip().splitlines()[-1]


class Resposta:
    def __init__(self, url: str, corpo: bytes = b""):
        self.url, self.corpo = url, corpo

    def geturl(self):
        return self.url

    def read(self):
        return self.corpo

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class GithubFalso:
    def __init__(self, ultima: str, conteudo: bytes, soma: str | None = None):
        self.ultima, self.conteudo = ultima, conteudo
        self.soma = soma or hashlib.sha256(conteudo).hexdigest()
        self.pedidos: list[str] = []

    def __call__(self, pedido, timeout=None):
        url = pedido if isinstance(pedido, str) else pedido.full_url
        self.pedidos.append(url)
        if url.endswith("/latest"):
            return Resposta(f"{ytdlp.REPOSITORIO}/tag/{self.ultima}")
        if url.endswith("/" + ytdlp.SOMAS):
            return Resposta(url, f"{self.soma}  yt-dlp\nabc123  yt-dlp.exe\n".encode())
        if url.endswith("/yt-dlp"):
            return Resposta(url, self.conteudo)
        raise OSError(f"não esperava {url}")


class Base(unittest.TestCase):
    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.pasta, True)


class TestPreparar(Base):
    def test_sem_nada_baixado_usa_o_que_veio(self):
        self.assertEqual(versao_que_carrega(self.pasta), yt_dlp.version.__version__)

    def test_usa_o_baixado(self):
        (self.pasta / "yt-dlp").mkdir()
        (self.pasta / "yt-dlp" / "yt-dlp.zip").write_bytes(zip_do_ytdlp())
        self.assertEqual(versao_que_carrega(self.pasta), VERSAO_FALSA)

    def test_baixado_quebrado_volta_pro_que_veio_e_apaga(self):
        (self.pasta / "yt-dlp").mkdir()
        arquivo = self.pasta / "yt-dlp" / "yt-dlp.zip"
        arquivo.write_bytes(b"isso nao e um zip")
        self.assertEqual(versao_que_carrega(self.pasta), yt_dlp.version.__version__)
        self.assertFalse(arquivo.exists())


class TestAtualizar(Base):
    def test_baixa_confere_e_troca(self):
        github = GithubFalso("2099.01.01", zip_do_ytdlp())
        self.assertEqual(ytdlp.atualizar(self.pasta, "2025.01.01", abrir=github, agora=1000), "2099.01.01")
        self.assertTrue((self.pasta / "yt-dlp" / "yt-dlp.zip").exists())
        self.assertTrue(all(u.startswith(ytdlp.REPOSITORIO) for u in github.pedidos))
        self.assertEqual(versao_que_carrega(self.pasta), VERSAO_FALSA)

    def test_sha_errado_nao_troca(self):
        github = GithubFalso("2099.01.01", zip_do_ytdlp(), soma="0" * 64)
        self.assertIsNone(ytdlp.atualizar(self.pasta, "2025.01.01", abrir=github, agora=1000))
        self.assertFalse((self.pasta / "yt-dlp" / "yt-dlp.zip").exists())

    def test_arquivo_que_nao_e_o_ytdlp_nao_troca(self):
        falso = io.BytesIO()
        with zipfile.ZipFile(falso, "w") as z:
            z.writestr("outra_coisa/__init__.py", "")
        self.assertIsNone(ytdlp.atualizar(self.pasta, "2025.01.01", abrir=GithubFalso("2099.01.01", falso.getvalue()), agora=1000))

    def test_mesma_versao_nao_baixa(self):
        github = GithubFalso("2025.01.01", b"")
        self.assertIsNone(ytdlp.atualizar(self.pasta, "2025.01.01", abrir=github, agora=1000))
        self.assertEqual(len(github.pedidos), 1)

    def test_uma_olhada_por_dia(self):
        github = GithubFalso("2025.01.01", b"")
        ytdlp.atualizar(self.pasta, "2025.01.01", abrir=github, agora=1000)
        ytdlp.atualizar(self.pasta, "2025.01.01", abrir=github, agora=1000 + 3600)
        self.assertEqual(len(github.pedidos), 1)
        ytdlp.atualizar(self.pasta, "2025.01.01", abrir=github, agora=1000 + 25 * 3600)
        self.assertEqual(len(github.pedidos), 2)

    def test_sem_internet_nao_quebra(self):
        def sem_internet(*_a, **_k):
            raise OSError("sem rede")

        self.assertIsNone(ytdlp.atualizar(self.pasta, "2025.01.01", abrir=sem_internet, agora=1000))
        controle = json.loads((self.pasta / "yt-dlp" / "controle.json").read_text())
        self.assertEqual(controle["olhado_em"], 1000)


if __name__ == "__main__":
    unittest.main()
