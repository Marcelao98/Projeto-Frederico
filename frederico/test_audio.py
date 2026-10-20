"""Mixagem, buffer e motor, sem placa de som (o sounddevice nem é importado)."""

import unittest

import numpy as np

from frederico import mixer
from frederico.audio import Buffer, Motor


class PlayerFalso:
    def ler(self, quadros):
        return np.full((quadros, 2), 0.5, np.float32)


class TestMixer(unittest.TestCase):
    def test_mic_mono_vira_estereo_e_soma(self):
        saida = mixer.misturar(np.zeros((4, 2), np.float32), np.full((4, 1), 0.3, np.float32), 1.0, 1.0)
        self.assertEqual(saida.shape, (4, 2))
        self.assertAlmostEqual(float(saida[0, 1]), 0.3, places=5)

    def test_limitador_nao_mexe_no_normal_e_segura_o_alto(self):
        self.assertAlmostEqual(float(mixer.limitar(np.array([0.5]))[0]), 0.5)
        self.assertLessEqual(float(mixer.limitar(np.array([5.0]))[0]), 1.0)
        self.assertGreaterEqual(float(mixer.limitar(np.array([-5.0]))[0]), -1.0)

    def test_ducking_cai_na_hora_e_volta_devagar(self):
        d = mixer.Ducker(0.02)
        self.assertEqual(d.proximo(0.1), mixer.GANHO_DUCKING)
        depois = d.proximo(0.0)
        self.assertGreater(depois, mixer.GANHO_DUCKING)
        self.assertLess(depois, 1.0)
        for _ in range(100):
            d.proximo(0.0)
        self.assertEqual(d.ganho, 1.0)

    def test_ducking_desligado(self):
        self.assertEqual(mixer.Ducker(0.02).proximo(0.5, ligado=False), 1.0)


class TestBuffer(unittest.TestCase):
    def test_completa_com_silencio_e_guarda_a_sobra(self):
        b = Buffer(canais=1)
        b.colocar(np.ones((5, 1), np.float32))
        self.assertEqual(float(b.tirar(3).sum()), 3)
        self.assertEqual(float(b.tirar(4).sum()), 2)
        self.assertEqual(len(b), 0)

    def test_joga_fora_o_mais_velho_quando_atrasa(self):
        b = Buffer(maximo=10, canais=1)
        b.colocar(np.zeros((8, 1), np.float32))
        b.colocar(np.ones((8, 1), np.float32))
        self.assertEqual(len(b), 8)
        self.assertEqual(float(b.tirar(8).sum()), 8)


class TestMotor(unittest.TestCase):
    def test_voz_abaixa_a_musica_mas_nao_o_monitor_de_mic(self):
        motor = Motor(PlayerFalso())
        motor.config = {"mic": 1, "saida": 2, "monitor": 3}
        motor._mic.colocar(np.full((960, 1), 0.2, np.float32))
        saida, so_musica = motor.processar(960)
        self.assertAlmostEqual(float(so_musica[0, 0]), 0.5 * mixer.GANHO_DUCKING, places=5)
        self.assertAlmostEqual(float(saida[0, 0]), 0.5 * mixer.GANHO_DUCKING + 0.2, places=5)

    def test_mic_mudo_nao_vai_pra_saida(self):
        motor = Motor(PlayerFalso())
        motor.config = {"mic": 1, "saida": 2, "monitor": None}
        motor.mic_ligado = False
        motor.ducking = False
        motor._mic.colocar(np.full((960, 1), 0.2, np.float32))
        saida, _ = motor.processar(960)
        self.assertAlmostEqual(float(saida[0, 0]), 0.5, places=5)

    def test_sem_mic_so_musica(self):
        motor = Motor(PlayerFalso())
        motor.config = {"mic": None, "saida": 2, "monitor": None}
        saida, _ = motor.processar(960)
        self.assertAlmostEqual(float(saida[0, 0]), 0.5, places=5)


if __name__ == "__main__":
    unittest.main()
