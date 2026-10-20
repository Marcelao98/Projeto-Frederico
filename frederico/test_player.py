"""Player sem rede nem placa de som: fontes falsas e relógio de mentira."""

import time
import unittest
from unittest import mock

import numpy as np

from frederico import service
from frederico.player import Player


class FonteFalsa:
    def __init__(self, quadros: int):
        self.restam = quadros
        self.fechada = False

    @property
    def terminou(self):
        return self.restam == 0

    def ler(self, quadros):
        n = min(quadros, self.restam)
        self.restam -= n
        return np.full((n, 2), 0.5, np.float32)

    def fechar(self):
        self.fechada = True


class Relogio:
    def __init__(self):
        self.agora = 0.0

    def __call__(self):
        return self.agora


def musica(nome):
    return service.Musica(nome, f"https://youtu.be/{nome}")


class TestPlayer(unittest.TestCase):
    def setUp(self):
        self.relogio = Relogio()
        self.abertas = []
        self.quebradas = set()

        def abrir(m, info):
            if m.titulo in self.quebradas:
                raise RuntimeError("link morto")
            fonte = FonteFalsa(960 * 3)
            self.abertas.append((m.titulo, fonte))
            return fonte

        self.player = Player(abrir=abrir, relogio=self.relogio)
        busca = mock.patch.object(service, "buscar_musicas", side_effect=lambda t: ([musica(x) for x in t.split()], len(t.split())))
        busca.start()
        self.addCleanup(busca.stop)

    def esperar_fins(self):
        self.player._fins.join()

    def tocar_ate_acabar(self):
        for _ in range(4):
            self.player.ler(960)
        self.esperar_fins()

    def test_tocar_comeca_e_enfileira(self):
        resposta = self.player.tocar("a b c")
        self.assertIn("Tocando a", resposta)
        self.assertEqual(self.player.estado()["proximas"], ["b", "c"])

    def test_volume_e_pausa_no_audio(self):
        self.player.tocar("a")
        self.player.mudar_volume(50)
        self.assertAlmostEqual(float(self.player.ler(10)[0, 0]), 0.25)
        self.player.pausar()
        self.assertEqual(float(np.abs(self.player.ler(10)).max()), 0.0)
        self.player.continuar()
        self.assertGreater(float(self.player.ler(10)[0, 0]), 0)

    def test_acabou_sozinha_anda_a_fila(self):
        self.player.tocar("a b")
        self.relogio.agora = 100  # tocou bastante: não é falha
        self.tocar_ate_acabar()
        self.assertEqual(self.player.estado()["tocando"], "b")

    def test_falha_rapida_tenta_de_novo_uma_vez(self):
        self.player.tocar("a b")
        self.tocar_ate_acabar()  # acabou em 0 s: falha → tenta "a" de novo
        self.assertEqual([t for t, _ in self.abertas], ["a", "a"])
        self.tocar_ate_acabar()  # falhou de novo: desiste e pula
        self.assertEqual(self.player.estado()["tocando"], "b")

    def test_repetir(self):
        self.player.tocar("a b")
        self.player.repetir()
        self.relogio.agora = 100
        self.tocar_ate_acabar()
        self.assertEqual(self.player.estado()["tocando"], "a")

    def test_pular_desliga_repetir_e_fecha_a_fonte(self):
        self.player.tocar("a b")
        self.player.repetir()
        fonte_a = self.abertas[0][1]
        self.assertIn("repetição desligada", self.player.pular())
        self.assertTrue(fonte_a.fechada)
        self.assertEqual(self.player.estado()["tocando"], "b")
        self.assertFalse(self.player.estado()["repetir"])

    def test_link_morto_pula_pra_proxima(self):
        self.quebradas.add("a")
        self.assertIn("Tocando b", self.player.tocar("a b"))

    def test_parar_esvazia(self):
        self.player.tocar("a b")
        self.player.parar()
        estado = self.player.estado()
        self.assertIsNone(estado["tocando"])
        self.assertEqual(estado["proximas"], [])
        self.assertEqual(float(np.abs(self.player.ler(10)).max()), 0.0)

    def test_frase_em_portugues(self):
        self.player.tocar("a")
        self.assertIn("40%", self.player.executar("volume 40"))
        self.assertIn("Pausei", self.player.executar("pausa"))

    def test_arquivo_local(self):
        with mock.patch("frederico.player.eh_arquivo_local", return_value=True):
            self.assertIn("Tocando aula", self.player.tocar("C:/musicas/aula.mp3"))


if __name__ == "__main__":
    unittest.main()
