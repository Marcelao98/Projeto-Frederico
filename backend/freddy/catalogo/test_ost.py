"""Trilhas instrumentais (freddy.catalogo.ost): limpar título, escolher faixa, marcar e importar."""

import shutil
import tempfile
import unittest
from pathlib import Path

from freddy.catalogo import ost
from freddy.catalogo.compilar import PASTA_CATALOGO, carregar, conferir

OBRA = {"id": "jogo-teste", "nome": "Hollow Knight", "tipo": "jogo", "ano": "2017",
        "compositor": "Christopher Larkin", "apelidos": "hk", "grupo": "indie", "meta": "3",
        "playlist": "", "nota": ""}


def v(titulo, vid, dur=180, canal="Fulano"):
    return {"title": titulo, "id": vid, "duration": dur, "channel": canal}


class TestLimpar(unittest.TestCase):
    def test_tira_o_lixo_do_titulo(self):
        casos = {
            "Hollow Knight OST - Greenpath": "Greenpath",
            "Souls of Fire - Dark Souls Soundtrack 01": "Souls of Fire",
            "01. Dirtmouth": "Dirtmouth",
            "Greenpath (Hollow Knight Original Soundtrack)": "Greenpath",
            "🎵 RPG Combat Music | Paladin's Resolve": "Paladin's Resolve",
            "Hollow Knight - City of Tears": "City of Tears",
            "Nighttime Coming (Yoru Kitaru) - Spirited Away Ost「02」": "Nighttime Coming (Yoru Kitaru)",
        }
        for bruto, limpo in casos.items():
            self.assertEqual(ost.limpar_titulo(bruto, "Hollow Knight"), limpo, bruto)

    def test_faixas_validas_corta_cover_compilacao_e_repetida(self):
        videos = [v("Hollow Knight OST - Greenpath", "a"), v("Greenpath (piano cover)", "b"),
                  v("Hollow Knight Full OST", "c", dur=5000), v("Greenpath", "d"), v("Vinheta", "e", dur=10),
                  v("City of Tears", "f", canal="Christopher Larkin")]
        f = ost.faixas_validas(OBRA, videos)
        self.assertEqual([x["titulo"] for x in f], ["Greenpath", "City of Tears"])
        self.assertEqual([x["oficial"] for x in f], ["0", "1"])
        self.assertEqual([x["ordem"] for x in f], ["1", "2"])

    def test_playlist_de_arranjo_nao_serve(self):
        self.assertEqual(ost.nota_da_playlist(OBRA, "Hollow Knight Piano Collection", 30), 0)
        self.assertEqual(ost.nota_da_playlist(OBRA, "Elden Ring OST", 30), 0)
        outra = dict(OBRA, id="outra", nome="Outro Jogo", apelidos="hk")
        self.assertEqual(ost.nomes_proprios(OBRA, [OBRA, outra]), ["Hollow Knight"])
        self.assertGreater(ost.nota_da_playlist(OBRA, "Hollow Knight (Original Soundtrack)", 30),
                           ost.nota_da_playlist(OBRA, "Hollow Knight songs", 30))


class TestMarcarEImportar(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cat = self.tmp / "catalogo"
        shutil.copytree(PASTA_CATALOGO, self.cat, ignore=shutil.ignore_patterns("ost", "blocos"))
        self.ost = self.cat / "ost"
        ost.gravar(self.ost / "obras.csv", ost.COLUNAS_OBRA, [OBRA])
        faixas = ost.faixas_validas(OBRA, [v("Greenpath", "a"), v("Mantis Lords", "b"), v("Jingle", "c")])
        n, erros = ost.aplicar_marcas(faixas, [
            "1|rpg-exploracao|floresta|calmo,misterioso|2|3|S|harpa,cordas|foco,relaxar|70|",
            "2|rpg-chefe||epico,tenso|5|3|E|orquestra||80|",
            "3||||||X",
        ])
        self.faixas = faixas
        ost.gravar(self.ost / "faixas" / f"{OBRA['id']}.csv", ost.COLUNAS_FAIXA, faixas)

    def test_marcas_viram_colunas(self):
        f1, f2, f3 = self.faixas
        self.assertEqual((f1["climas"], f1["estavel"], f1["ocasioes"], f1["uso"]),
                         ("calmo|misterioso", "1", "foco|relaxar", "rpg-exploracao"))
        self.assertEqual((f2["essencial"], f2["estavel"], f2["tem_voz"]), ("1", "0", "0"))
        self.assertEqual(f3["fora"], "1")
        tags = {x["id"]: x["gaveta"] for x in ost.ler(self.cat / "tags.csv")}
        self.assertEqual(ost.conferir_faixas(self.faixas, tags), [])
        errado = dict(f1, climas="calmo", ocasioes="rpg-chefe")
        self.assertTrue(len(ost.conferir_faixas([errado], tags)) >= 2)

    def test_importa_compila_e_e_idempotente(self):
        for _ in range(2):
            rel = ost.importar(self.cat, self.ost)
            self.assertEqual((rel.entraram, rel.fora, rel.erros), (2, 1, []))
        d = carregar(self.cat)
        r = conferir(d)
        self.assertEqual(r.erros, [])
        novas = [m for m in d["musicas"] if m["lote"] == ost.LOTE]
        self.assertEqual(sorted(m["titulo"] for m in novas), ["Greenpath", "Mantis Lords"])
        g = next(m for m in novas if m["titulo"] == "Greenpath")
        self.assertEqual((g["obra"], g["estavel"], g["ano"]), ("jogo-teste", "1", "2017"))
        self.assertIn({"musica": g["id"], "genero": "trilha-de-jogo", "peso": "1.0"}, d["musica_genero"])
        self.assertTrue(any(o["id"] == "jogo-teste" for o in d["obras"]))


if __name__ == "__main__":
    unittest.main()
