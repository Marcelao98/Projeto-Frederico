"""
Testes do cog do Bardo que não dependem do Discord de verdade: parar e pular
só param a MÚSICA — não saem da call nem derrubam a escuta do Echo.
"""

import asyncio
import unittest
from types import SimpleNamespace
from unittest import mock

from modules.bardo import cog


class ConexaoComum:
    """discord.VoiceClient: stop() já é só a música."""

    def __init__(self, tocando=True):
        self.tocando = tocando
        self.stop = mock.MagicMock()
        self.disconnect = mock.AsyncMock()

    def is_playing(self):
        return self.tocando

    def is_paused(self):
        return False


class ConexaoDoEcho(ConexaoComum):
    """VoiceRecvClient: stop() para música E escuta; stop_playing() só a música."""

    def __init__(self, tocando=True):
        super().__init__(tocando)
        self.stop_playing = mock.MagicMock()


class TestPararNaoSaiDaCall(unittest.TestCase):
    def setUp(self):
        self.c = cog.BardoCog(bot=SimpleNamespace(user=None))

    def parar(self, conexao):
        guild = SimpleNamespace(id=1, voice_client=conexao)
        return asyncio.run(self.c._parar(guild))

    def test_parar_nao_desconecta(self):
        conexao = ConexaoComum()
        self.assertEqual(self.parar(conexao), "Parei ⏹️")
        conexao.stop.assert_called_once()
        conexao.disconnect.assert_not_called()

    def test_parar_com_o_echo_escutando_nao_derruba_a_escuta(self):
        conexao = ConexaoDoEcho()
        self.parar(conexao)
        conexao.stop_playing.assert_called_once()
        conexao.stop.assert_not_called()  # stop() mataria a escuta da senha
        conexao.disconnect.assert_not_called()

    def test_parar_limpa_a_fila(self):
        fila = self.c._fila(SimpleNamespace(id=1))
        with mock.patch.object(fila, "resetar") as resetar:
            self.parar(ConexaoComum())
        resetar.assert_called_once()

    def test_pular_com_o_echo_escutando_nao_derruba_a_escuta(self):
        conexao = ConexaoDoEcho()
        guild = SimpleNamespace(id=1, voice_client=conexao)
        self.c._pular(guild)
        conexao.stop_playing.assert_called_once()
        conexao.stop.assert_not_called()


if __name__ == "__main__":
    unittest.main()
