"""Entender pedidos (freddy.nucleo.pedido). Rodar de dentro de backend/:
    python -m unittest discover -s freddy -t .
"""

import unittest

from freddy.nucleo.pedido import PASSO_VOLUME, Pedido, interpretar_pedido, novo_volume
from freddy.nucleo.texto import extrair_link_youtube

LINK = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


class Tocar(unittest.TestCase):
    def test_gatilhos_com_link(self):
        for verbo in ["toca", "toque", "tocar", "bota", "coloca", "põe", "play"]:
            with self.subTest(verbo=verbo):
                self.assertEqual(interpretar_pedido(f"freddy {verbo} {LINK}"), Pedido("tocar", link=LINK))

    def test_youtu_be_com_querystring(self):
        link = "https://youtu.be/dQw4w9WgXcQ?si=abc&list=PL123"
        self.assertEqual(interpretar_pedido(f"freddy toca {link}"), Pedido("tocar", link=link))

    def test_sem_link_vira_busca(self):
        self.assertEqual(
            interpretar_pedido("freddy toca triste e bloodborne"), Pedido("tocar", busca="triste e bloodborne")
        )
        self.assertEqual(interpretar_pedido("<@123> play boss fight!"), Pedido("tocar", busca="boss fight"))

    def test_sem_link_nem_busca(self):
        self.assertEqual(interpretar_pedido("freddy toca"), Pedido("tocar"))

    def test_para_na_frase_nao_para(self):
        self.assertEqual(interpretar_pedido(f"freddy toca essa para mim {LINK}"), Pedido("tocar", link=LINK))

    def test_para_na_frase_sem_link_nao_para(self):
        for texto in ["freddy toca uma música para relaxar", "freddy bota algo de taverna para o combate"]:
            with self.subTest(texto=texto):
                self.assertEqual(interpretar_pedido(texto).acao, "tocar")


class Controles(unittest.TestCase):
    def test_pausar(self):
        for texto in ["freddy pausa", "freddy, pause a música", "freddy pausar"]:
            with self.subTest(texto=texto):
                self.assertEqual(interpretar_pedido(texto), Pedido("pausar"))

    def test_continuar(self):
        for texto in ["freddy continua", "freddy volta a tocar", "freddy despausa", "freddy retoma"]:
            with self.subTest(texto=texto):
                self.assertEqual(interpretar_pedido(texto), Pedido("continuar"))

    def test_parar(self):
        for texto in ["freddy para", "freddy para de tocar", "freddy stop", "freddy chega", "freddy sai do canal"]:
            with self.subTest(texto=texto):
                self.assertEqual(interpretar_pedido(texto), Pedido("parar"))

    def test_nao_e_pedido(self):
        for texto in ["freddy", "freddy bom dia", "freddy rola 1d20"]:
            with self.subTest(texto=texto):
                self.assertIsNone(interpretar_pedido(texto))


class PedidosDeFila(unittest.TestCase):
    def test_adicionar_e_tocar(self):
        for texto in [f"freddy adiciona {LINK}", f"freddy coloca na fila {LINK}", f"freddy add {LINK}"]:
            with self.subTest(texto=texto):
                self.assertEqual(interpretar_pedido(texto), Pedido("tocar", link=LINK))

    def test_pular(self):
        for texto in ["freddy pula", "freddy próxima", "freddy proxima", "freddy toca a próxima", "freddy skip"]:
            with self.subTest(texto=texto):
                self.assertEqual(interpretar_pedido(texto), Pedido("pular"))

    def test_ver_fila(self):
        for texto in ["freddy fila", "freddy mostra a fila", "freddy qual a playlist?"]:
            with self.subTest(texto=texto):
                self.assertEqual(interpretar_pedido(texto), Pedido("fila"))

    def test_limpar_fila(self):
        for texto in ["freddy limpa a fila", "freddy esvazia a fila", "freddy zera a playlist"]:
            with self.subTest(texto=texto):
                self.assertEqual(interpretar_pedido(texto), Pedido("limpar_fila"))


class ParaDeOutraCoisa(unittest.TestCase):
    """"para de X" só para a música se X for música: "para de transcrever" é pedido pra outro bot."""

    def test_para_de_outra_coisa_nao_para_a_musica(self):
        for texto in ["freddy para de transcrever", "@Freddy pare de transcrever", "freddy parar de transcrever"]:
            with self.subTest(texto=texto):
                self.assertIsNone(interpretar_pedido(texto))

    def test_para_de_tocar_continua_parando(self):
        for texto in ["freddy para de tocar", "freddy para de cantar", "freddy para", "freddy para a música"]:
            with self.subTest(texto=texto):
                self.assertEqual(interpretar_pedido(texto).acao, "parar")


class Repetir(unittest.TestCase):
    """Repetir a faixa ATUAL: "freddy repete" alterna; "para de repetir"/"repete não" desliga."""

    def test_pedidos_que_alternam(self):
        for texto in ["freddy repete", "freddy, repete", "freddy repetir", "freddy repita essa", "freddy loop",
                      "@Freddy repete a música"]:
            with self.subTest(texto=texto):
                self.assertEqual(interpretar_pedido(texto), Pedido("repetir", repetir=None))

    def test_pedidos_que_desligam(self):
        for texto in ["freddy para de repetir", "freddy pare de repetir", "freddy repete não", "freddy não repete",
                      "freddy chega de loop", "freddy desliga o repetir", "freddy tira o loop"]:
            with self.subTest(texto=texto):
                self.assertEqual(interpretar_pedido(texto), Pedido("repetir", repetir=False))

    def test_toca_antes_do_repete_e_busca(self):
        self.assertEqual(interpretar_pedido("freddy toca Repete Comigo"), Pedido("tocar", busca="Repete Comigo"))

    def test_parar_e_pular_continuam_iguais(self):
        self.assertEqual(interpretar_pedido("freddy para").acao, "parar")
        self.assertEqual(interpretar_pedido("freddy pula").acao, "pular")


class Volume(unittest.TestCase):
    def test_absoluto(self):
        self.assertEqual(interpretar_pedido("freddy volume 30"), Pedido("volume", volume=30))
        self.assertEqual(interpretar_pedido("freddy coloca o volume em 75%"), Pedido("volume", volume=75))

    def test_absoluto_limitado(self):
        self.assertEqual(interpretar_pedido("freddy volume 250"), Pedido("volume", volume=100))

    def test_relativo(self):
        self.assertEqual(interpretar_pedido("freddy aumenta o volume"), Pedido("volume", delta_volume=PASSO_VOLUME))
        self.assertEqual(interpretar_pedido("freddy abaixa"), Pedido("volume", delta_volume=-PASSO_VOLUME))
        self.assertEqual(interpretar_pedido("freddy mais baixo"), Pedido("volume", delta_volume=-PASSO_VOLUME))

    def test_pergunta(self):
        self.assertEqual(interpretar_pedido("freddy qual o volume?"), Pedido("volume"))

    def test_novo_volume(self):
        self.assertEqual(novo_volume(50, Pedido("volume", volume=10)), 10)
        self.assertEqual(novo_volume(90, Pedido("volume", delta_volume=PASSO_VOLUME)), 100)
        self.assertEqual(novo_volume(10, Pedido("volume", delta_volume=-PASSO_VOLUME)), 0)
        self.assertEqual(novo_volume(40, Pedido("volume")), 40)


if __name__ == "__main__":
    unittest.main()
