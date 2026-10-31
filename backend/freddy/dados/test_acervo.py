"""Acervo com ajustes e aprendidas, e a planilha (CSV). Dataset de mentira numa pasta temporária."""

from __future__ import annotations

import csv
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from freddy.dados import planilha
from freddy.dados.acervo import Acervo, FaixaNaoEncontrada
from modules.bardo import service

DATASET = {
    "_comentario": "teste",
    "musicas": [
        {
            "id": "hk-greenpath",
            "nome": "Greenpath",
            "link": "https://www.youtube.com/watch?v=green",
            "escopo": "faixa_individual",
            "origem": {"nome": "Hollow Knight", "tipo": "jogo"},
            "temas": ["calmo", "floresta"],
            "categorias": ["calmo", "natureza"],
            "comentario_pessoal": "",
        },
        {
            "id": "bb-cleric",
            "nome": "Cleric Beast",
            "link": "https://www.youtube.com/watch?v=cleric",
            "escopo": "faixa_individual",
            "origem": {"nome": "Bloodborne", "tipo": "jogo"},
            "temas": ["não classificado"],
            "categorias": [],
            "comentario_pessoal": "",
        },
    ],
}


class Base(unittest.TestCase):
    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.pasta, True)
        dataset = self.pasta / "dataset"
        dataset.mkdir()
        (dataset / "musicas.json").write_text(json.dumps(DATASET, ensure_ascii=False), encoding="utf-8")
        real = Path(service.__file__).parent / "dataset" / "vocabulario.json"
        shutil.copy(real, dataset / "vocabulario.json")
        self.acervo = Acervo(self.pasta / "mestre" / "aprendidas.json", pasta_dataset=dataset)

    def faixa(self, id_):
        return self.acervo.faixa(id_)


class TestAjustes(Base):
    def test_editar_temas_recalcula_categorias_e_nao_mexe_no_dataset(self):
        f = self.acervo.editar("bb-cleric", {"temas": ["Chefe", "terror", "chefe", " "]})
        self.assertEqual(f["temas"], ["chefe", "terror"])
        self.assertIn("chefe", f["categorias"])
        self.assertEqual(self.faixa("bb-cleric")["temas"], ["chefe", "terror"])
        dataset = json.loads((self.pasta / "dataset" / "musicas.json").read_text(encoding="utf-8"))
        self.assertEqual(dataset["musicas"][1]["temas"], ["não classificado"])
        self.assertTrue((self.pasta / "mestre" / "ajustes.json").exists())

    def test_voltar_ao_original_apaga_o_ajuste(self):
        self.acervo.editar("hk-greenpath", {"nome": "Greenpath (remix)"})
        self.assertIn("hk-greenpath", self.acervo.ajustes())
        self.acervo.editar("hk-greenpath", {"nome": "Greenpath"})
        self.assertEqual(self.acervo.ajustes(), {})

    def test_temas_vazios_viram_nao_classificado(self):
        self.assertEqual(self.acervo.editar("hk-greenpath", {"temas": []})["temas"], ["não classificado"])

    def test_so_campos_editaveis(self):
        f = self.acervo.editar("hk-greenpath", {"link": "https://youtu.be/hack", "id": "x", "comentario_pessoal": "linda"})
        self.assertEqual(f["link"], "https://www.youtube.com/watch?v=green")
        self.assertEqual(f["comentario_pessoal"], "linda")

    def test_faixa_que_nao_existe(self):
        with self.assertRaises(FaixaNaoEncontrada):
            self.acervo.editar("nada", {"temas": ["x"]})

    def test_editar_aprendida_muda_o_proprio_arquivo(self):
        nova = self.acervo.aprender("Taverna", "https://youtu.be/tav", ["alegre"])
        self.acervo.editar(nova["id"], {"temas": ["taverna", "alegre"]})
        self.assertEqual(self.acervo.aprendidas()[0]["temas"], ["taverna", "alegre"])
        self.assertEqual(self.acervo.ajustes(), {})

    def test_aprender_video_repetido(self):
        with self.assertRaises(service.MusicaJaNoDataset):
            self.acervo.aprender("x", "https://youtu.be/green", [])


class TestPlanilha(Base):
    def linhas(self, texto: str) -> list[dict]:
        return list(csv.DictReader(io.StringIO(texto.lstrip("﻿")), delimiter=";"))

    def test_exportar(self):
        texto = planilha.exportar(self.acervo)
        self.assertTrue(texto.startswith("﻿id;nome;franquia;link;temas;categorias;comentario"))
        linhas = self.linhas(texto)
        self.assertEqual(linhas[0]["temas"], "calmo, floresta")
        self.assertEqual(linhas[0]["franquia"], "Hollow Knight")

    def editar_e_comparar(self, mexer) -> planilha.Resumo:
        linhas = self.linhas(planilha.exportar(self.acervo))
        mexer(linhas)
        saida = io.StringIO()
        w = csv.DictWriter(saida, fieldnames=planilha.COLUNAS, delimiter=";")
        w.writeheader()
        w.writerows(linhas)
        return planilha.comparar(self.acervo, saida.getvalue())

    def test_ida_e_volta_sem_mexer_nao_muda_nada(self):
        r = self.editar_e_comparar(lambda linhas: None)
        self.assertEqual((r.mudancas, r.novas, r.ignoradas), ({}, [], []))

    def test_mudar_temas_e_aplicar(self):
        def mexer(linhas):
            linhas[1]["temas"] = "chefe; terror | sangue"
            linhas[1]["categorias"] = "isso aqui é ignorado"

        r = self.editar_e_comparar(mexer)
        self.assertEqual(r.mudancas, {"bb-cleric": {"temas": ["chefe", "terror", "sangue"]}})
        self.assertEqual(r.exemplos[0]["antes"], ["não classificado"])
        planilha.aplicar(self.acervo, r)
        self.assertEqual(self.faixa("bb-cleric")["temas"], ["chefe", "terror", "sangue"])

    def test_linha_nova_e_linhas_tortas(self):
        def mexer(linhas):
            vazio = dict.fromkeys(planilha.COLUNAS, "")
            linhas.append({**vazio, "nome": "Taverna", "link": "https://youtu.be/tav", "temas": "taverna"})
            linhas.append({**vazio, "nome": "Sem link", "temas": "x"})
            linhas.append({**vazio, "id": "inventado", "temas": "x"})
            linhas.append({**vazio, "nome": "Repetida", "link": "https://youtu.be/green"})
            linhas.append(vazio)  # em branco: some

        r = self.editar_e_comparar(mexer)
        self.assertEqual(r.novas, [("Taverna", "https://youtu.be/tav", ["taverna"])])
        self.assertEqual([i["linha"] for i in r.ignoradas], [5, 6, 7])
        planilha.aplicar(self.acervo, r)
        self.assertEqual(self.acervo.aprendidas()[0]["nome"], "Taverna")

    def test_apagar_linha_nao_apaga_faixa(self):
        r = self.editar_e_comparar(lambda linhas: linhas.pop(0))
        planilha.aplicar(self.acervo, r)
        self.assertEqual(len(self.acervo.faixas()), 2)

    def test_aceita_virgula_como_separador(self):
        texto = 'id,nome,temas\nbb-cleric,Cleric Beast,"chefe, terror"\n'
        self.assertEqual(planilha.comparar(self.acervo, texto).mudancas, {"bb-cleric": {"temas": ["chefe", "terror"]}})

    def test_planilha_sem_as_colunas(self):
        with self.assertRaises(ValueError):
            planilha.comparar(self.acervo, "a;b\n1;2\n")


if __name__ == "__main__":
    unittest.main()
