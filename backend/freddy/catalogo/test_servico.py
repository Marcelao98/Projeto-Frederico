"""O catálogo dentro do app (freddy.catalogo.servico) e a rota /catalogo."""

import tempfile
import unittest
from pathlib import Path

from freddy.catalogo.compilar import PASTA_CATALOGO
from freddy.catalogo.servico import CatalogoDoApp


class TestCatalogoDoApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.cat = CatalogoDoApp(PASTA_CATALOGO, Path(cls.tmp.name) / "catalogo.db")
        cls.cat.preparar()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_compila_sozinho_e_fica_pronto(self):
        self.assertIsNone(self.cat.erro)
        self.assertTrue(self.cat.pronto)
        self.assertGreater(self.cat.quantas, 5000)

    def test_pedido_vira_musicas_pra_fila(self):
        r = self.cat.buscar("pagode anos 90 pro churrasco")
        self.assertTrue(r["entendeu"])
        self.assertTrue(0 < len(r["musicas"]) <= 15)
        for m in r["musicas"]:
            self.assertTrue(m["link"].startswith("https://www.youtube.com/watch?v="))
            self.assertIn(" - ", m["titulo"])  # "Artista - Título"
            self.assertIn(m["faixaId"], self.cat.cat.musicas)
            self.assertIn("pagode", self.cat.cat.musicas[m["faixaId"]]["generos"])

    def test_pedido_pelo_nome_traz_a_certa_primeiro(self):
        r = self.cat.buscar("evidências")
        self.assertIn("Evidências", r["musicas"][0]["titulo"])

    def test_rpg_continua_funcionando(self):
        r = self.cat.buscar("triste e bloodborne")
        self.assertTrue(r["musicas"])
        self.assertTrue(all(m["faixaId"].startswith("bloodborne") for m in r["musicas"]))

    def test_e_depois_divide_o_pedido(self):
        r = self.cat.buscar("um pagode e depois um rock internacional", quantas=10)
        generos = [self.cat.cat.musicas[m["faixaId"]]["generos"] for m in r["musicas"]]
        self.assertIn("pagode", generos[0])
        self.assertIn("rock", generos[-1])

    def test_palavra_que_nao_conhece_deixa_pro_resto(self):
        r = self.cat.buscar("triste zzzxqw")
        self.assertEqual(r, {"musicas": [], "total": 0, "entendeu": False})

    def test_sem_csv_nao_quebra(self):
        with tempfile.TemporaryDirectory() as t:
            fora = CatalogoDoApp(Path(t) / "nao-existe", Path(t) / "c.db")
            fora.preparar()
            self.assertFalse(fora.pronto)
            self.assertTrue(fora.erro)
            self.assertEqual(fora.buscar("pagode")["musicas"], [])


if __name__ == "__main__":
    unittest.main()
