"""Busca no acervo e vocabulário (freddy.nucleo.busca, freddy.nucleo.vocabulario)."""

import unittest

from freddy.dados.acervo_oficial import carregar
from freddy.nucleo.busca import MAX_RESULTADOS_DA_BUSCA, buscar_por_tags, sortear_da_busca
from freddy.nucleo.texto import extrair_link_youtube
from freddy.nucleo.vocabulario import carregar_vocabulario, categorias_dos_temas, montar_vocabulario

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


class TestBuscaBooleana(unittest.TestCase):
    def test_busca_por_tema_simples(self):
        r = buscar_por_tags("terror", dataset=_DATASET_TESTE)
        self.assertEqual([m["id"] for m in r], ["bloodborne-cleric-beast"])

    def test_busca_and_tema_e_origem(self):
        r = buscar_por_tags("calmo e hollow knight", dataset=_DATASET_TESTE)
        self.assertEqual([m["id"] for m in r], ["hollow-knight-greenpath"])

    def test_busca_and_nao_bate_quando_falta_um_termo(self):
        r = buscar_por_tags("terror e hollow knight", dataset=_DATASET_TESTE)
        self.assertEqual(r, [])

    def test_busca_or_junta_dois_grupos(self):
        r = buscar_por_tags("terror ou epico", dataset=_DATASET_TESTE)
        ids = {m["id"] for m in r}
        self.assertEqual(ids, {"bloodborne-cleric-beast", "hollow-knight-radiance"})

    def test_busca_negacao_com_sem(self):
        r = buscar_por_tags("bloodborne sem terror", dataset=_DATASET_TESTE)
        self.assertEqual([m["id"] for m in r], ["bloodborne-dream-refuge"])

    def test_busca_ignora_palavras_de_preenchimento(self):
        # "musica" e "de" não devem virar termo obrigatório que não bate com nada
        r = buscar_por_tags("uma musica de boss fight", dataset=_DATASET_TESTE)
        ids = {m["id"] for m in r}
        self.assertEqual(ids, {"bloodborne-cleric-beast", "hollow-knight-radiance"})

    def test_busca_ignora_acento_e_maiuscula(self):
        r = buscar_por_tags("ÉPICO", dataset=_DATASET_TESTE)
        self.assertEqual([m["id"] for m in r], ["hollow-knight-radiance"])

    def test_busca_por_nome_da_faixa(self):
        r = buscar_por_tags("greenpath", dataset=_DATASET_TESTE)
        self.assertEqual([m["id"] for m in r], ["hollow-knight-greenpath"])

    def test_busca_vazia_retorna_lista_vazia(self):
        self.assertEqual(buscar_por_tags("", dataset=_DATASET_TESTE), [])
        self.assertEqual(buscar_por_tags("musica de", dataset=_DATASET_TESTE), [])

    def test_busca_sem_resultado(self):
        self.assertEqual(buscar_por_tags("dark souls", dataset=_DATASET_TESTE), [])

    def test_or_tem_precedencia_menor_que_e(self):
        # "boss fight e bloodborne ou greenpath" = (boss fight e bloodborne) ou greenpath
        r = buscar_por_tags("boss fight e bloodborne ou greenpath", dataset=_DATASET_TESTE)
        self.assertEqual({m["id"] for m in r}, {"bloodborne-cleric-beast", "hollow-knight-greenpath"})


_VOCABULARIO_TESTE = montar_vocabulario({
    "categorias": {
        "triste": {"palavras": ["tristeza", "trágico", "melancólico"], "temas": ["vazio"]},
        "chefe": {"palavras": ["chefão", "boss fight"], "temas": []},
        "epico": {"palavras": ["grandioso"], "temas": ["coral"]},
    }
})


_DATASET_COM_CATEGORIAS = [
    dict(_DATASET_TESTE[0], temas=["boss fight", "trágico"], categorias=["chefe", "triste"]),
    dict(_DATASET_TESTE[3], temas=["boss fight", "coral"], categorias=["chefe", "epico"]),
]


