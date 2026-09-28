"""
Testes do serviço do Bardo. Da raiz do projeto:
    python -m unittest discover -s modules/bardo -t .
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from modules.bardo import service  # noqa: E402

_DATASET_TESTE = [
    {
        "id": "bloodborne-cleric-beast",
        "nome": "Cleric Beast",
        "link": "https://www.youtube.com/watch?v=aaa",
        "escopo": "faixa_individual",
        "origem": {"nome": "Bloodborne", "tipo": "jogo"},
        "temas": ["boss fight", "terror", "opressivo"],
        "comentario_pessoal": "",
    },
    {
        "id": "bloodborne-dream-refuge",
        "nome": "Dream Refuge (Character Creation)",
        "link": "https://www.youtube.com/watch?v=bbb",
        "escopo": "faixa_individual",
        "origem": {"nome": "Bloodborne", "tipo": "jogo"},
        "temas": ["calmo", "hub", "atmosférico"],
        "comentario_pessoal": "",
    },
    {
        "id": "hollow-knight-greenpath",
        "nome": "Greenpath",
        "link": "https://www.youtube.com/watch?v=ccc",
        "escopo": "faixa_individual",
        "origem": {"nome": "Hollow Knight", "tipo": "jogo"},
        "temas": ["exploração", "sereno", "calmo"],
        "comentario_pessoal": "",
    },
    {
        "id": "hollow-knight-radiance",
        "nome": "Radiance (Final Boss)",
        "link": "https://www.youtube.com/watch?v=ddd",
        "escopo": "faixa_individual",
        "origem": {"nome": "Hollow Knight", "tipo": "jogo"},
        "temas": ["boss fight", "épico", "coral"],
        "comentario_pessoal": "",
    },
]


class TestGatilhoEBusca(unittest.TestCase):
    def test_extrai_texto_de_busca_remove_gatilho(self):
        self.assertEqual(service.extrair_texto_de_busca("toca triste e bloodborne"), "triste e bloodborne")
        self.assertEqual(service.extrair_texto_de_busca("PLAY boss fight"), "boss fight")

    def test_extrai_texto_de_busca_sem_gatilho(self):
        # não deveria acontecer na prática (cog.py só chama isso depois de
        # confirmar eh_pedido_de_musica), mas não deve quebrar.
        self.assertEqual(service.extrair_texto_de_busca("bloodborne triste"), "bloodborne triste")


class TestBuscaBooleana(unittest.TestCase):
    def test_busca_por_tema_simples(self):
        r = service.buscar_por_tags("terror", dataset=_DATASET_TESTE)
        self.assertEqual([m["id"] for m in r], ["bloodborne-cleric-beast"])

    def test_busca_and_tema_e_origem(self):
        r = service.buscar_por_tags("calmo e hollow knight", dataset=_DATASET_TESTE)
        self.assertEqual([m["id"] for m in r], ["hollow-knight-greenpath"])

    def test_busca_and_nao_bate_quando_falta_um_termo(self):
        r = service.buscar_por_tags("terror e hollow knight", dataset=_DATASET_TESTE)
        self.assertEqual(r, [])

    def test_busca_or_junta_dois_grupos(self):
        r = service.buscar_por_tags("terror ou epico", dataset=_DATASET_TESTE)
        ids = {m["id"] for m in r}
        self.assertEqual(ids, {"bloodborne-cleric-beast", "hollow-knight-radiance"})

    def test_busca_negacao_com_sem(self):
        r = service.buscar_por_tags("bloodborne sem terror", dataset=_DATASET_TESTE)
        self.assertEqual([m["id"] for m in r], ["bloodborne-dream-refuge"])

    def test_busca_ignora_palavras_de_preenchimento(self):
        # "musica" e "de" não devem virar termo obrigatório que não bate com nada
        r = service.buscar_por_tags("uma musica de boss fight", dataset=_DATASET_TESTE)
        ids = {m["id"] for m in r}
        self.assertEqual(ids, {"bloodborne-cleric-beast", "hollow-knight-radiance"})

    def test_busca_ignora_acento_e_maiuscula(self):
        r = service.buscar_por_tags("ÉPICO", dataset=_DATASET_TESTE)
        self.assertEqual([m["id"] for m in r], ["hollow-knight-radiance"])

    def test_busca_por_nome_da_faixa(self):
        r = service.buscar_por_tags("greenpath", dataset=_DATASET_TESTE)
        self.assertEqual([m["id"] for m in r], ["hollow-knight-greenpath"])

    def test_busca_vazia_retorna_lista_vazia(self):
        self.assertEqual(service.buscar_por_tags("", dataset=_DATASET_TESTE), [])
        self.assertEqual(service.buscar_por_tags("musica de", dataset=_DATASET_TESTE), [])

    def test_busca_sem_resultado(self):
        self.assertEqual(service.buscar_por_tags("dark souls", dataset=_DATASET_TESTE), [])


class TestFila(unittest.TestCase):
    def setUp(self):
        # cada teste usa um guild_id diferente pra não vazar estado entre eles,
        # já que _filas é um dict de módulo (deliberado — é o estado real em produção).
        self._guild_id = id(self)

    def test_fila_vazia_no_inicio(self):
        self.assertEqual(service.ver_fila(self._guild_id), [])
        self.assertIsNone(service.proxima_da_fila(self._guild_id))

    def test_adicionar_e_tirar_da_fila_e_fifo(self):
        service.adicionar_na_fila(self._guild_id, {"id": "a"})
        service.adicionar_na_fila(self._guild_id, {"id": "b"})
        self.assertEqual(service.proxima_da_fila(self._guild_id), {"id": "a"})
        self.assertEqual(service.proxima_da_fila(self._guild_id), {"id": "b"})
        self.assertIsNone(service.proxima_da_fila(self._guild_id))

    def test_adicionar_varias_na_fila(self):
        service.adicionar_varias_na_fila(self._guild_id, [{"id": "x"}, {"id": "y"}])
        self.assertEqual(service.ver_fila(self._guild_id), [{"id": "x"}, {"id": "y"}])

    def test_limpar_fila(self):
        service.adicionar_na_fila(self._guild_id, {"id": "a"})
        service.limpar_fila(self._guild_id)
        self.assertEqual(service.ver_fila(self._guild_id), [])

    def test_filas_de_servidores_diferentes_nao_se_misturam(self):
        outro_guild_id = self._guild_id + 1
        service.adicionar_na_fila(self._guild_id, {"id": "a"})
        service.adicionar_na_fila(outro_guild_id, {"id": "b"})
        self.assertEqual(service.ver_fila(self._guild_id), [{"id": "a"}])
        self.assertEqual(service.ver_fila(outro_guild_id), [{"id": "b"}])


class TestCarregarDatasetReal(unittest.TestCase):
    def test_dataset_de_producao_carrega_sem_erro(self):
        musicas = service.carregar_dataset()
        self.assertGreater(len(musicas), 0)
        # confere que toda entrada tem os campos que a busca depende
        for m in musicas[:5]:
            self.assertIn("nome", m)
            self.assertIn("origem", m)
            self.assertIn("temas", m)


if __name__ == "__main__":
    unittest.main()
