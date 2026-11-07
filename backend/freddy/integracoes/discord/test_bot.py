"""O bot sem o Discord de verdade: o chat (Conversa), o som da call e o token."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from freddy.audio.mesa import Mesa
from freddy.audio.pcm import BYTES_POR_QUADRO, SILENCIO
from freddy.audio.reprodutor_falso import ReprodutorFalso
from freddy.integracoes.discord.bot import PERMISSOES_DO_CONVITE, BotDoFreddy, link_de_convite
from freddy.conversa.cerebro import AJUDA, Conversa, fala_do_evento
from freddy.audio.saidas.discord import SaidaDiscord
from freddy.dados.acervo import Acervo
from freddy.dados.playlists import Playlists
from freddy.dados.segredos import VARIAVEL, Segredos
from freddy.salas.motor import Motor


def m(n: int) -> dict:
    return {"titulo": f"Música {n}", "link": f"https://www.youtube.com/watch?v=v{n}"}


class YoutubeFalso:
    def info(self, link):
        return {"titulo": "Vídeo Colado", "duracaoSegundos": 200}

    def buscar(self, texto):
        if texto == "nada existe":
            raise LookupError(texto)
        return {"titulo": f"Achei {texto}", "link": "https://www.youtube.com/watch?v=yt1", "duracaoSegundos": 100}


class Base(unittest.TestCase):
    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.pasta, True)
        self.motor = Motor(ReprodutorFalso())
        self.playlists = Playlists(self.pasta / "playlists.json")
        self.conversa = Conversa(self.motor, Acervo(self.pasta / "aprendidas.json"), self.playlists, YoutubeFalso())

    def diz(self, texto: str) -> str:
        return asyncio.run(self.conversa.responder(texto))


class TestConversa(Base):
    def test_busca_no_acervo_e_comandos(self):
        r = self.diz("toca calmo e hollow knight")
        self.assertTrue(r.startswith("Tocando **"), r)
        self.assertEqual(self.motor.estado()["tocando"]["origem"], "Hollow Knight")
        self.assertIn("📜 Próximas:", self.diz("fila"))
        self.assertTrue(self.diz("pula").startswith("Pulei ⏭️"))
        self.assertEqual(self.diz("volume 30"), "Volume em 30% 🔊")
        self.assertEqual(self.diz("qual o volume?"), "O volume está em 30%.")
        self.assertIn("Repetindo", self.diz("repete"))
        self.assertIn("desligada", self.diz("para de repetir"))
        self.assertEqual(self.diz("para"), "Parei ⏹️")
        self.assertEqual(self.diz("pausa"), "Não tem nada tocando.")

    def test_link_e_busca_livre(self):
        self.assertEqual(self.diz("toca https://youtu.be/abc"), "Tocando **Vídeo Colado** 🎵")
        r = self.diz("toca uma coisa que nao tem no acervo zzz")
        self.assertIn("procurei no YouTube: **Achei uma coisa que nao tem no acervo zzz**, na fila (posição 1)", r)
        self.assertIn("nem no acervo nem no YouTube", self.diz("toca nada existe"))

    def test_playlists_pelo_discord(self):
        self.assertIn("Nenhuma playlist", self.diz("playlists"))
        self.motor.executar({"tipo": "adicionar", "musicas": [m(1), m(2)]})
        self.assertEqual(self.diz("salva a fila como Sessão 12"), "Salvei a playlist **Sessão 12** com 2 músicas 💾")
        self.assertIn("Atualizei", self.diz('salva a fila como "Sessão 12"'))
        self.assertEqual(len(self.playlists.listar()), 1)
        self.motor.executar({"tipo": "parar"})
        self.motor.executar({"tipo": "adicionar", "musicas": [m(9)]})
        r = self.diz("toca a playlist sessao 12")
        self.assertIn("Tocando a playlist **Sessão 12** 🎵 (2 músicas)", r)
        self.assertEqual([x["titulo"] for x in [self.motor.estado()["tocando"], *self.motor.estado()["proximas"]]], ["Música 1", "Música 2"])
        self.assertIn("Pus a playlist", self.diz("põe a playlist sessão 12 na fila"))
        self.assertIn('Não achei a playlist "dragão"', self.diz("toca a playlist dragão"))
        self.assertIn("**Sessão 12** (2 músicas)", self.diz("playlists"))

    def test_ajuda_e_nao_entendi(self):
        self.assertEqual(self.diz(""), AJUDA)
        self.assertEqual(self.diz("ajuda"), AJUDA)
        self.assertIn("Não entendi", self.diz("bom dia"))

    def test_sair_e_markdown(self):
        self.assertTrue(Conversa.quer_sair("sai da call"))
        self.assertFalse(Conversa.quer_sair("toca sai"))
        self.assertEqual(fala_do_evento({"tipo": "tocando_agora", "musica": {"titulo": "a*b"}}), "Tocando agora **a\\*b** 🎵")


class TestQuerTocar(unittest.TestCase):
    def test_so_pedido_de_tocar_entra_na_call(self):
        self.assertTrue(BotDoFreddy._quer_tocar("toca triste"))
        self.assertTrue(BotDoFreddy._quer_tocar("toca https://youtu.be/x"))
        self.assertTrue(BotDoFreddy._quer_tocar("toca a playlist sessão 12"))
        self.assertFalse(BotDoFreddy._quer_tocar("fila"))
        self.assertFalse(BotDoFreddy._quer_tocar("pula"))
        self.assertFalse(BotDoFreddy._quer_tocar("toca"))

    def test_convite_com_as_permissoes(self):
        url = link_de_convite(123)
        self.assertIn("client_id=123", url)
        self.assertIn(f"permissions={PERMISSOES_DO_CONVITE}", url)
        self.assertEqual(PERMISSOES_DO_CONVITE, 3214336)


class TestSomDaCall(unittest.TestCase):
    def tom(self, valor: int) -> bytes:
        return np.full(BYTES_POR_QUADRO // 2, valor, dtype=np.int16).tobytes()

    def test_discord_puxa_e_a_caixa_toca_a_copia(self):
        mesa = Mesa()
        mesa.ganho = 1.0
        quadros = [self.tom(100), self.tom(200)]

        class Fonte:
            esgotada = False

            def ler_quadro(self):
                return quadros.pop(0) if quadros else None

            def fechar(self):
                pass

        mesa.trocar(Fonte())
        saida = SaidaDiscord(mesa)
        mesa.entrar_no_discord()
        self.assertFalse(saida.is_opus())
        self.assertEqual(saida.read(), self.tom(100))
        self.assertEqual(mesa.ler_para_local(), self.tom(100))  # a cópia, não o próximo quadro
        self.assertEqual(saida.read(), self.tom(200))
        self.assertEqual(mesa.ler_para_local(), self.tom(200))
        self.assertEqual(mesa.ler_para_local(), SILENCIO)  # o Discord ainda não puxou

    def test_sem_ouvir_aqui_a_caixa_fica_muda(self):
        mesa = Mesa()
        mesa.entrar_no_discord()
        mesa.ouvir_aqui = False
        SaidaDiscord(mesa).read()
        self.assertEqual(mesa.ler_para_local(), SILENCIO)

    def test_player_parado_nao_tira_a_mesa_do_discord(self):
        mesa = Mesa()
        mesa.entrar_no_discord()
        SaidaDiscord(mesa).cleanup()  # o bot parou o player (música parou)
        self.assertTrue(mesa.no_discord)
        mesa.sair_do_discord()  # saiu da call
        self.assertFalse(mesa.no_discord)

    def test_quadro_sempre_do_tamanho_do_discord(self):
        self.assertEqual(len(SaidaDiscord(Mesa()).read()), 3840)

    def test_medidor_conta_o_que_foi_pra_call(self):
        mesa = Mesa()
        mesa.ganho = 1.0
        mesa.assobiar()
        saida = SaidaDiscord(mesa)
        for _ in range(10):
            saida.read()
        med = saida.medidor()
        self.assertEqual((med["quadros"], med["quadrosPorSegundo"]), (10, 10))
        self.assertGreater(med["comSomPorSegundo"], 0)
        self.assertGreater(med["nivel"], 1000)

    def test_assobio_toca_no_lugar_da_musica_e_depois_ela_volta(self):
        from freddy.audio.fontes.assobio import quadros_do_assobio

        mesa = Mesa()
        mesa.ganho = 1.0
        musica = [self.tom(100)] * 3

        class Fonte:
            esgotada = False
            segundos_no_buffer = 1.0

            def ler_quadro(self):
                return musica.pop(0) if musica else None

            def fechar(self):
                pass

        mesa.trocar(Fonte())
        segundos = mesa.assobiar()
        self.assertGreater(segundos, 1)
        self.assertEqual(mesa.diagnostico()["musica"], "assobiando")
        assobio = quadros_do_assobio()
        self.assertEqual([mesa.ler() for _ in assobio], list(assobio))
        self.assertEqual(mesa.ler(), self.tom(100))  # a música segue de onde estava
        self.assertEqual(mesa.diagnostico()["musica"], "tocando")

    def test_diagnostico_avisa_engasgo(self):
        mesa = Mesa()

        class Vazia:
            esgotada = False
            segundos_no_buffer = 0.0

            def ler_quadro(self):
                return None

            def fechar(self):
                pass

        mesa.trocar(Vazia())
        self.assertEqual(mesa.diagnostico()["musica"], "carregando")
        mesa.quadros_tocados = 10
        self.assertEqual(mesa.diagnostico()["musica"], "engasgou")
        mesa.entrar_no_discord()
        mesa.ouvir_aqui = False
        self.assertTrue(mesa.diagnostico()["mudoLocal"])



class TestSegredos(unittest.TestCase):
    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.pasta, True)
        self.s = Segredos(self.pasta / "discord.json")

    def test_guarda_le_e_esquece(self):
        self.assertIsNone(self.s.token())
        self.s.guardar("  abc.def  ")
        self.assertEqual(self.s.token(), "abc.def")
        self.assertEqual(json.loads((self.pasta / "discord.json").read_text()), {"token": "abc.def"})
        if sys.platform != "win32":
            self.assertEqual(stat.S_IMODE(os.stat(self.pasta / "discord.json").st_mode), 0o600)
        self.s.esquecer()
        self.assertIsNone(self.s.token())

    def test_variavel_de_ambiente_ganha(self):
        self.s.guardar("do-arquivo")
        with mock.patch.dict(os.environ, {VARIAVEL: "do-ambiente"}):
            self.assertEqual(self.s.token(), "do-ambiente")
            self.assertTrue(self.s.do_ambiente)


class TestBotSemConectar(unittest.TestCase):
    def test_estado_desligado(self):
        pasta = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, pasta, True)
        motor = Motor(ReprodutorFalso())
        bot = BotDoFreddy(motor, ReprodutorFalso(), None, Segredos(pasta / "d.json"))  # type: ignore[arg-type]
        e = bot.estado()
        self.assertEqual((e["situacao"], e["configurado"], e["servidores"], e["podeTocar"]), ("desligado", False, [], False))

    def test_entrar_sem_conectar_e_sem_som(self):
        from freddy.integracoes.discord.bot import ErroDoBot

        pasta = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, pasta, True)
        bot = BotDoFreddy(Motor(ReprodutorFalso()), ReprodutorFalso(), None, Segredos(pasta / "d.json"))  # type: ignore[arg-type]
        with self.assertRaisesRegex(ErroDoBot, "não está conectado"):
            asyncio.run(bot.entrar(1))


    def test_so_na_call_fica_guardado(self):
        pasta = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, pasta, True)

        class ComMesa(ReprodutorFalso):
            def __init__(self):
                super().__init__()
                self.mesa = Mesa()

        bot = BotDoFreddy(Motor(ReprodutorFalso()), ComMesa(), None, Segredos(pasta / "d.json"))  # type: ignore[arg-type]
        self.assertTrue(bot.mesa.ouvir_aqui)
        bot.definir_ouvir_aqui(False)
        de_novo = BotDoFreddy(Motor(ReprodutorFalso()), ComMesa(), None, Segredos(pasta / "d.json"))  # type: ignore[arg-type]
        self.assertFalse(de_novo.mesa.ouvir_aqui)
        self.assertFalse(de_novo.estado()["ouvirAqui"])

    def test_assobio_pede_call_e_diagnostico_responde(self):
        from freddy.integracoes.discord.bot import ErroDoBot

        pasta = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, pasta, True)

        class ComMesa(ReprodutorFalso):
            def __init__(self):
                super().__init__()
                self.mesa = Mesa()

        bot = BotDoFreddy(Motor(ReprodutorFalso()), ComMesa(), None, Segredos(pasta / "d.json"))  # type: ignore[arg-type]
        with self.assertRaisesRegex(ErroDoBot, "nenhuma call"):
            asyncio.run(bot.assobiar())
        d = bot.diagnostico()
        self.assertEqual((d["bot"], d["canal"], d["transmissao"]), ("desligado", None, None))
        self.assertEqual(d["mesa"]["musica"], "sem música")


    def test_toca_na_call_so_quando_tem_som_como_o_kenku(self):
        pasta = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, pasta, True)

        class ComMesa(ReprodutorFalso):
            def __init__(self):
                super().__init__()
                self.mesa = Mesa()

        class VozFalsa:
            def __init__(self):
                self.tocando = None
                self.channel = None

            def is_connected(self):
                return True

            def is_playing(self):
                return self.tocando is not None

            def play(self, fonte, after=None):
                self.tocando = fonte

            def stop(self):
                self.tocando = None

        reprodutor = ComMesa()
        motor = Motor(reprodutor)
        bot = BotDoFreddy(motor, reprodutor, None, Segredos(pasta / "d.json"))  # type: ignore[arg-type]
        bot.voz = VozFalsa()  # type: ignore[assignment]
        bot._atualizar_player()
        self.assertFalse(bot.voz.is_playing())  # parado: nada de silêncio na call
        motor.executar({"tipo": "adicionar", "musicas": [m(1)]})
        self.assertIsInstance(bot.voz.tocando, SaidaDiscord)
        primeira = bot.voz.tocando
        motor.executar({"tipo": "parar"})
        self.assertFalse(bot.voz.is_playing())
        motor.executar({"tipo": "adicionar", "musicas": [m(2)]})
        self.assertIsNot(bot.voz.tocando, primeira)  # recurso novo a cada play


if __name__ == "__main__":
    unittest.main()