def _ids(query: str) -> set[str]:
    return {m["id"] for m in buscar_por_tags(query, _DATASET_COM_CATEGORIAS, _VOCABULARIO_TESTE)}


class Sinonimos(unittest.TestCase):
    def test_vocabulario_monta_categorias_dos_temas(self):
        self.assertEqual(categorias_dos_temas(["Trágico", "coral", "piano"], _VOCABULARIO_TESTE), ["epico", "triste"])

    def test_sinonimo_acha_a_categoria(self):
        for query in ["triste", "tristeza", "melancolico", "tragico"]:
            with self.subTest(query=query):
                self.assertEqual(_ids(query), {"bloodborne-cleric-beast"})

    def test_tema_so_puxa_a_faixa_nao_a_categoria(self):
        # "coral" põe a faixa em "epico", mas quem busca "coral" não quer todo o épico.
        self.assertEqual(_ids("coral"), {"hollow-knight-radiance"})
        self.assertEqual(_ids("grandioso"), {"hollow-knight-radiance"})

    def test_frase_com_varias_palavras(self):
        self.assertEqual(_ids("chefao triste"), {"bloodborne-cleric-beast"})
        self.assertEqual(_ids("uma musica de chefao para chorar"), set())
        self.assertEqual(_ids("hollow knight"), {"hollow-knight-radiance"})

    def test_feminino_cai_na_mesma_categoria(self):
        vocabulario = montar_vocabulario({"categorias": {
            "alegre": {"palavras": ["animado"], "temas": []},
            "terror": {"palavras": ["assustador"], "temas": []},
        }})
        self.assertEqual(vocabulario.sinonimos["animada"], {"alegre"})
        self.assertEqual(vocabulario.sinonimos["assustadora"], {"terror"})
        self.assertEqual(categorias_dos_temas(["Animada"], vocabulario), ["alegre"])

    def test_negacao_com_sinonimo(self):
        self.assertEqual(_ids("chefao sem tristeza"), {"hollow-knight-radiance"})


class VocabularioReal(unittest.TestCase):
    def test_categorias_do_dataset_existem_no_vocabulario(self):
        vocabulario = carregar_vocabulario()
        conhecidas = {c for cats in vocabulario.por_tema.values() for c in cats}
        for m in carregar():
            with self.subTest(id=m["id"]):
                self.assertLessEqual(set(m.get("categorias", [])), conhecidas)

    def test_buscas_que_as_pessoas_fazem(self):
        for query in ["triste e bloodborne", "luta de chefe", "clima de taverna", "algo assustador", "masmorra"]:
            with self.subTest(query=query):
                self.assertTrue(buscar_por_tags(query, carregar()))


class SortearDaBusca(unittest.TestCase):
    def test_acha_e_conta(self):
        escolhidas, total = sortear_da_busca("greenpath", _DATASET_TESTE)
        self.assertEqual([m["nome"] for m in escolhidas], ["Greenpath"])
        self.assertEqual(total, 1)

    def test_sorteia_quando_acha_demais(self):
        dataset = [dict(_DATASET_TESTE[0], id=f"f{n}", nome=f"Faixa {n}") for n in range(MAX_RESULTADOS_DA_BUSCA + 5)]
        escolhidas, total = sortear_da_busca("terror", dataset)
        self.assertEqual(len(escolhidas), MAX_RESULTADOS_DA_BUSCA)
        self.assertEqual(total, MAX_RESULTADOS_DA_BUSCA + 5)
        self.assertEqual(len({m["id"] for m in escolhidas}), MAX_RESULTADOS_DA_BUSCA)

    def test_acervo_de_verdade(self):
        musicas = carregar()
        self.assertGreater(len(musicas), 0)
        for m in musicas:
            with self.subTest(id=m.get("id")):
                for campo in ("nome", "link", "origem", "temas"):
                    self.assertIn(campo, m)
                self.assertIsNotNone(extrair_link_youtube(m["link"]))


if __name__ == "__main__":
    unittest.main()
