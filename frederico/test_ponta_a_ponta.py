"""Ponta a ponta sem placa de som: ffmpeg de verdade decodificando um arquivo,
player tocando, motor mixando com um "mic" e o painel web respondendo.
"""

import json
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

from frederico.audio import Motor
from frederico.fonte import TAXA
from frederico.player import Player
from frederico.web import App, criar_servidor


@unittest.skipUnless(shutil.which("ffmpeg"), "precisa do ffmpeg")
class TestArquivoDeVerdade(unittest.TestCase):
    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.pasta)
        self.arquivos = []
        for nome, freq in (("um", 440), ("dois", 660)):
            caminho = self.pasta / f"{nome}.mp3"
            subprocess.run(
                ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=frequency={freq}:duration=0.5", str(caminho)],
                check=True,
            )
            self.arquivos.append(str(caminho))

    def ler_tudo(self, player, segundos):
        blocos = []
        fim = time.monotonic() + 5
        while sum(map(len, blocos)) < TAXA * segundos and time.monotonic() < fim:
            bloco = player.ler(960)
            if np.abs(bloco).max() > 0:
                blocos.append(bloco)
            else:
                time.sleep(0.005)  # o ffmpeg ainda está carregando
        return np.concatenate(blocos) if blocos else np.zeros((0, 2))

    def test_toca_um_arquivo_e_passa_pro_proximo(self):
        player = Player()
        self.assertIn("Tocando um", player.tocar(self.arquivos[0]))
        self.assertIn("Na fila", player.tocar(self.arquivos[1]))
        player.mudar_volume(100)
        primeiro = self.ler_tudo(player, 0.4)
        self.assertGreater(len(primeiro), TAXA * 0.3)
        self.assertGreater(float(np.abs(primeiro).max()), 0.05)
        # Termina o primeiro (o arquivo é curto: o player tenta de novo uma vez, como no YouTube).
        fim = time.monotonic() + 5
        while player.estado()["tocando"] != "dois" and time.monotonic() < fim:
            player.ler(960)
            time.sleep(0.001)
        self.assertEqual(player.estado()["tocando"], "dois")
        player.parar()

    def test_motor_soma_mic_com_musica(self):
        player = Player()
        player.mudar_volume(100)
        player.tocar(self.arquivos[0])
        motor = Motor(player)
        motor.config = {"mic": 1, "saida": 2, "monitor": None}
        motor.ducking = False
        time.sleep(0.3)
        motor._mic.colocar(np.full((960, 1), 0.1, np.float32))
        saida, musica = motor.processar(960)
        self.assertGreater(float(np.abs(musica).max()), 0.05)
        np.testing.assert_allclose(saida, np.clip(musica + 0.1, -1, 1), atol=0.2)
        player.parar()


class MotorFalso:
    ligado, config, erro, mic_ligado, ganho_mic, ducking, nivel_mic, nivel_saida, ouvir_saida = (
        False, {"mic": None, "saida": None, "monitor": None}, None, True, 1.0, True, 0.0, 0.0, False)

    def ligar(self, saida, mic=None, monitor=None):
        self.config = {"mic": mic, "saida": saida, "monitor": monitor}
        self.ligado = True

    def desligar(self):
        self.ligado = False


class TestPainel(unittest.TestCase):
    def setUp(self):
        self.player = Player(abrir=lambda m, info: None)
        self.servidor = criar_servidor(App(self.player, MotorFalso()), porta=0)
        self.porta = self.servidor.server_address[1]
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        self.addCleanup(self.servidor.server_close)
        self.addCleanup(self.servidor.shutdown)

    def pedir(self, rota, dados=None, host=None):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.porta}{rota}",
            data=None if dados is None else json.dumps(dados).encode(),
            headers={"Content-Type": "application/json", **({"Host": host} if host else {})},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read()) if "json" in r.headers["Content-Type"] else r.read()

    def test_painel_e_estado(self):
        self.assertIn(b"Frederico", self.pedir("/"))
        self.assertEqual(self.pedir("/api/estado")["player"]["volume"], self.player.volume)

    def test_comandos(self):
        self.assertIn("50%", self.pedir("/api/volume", {"valor": 50})["msg"])
        self.assertIn("Não tem nada", self.pedir("/api/comando", {"acao": "pular"})["msg"])
        self.pedir("/api/mic", {"ligado": False, "ganho": 150, "ouvir_saida": True})
        audio = self.pedir("/api/estado")["audio"]
        self.assertFalse(audio["mic_ligado"])
        self.assertEqual(audio["ganho_mic"], 150)
        self.assertTrue(audio["ouvir_saida"])

    def test_recusa_host_de_fora(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.pedir("/api/estado", host="site-malvado.com")
        self.assertEqual(ctx.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
