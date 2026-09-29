"""
Testes do reconhecimento de pedidos do Bardo. Da raiz do projeto:
    python -m unittest discover -s modules/bardo -t .
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from modules.bardo.service import (  # noqa: E402
    MAX_FILA,
    PASSO_VOLUME,
    Fila,
    FilaCheia,
    Musica,
    Pedido,
    chamou_a_natty,
    interpretar_pedido,
    novo_volume,
)

LINK = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


class ChamouANatty(unittest.TestCase):
    def test_pelo_nome(self):
        for texto in ["natty toca", "Natty, pausa", "ei natty para", "@Natty volume 30", "NATTY: continua"]:
            with self.subTest(texto=texto):
                self.assertTrue(chamou_a_natty(texto))

    def test_sem_chamar(self):
        for texto in ["toca essa", "a natty toca bem", "nattyzinha pausa", "pausa pro café"]:
            with self.subTest(texto=texto):
                self.assertFalse(chamou_a_natty(texto))


class Tocar(unittest.TestCase):
    def test_gatilhos_com_link(self):
        for verbo in ["toca", "toque", "tocar", "bota", "coloca", "põe", "play"]:
            with self.subTest(verbo=verbo):
                self.assertEqual(interpretar_pedido(f"natty {verbo} {LINK}"), Pedido("tocar", link=LINK))

    def test_youtu_be_com_querystring(self):
        link = "https://youtu.be/dQw4w9WgXcQ?si=abc&list=PL123"
        self.assertEqual(interpretar_pedido(f"natty toca {link}"), Pedido("tocar", link=link))

    def test_sem_link_pede_link(self):
        self.assertEqual(interpretar_pedido("natty toca uma música de taverna"), Pedido("tocar"))

    def test_para_na_frase_nao_para(self):
        self.assertEqual(interpretar_pedido(f"natty toca essa para mim {LINK}"), Pedido("tocar", link=LINK))

    def test_para_na_frase_sem_link_nao_para(self):
        for texto in ["natty toca uma música para relaxar", "natty bota algo de taverna para o combate"]:
            with self.subTest(texto=texto):
                self.assertEqual(interpretar_pedido(texto), Pedido("tocar"))


class Controles(unittest.TestCase):
    def test_pausar(self):
        for texto in ["natty pausa", "natty, pause a música", "natty pausar"]:
            with self.subTest(texto=texto):
                self.assertEqual(interpretar_pedido(texto), Pedido("pausar"))

    def test_continuar(self):
        for texto in ["natty continua", "natty volta a tocar", "natty despausa", "natty retoma"]:
            with self.subTest(texto=texto):
                self.assertEqual(interpretar_pedido(texto), Pedido("continuar"))

    def test_parar(self):
        for texto in ["natty para", "natty para de tocar", "natty stop", "natty chega", "natty sai do canal"]:
            with self.subTest(texto=texto):
                self.assertEqual(interpretar_pedido(texto), Pedido("parar"))

    def test_nao_e_pedido(self):
        for texto in ["natty", "natty bom dia", "natty rola 1d20"]:
            with self.subTest(texto=texto):
                self.assertIsNone(interpretar_pedido(texto))


class PedidosDeFila(unittest.TestCase):
    def test_adicionar_e_tocar(self):
        for texto in [f"natty adiciona {LINK}", f"natty coloca na fila {LINK}", f"natty add {LINK}"]:
            with self.subTest(texto=texto):
                self.assertEqual(interpretar_pedido(texto), Pedido("tocar", link=LINK))

    def test_pular(self):
        for texto in ["natty pula", "natty próxima", "natty proxima", "natty toca a próxima", "natty skip"]:
            with self.subTest(texto=texto):
                self.assertEqual(interpretar_pedido(texto), Pedido("pular"))

    def test_ver_fila(self):
        for texto in ["natty fila", "natty mostra a fila", "natty qual a playlist?"]:
            with self.subTest(texto=texto):
                self.assertEqual(interpretar_pedido(texto), Pedido("fila"))

    def test_limpar_fila(self):
        for texto in ["natty limpa a fila", "natty esvazia a fila", "natty zera a playlist"]:
            with self.subTest(texto=texto):
                self.assertEqual(interpretar_pedido(texto), Pedido("limpar_fila"))


def _musica(n: int) -> Musica:
    return Musica(f"Música {n}", f"https://youtu.be/{n}")


class FilaDeMusicas(unittest.TestCase):
    def test_ordem_e_posicao(self):
        fila = Fila()
        self.assertEqual(fila.adicionar(_musica(1)), 1)
        self.assertEqual(fila.adicionar(_musica(2)), 2)
        self.assertEqual(fila.avancar(), _musica(1))
        self.assertEqual(fila.tocando, _musica(1))
        self.assertEqual(fila.proximas, (_musica(2),))
        self.assertEqual(fila.avancar(), _musica(2))
        self.assertIsNone(fila.avancar())
        self.assertIsNone(fila.tocando)

    def test_limpar_mantem_a_atual(self):
        fila = Fila()
        fila.tocando = _musica(0)
        fila.adicionar(_musica(1))
        fila.adicionar(_musica(2))
        self.assertEqual(fila.limpar(), 2)
        self.assertEqual(fila.proximas, ())
        self.assertEqual(fila.tocando, _musica(0))

    def test_resetar(self):
        fila = Fila()
        fila.tocando = _musica(0)
        fila.adicionar(_musica(1))
        fila.resetar()
        self.assertIsNone(fila.tocando)
        self.assertEqual(fila.proximas, ())

    def test_limite(self):
        fila = Fila()
        for n in range(MAX_FILA):
            fila.adicionar(_musica(n))
        with self.assertRaises(FilaCheia):
            fila.adicionar(_musica(MAX_FILA))


class Volume(unittest.TestCase):
    def test_absoluto(self):
        self.assertEqual(interpretar_pedido("natty volume 30"), Pedido("volume", volume=30))
        self.assertEqual(interpretar_pedido("natty coloca o volume em 75%"), Pedido("volume", volume=75))

    def test_absoluto_limitado(self):
        self.assertEqual(interpretar_pedido("natty volume 250"), Pedido("volume", volume=100))

    def test_relativo(self):
        self.assertEqual(interpretar_pedido("natty aumenta o volume"), Pedido("volume", delta_volume=PASSO_VOLUME))
        self.assertEqual(interpretar_pedido("natty abaixa"), Pedido("volume", delta_volume=-PASSO_VOLUME))
        self.assertEqual(interpretar_pedido("natty mais baixo"), Pedido("volume", delta_volume=-PASSO_VOLUME))

    def test_pergunta(self):
        self.assertEqual(interpretar_pedido("natty qual o volume?"), Pedido("volume"))

    def test_novo_volume(self):
        self.assertEqual(novo_volume(50, Pedido("volume", volume=10)), 10)
        self.assertEqual(novo_volume(90, Pedido("volume", delta_volume=PASSO_VOLUME)), 100)
        self.assertEqual(novo_volume(10, Pedido("volume", delta_volume=-PASSO_VOLUME)), 0)
        self.assertEqual(novo_volume(40, Pedido("volume")), 40)


if __name__ == "__main__":
    unittest.main()
