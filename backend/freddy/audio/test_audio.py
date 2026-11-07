"""O caminho do som de verdade (FFmpeg → Mesa → saída), com um arquivo gerado na hora.

Sem internet e sem caixa de som: o "link" é um .wav de tom puro, e a
SaidaMuda puxa os quadros 20x mais rápido que o normal.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

import numpy as np

from freddy.audio.mesa import Mesa, aplicar_ganho
from freddy.audio.pcm import BYTES_POR_QUADRO, SILENCIO
from freddy.audio.reprodutor_mesa import ReprodutorMesa
from freddy.audio.saidas.muda import SaidaMuda
from freddy.audio.fontes.youtube import Fonte, motivo_em_portugues

TEM_FFMPEG = shutil.which("ffmpeg") is not None


def gerar_tom(pasta: Path, segundos: float) -> Path:
    arquivo = pasta / f"tom-{segundos}.wav"
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=frequency=440:duration={segundos}", str(arquivo)],
        check=True,
    )
    return arquivo


class Ouvinte:
    def __init__(self):
        self.avisos: list[tuple] = []
        self.chegou = threading.Event()

    def _anotar(self, *aviso):
        self.avisos.append(aviso)
        self.chegou.set()

    def tocando(self):
        self._anotar("tocando")

    def pausado(self):
        self._anotar("pausado")

    def fim(self):
        self._anotar("fim")

    def erro(self, motivo):
        self._anotar("erro", motivo)

    def titulo(self, titulo):
        self._anotar("titulo", titulo)

    def esperar(self, nome: str, prazo: float = 10.0) -> tuple:
        limite = time.monotonic() + prazo
        while time.monotonic() < limite:
            for a in self.avisos:
                if a[0] == nome:
                    return a
            self.chegou.wait(0.05)
            self.chegou.clear()
        raise AssertionError(f"não chegou '{nome}': {self.avisos}")


class TestMesa(unittest.TestCase):
    def test_sem_fonte_e_silencio(self):
        self.assertEqual(Mesa().ler(), SILENCIO)

    def test_le_sempre_o_tamanho_pedido(self):
        self.assertEqual(len(Mesa().ler(1000)), 1000)

    def test_ganho(self):
        quadro = np.full(BYTES_POR_QUADRO // 2, 10000, dtype=np.int16).tobytes()
        metade = np.frombuffer(aplicar_ganho(quadro, 0.5), dtype=np.int16)
        self.assertEqual(int(metade[0]), 5000)
        self.assertEqual(aplicar_ganho(quadro, 1.0), quadro)
        self.assertEqual(aplicar_ganho(quadro, 0.0), SILENCIO)


class TestMotivos(unittest.TestCase):
    def test_erros_do_youtube_em_portugues(self):
        self.assertEqual(motivo_em_portugues("ERROR: [youtube] abc: Private video. Sign in"), "o vídeo é privado")
        self.assertIn("idade", motivo_em_portugues("Sign in to confirm your age"))
        self.assertEqual(motivo_em_portugues("qualquer coisa"), "não consegui abrir o vídeo")


@unittest.skipUnless(TEM_FFMPEG, "precisa do ffmpeg")
class TestReprodutorMesa(unittest.TestCase):
    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.pasta, True)
        self.ouvinte = Ouvinte()

    def novo(self, duracao_declarada: float | None = None) -> ReprodutorMesa:
        def resolver(link: str) -> Fonte:
            if link == "quebrado":
                raise RuntimeError("ERROR: Video unavailable")
            caminho = Path(link)
            return Fonte(f"Tom {caminho.stem}", str(caminho), duracao_declarada or 0.0, {})

        def abrir(mesa):
            saida = SaidaMuda(mesa, velocidade=20)
            saida.comecar()
            return saida

        r = ReprodutorMesa(abrir, resolver=resolver)
        r.ouvir(self.ouvinte)
        self.addCleanup(r.fechar)
        return r

    def test_toca_ate_o_fim(self):
        r = self.novo()
        r.carregar(str(gerar_tom(self.pasta, 2)))
        self.assertEqual(self.ouvinte.esperar("titulo"), ("titulo", "Tom tom-2"))
        self.ouvinte.esperar("tocando")
        self.ouvinte.esperar("fim")
        self.assertNotIn("erro", [a[0] for a in self.ouvinte.avisos])
        self.assertAlmostEqual(r.posicao(), 2.0, delta=0.1)

    def test_link_quebrado_vira_erro_em_portugues(self):
        r = self.novo()
        r.carregar("quebrado")
        self.assertEqual(self.ouvinte.esperar("erro"), ("erro", "o vídeo não existe mais (ou foi removido)"))

    def test_acabar_cedo_demais_e_falha(self):
        # O YouTube disse 3 minutos e só veio 1 segundo: o áudio foi recusado.
        r = self.novo(duracao_declarada=180)
        r.carregar(str(gerar_tom(self.pasta, 1)))
        self.assertEqual(self.ouvinte.esperar("erro")[0], "erro")

    def test_pausa_segura_o_relogio(self):
        r = self.novo()
        r.carregar(str(gerar_tom(self.pasta, 30)))
        self.ouvinte.esperar("tocando")
        r.pausar()
        time.sleep(0.1)
        antes = r.posicao()
        time.sleep(0.3)
        self.assertEqual(r.posicao(), antes)
        r.tocar()
        time.sleep(0.3)
        self.assertGreater(r.posicao(), antes)

    def test_buscar_pula_pro_ponto(self):
        r = self.novo(duracao_declarada=30)
        r.carregar(str(gerar_tom(self.pasta, 30)))
        self.ouvinte.esperar("tocando")
        r.buscar(20)
        self.assertGreaterEqual(r.posicao(), 20)
        self.ouvinte.esperar("fim", prazo=15)
        self.assertNotIn("erro", [a[0] for a in self.ouvinte.avisos])

    def test_parar_cala_e_ignora_avisos_velhos(self):
        r = self.novo()
        r.carregar(str(gerar_tom(self.pasta, 1)))
        r.parar()
        time.sleep(1)
        self.assertEqual([a for a in self.ouvinte.avisos if a[0] in ("fim", "tocando")], [])
        self.assertEqual(r.mesa.ler(), SILENCIO)


if __name__ == "__main__":
    unittest.main()
