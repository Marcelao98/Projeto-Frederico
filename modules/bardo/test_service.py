"""
Testes do serviço do Bardo (pedidos, fila, busca). Da raiz do projeto:
    python -m unittest discover -s modules/bardo -t .
"""

import os
import json
import shlex
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from modules.bardo.service import (  # noqa: E402
    MAX_FILA,
    NAO_CLASSIFICADO,
    SEGUNDOS_PARA_RESPONDER,
    MusicaJaNoDataset,
    adicionar_descoberta_ao_dataset,
    criar_pendencia,
    interpretar_resposta_de_pendencia,
    limpar_pendencia,
    pendencia_do_servidor,
    PASSO_VOLUME,
    Fila,
    FilaCheia,
    Musica,
    MAX_RESULTADOS_DA_BUSCA,
    Pedido,
    buscar_musicas,
    buscar_por_tags,
    carregar_dataset,
    carregar_vocabulario,
    categorias_dos_temas,
    chamou_a_natty,
    interpretar_pedido,
    extrair_link_youtube,
    montar_vocabulario,
    novo_volume,
    opcoes_ffmpeg,
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

    def test_sem_link_vira_busca(self):
        self.assertEqual(
            interpretar_pedido("natty toca triste e bloodborne"), Pedido("tocar", busca="triste e bloodborne")
        )
        self.assertEqual(interpretar_pedido("<@123> play boss fight!"), Pedido("tocar", busca="boss fight"))

    def test_sem_link_nem_busca(self):
        self.assertEqual(interpretar_pedido("natty toca"), Pedido("tocar"))

    def test_para_na_frase_nao_para(self):
        self.assertEqual(interpretar_pedido(f"natty toca essa para mim {LINK}"), Pedido("tocar", link=LINK))

    def test_para_na_frase_sem_link_nao_para(self):
        for texto in ["natty toca uma música para relaxar", "natty bota algo de taverna para o combate"]:
            with self.subTest(texto=texto):
                self.assertEqual(interpretar_pedido(texto).acao, "tocar")


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

    def test_adicionar_varias_ate_o_limite(self):
        fila = Fila()
        fila.adicionar(_musica(0))
        self.assertEqual(fila.adicionar_varias([_musica(n) for n in range(1, MAX_FILA + 5)]), MAX_FILA - 1)
        self.assertEqual(len(fila.proximas), MAX_FILA)
        self.assertEqual(fila.adicionar_varias([_musica(999)]), 0)


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
        for m in carregar_dataset():
            with self.subTest(id=m["id"]):
                self.assertLessEqual(set(m.get("categorias", [])), conhecidas)

    def test_buscas_que_as_pessoas_fazem(self):
        for query in ["triste e bloodborne", "luta de chefe", "clima de taverna", "algo assustador", "masmorra"]:
            with self.subTest(query=query):
                self.assertTrue(buscar_por_tags(query))


class BuscarMusicas(unittest.TestCase):
    def test_vira_musica_da_fila(self):
        musicas, achadas = buscar_musicas("greenpath", dataset=_DATASET_TESTE)
        self.assertEqual(musicas, [Musica("Greenpath", "https://www.youtube.com/watch?v=ccc")])
        self.assertEqual(achadas, 1)

    def test_sorteia_quando_acha_demais(self):
        dataset = [dict(_DATASET_TESTE[0], nome=f"Faixa {n}") for n in range(MAX_RESULTADOS_DA_BUSCA + 5)]
        musicas, achadas = buscar_musicas("terror", dataset=dataset)
        self.assertEqual(len(musicas), MAX_RESULTADOS_DA_BUSCA)
        self.assertEqual(achadas, MAX_RESULTADOS_DA_BUSCA + 5)
        self.assertEqual(len(set(musicas)), MAX_RESULTADOS_DA_BUSCA)

    def test_dataset_de_producao(self):
        musicas = carregar_dataset()
        self.assertGreater(len(musicas), 0)
        for m in musicas:
            with self.subTest(id=m.get("id")):
                for campo in ("nome", "link", "origem", "temas"):
                    self.assertIn(campo, m)
                self.assertIsNotNone(extrair_link_youtube(m["link"]))



class RespostaDaPendencia(unittest.TestCase):
    def test_nao_descarta(self):
        for texto in ["não", "Não é essa", "nao, errou", "natty, não era essa não"]:
            with self.subTest(texto=texto):
                self.assertIsNone(interpretar_resposta_de_pendencia(texto))

    def test_temas_separados_por_virgula_e_e(self):
        self.assertEqual(interpretar_resposta_de_pendencia("sim, é triste e épico"), ["triste", "épico"])
        self.assertEqual(
            interpretar_resposta_de_pendencia("Taverna, animado e boss fight"), ["taverna", "animado", "boss fight"]
        )

    def test_chamando_a_natty_antes(self):
        # A resposta só conta se chamar a Natty; o nome dela não vira tema.
        self.assertEqual(interpretar_resposta_de_pendencia("natty, é taverna e animado"), ["taverna", "animado"])
        self.assertEqual(interpretar_resposta_de_pendencia("ei natty sim, triste"), ["triste"])
        self.assertEqual(interpretar_resposta_de_pendencia("<@123> épico"), ["épico"])
        self.assertIsNone(interpretar_resposta_de_pendencia("natty, não"))
        # ...e o cog só trata como resposta o que não é pedido de música.
        for texto in ["natty, é taverna e animado", "ei natty sim, triste", "natty, não"]:
            with self.subTest(texto=texto):
                self.assertIsNone(interpretar_pedido(texto))

    def test_so_confirmacao_vira_lista_vazia(self):
        for texto in ["sim", "é essa mesmo!", "isso aí 🎉", "<@123> sim"]:
            with self.subTest(texto=texto):
                self.assertEqual(interpretar_resposta_de_pendencia(texto), [])

    def test_nao_repete_nem_passa_do_limite(self):
        temas = interpretar_resposta_de_pendencia("triste, triste, calmo, épico, sombrio, terror, tenso")
        self.assertEqual(temas, ["triste", "calmo", "épico", "sombrio", "terror"])

    def test_rolagem_nao_vira_tema(self):
        self.assertEqual(interpretar_resposta_de_pendencia("1d20+5"), [])


class Pendencia(unittest.TestCase):
    def tearDown(self):
        limpar_pendencia(1)

    def test_abre_e_limpa(self):
        criar_pendencia(1, "Música", LINK, canal_id=9, agora=0)
        self.assertEqual(pendencia_do_servidor(1, agora=10)["link"], LINK)
        limpar_pendencia(1)
        self.assertIsNone(pendencia_do_servidor(1, agora=10))

    def test_vence_depois_do_prazo(self):
        criar_pendencia(1, "Música", LINK, agora=0)
        self.assertIsNone(pendencia_do_servidor(1, agora=SEGUNDOS_PARA_RESPONDER + 1))
        # venceu = limpou: nem voltando no tempo ela reaparece
        self.assertIsNone(pendencia_do_servidor(1, agora=0))


class AdicionarDescoberta(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.arquivo = Path(pasta.name) / "musicas.json"
        self.arquivo.write_text(
            json.dumps({"_comentario": "teste", "musicas": [_DATASET_TESTE[2]]}, ensure_ascii=False), encoding="utf-8"
        )

    def _musicas(self):
        return json.loads(self.arquivo.read_text(encoding="utf-8"))["musicas"]

    def test_grava_com_temas_e_categorias(self):
        entrada = adicionar_descoberta_ao_dataset("Bard's Song", LINK, ["triste"], caminho=self.arquivo)
        self.assertEqual(entrada["id"], "descoberta-em-mesa-bards-song")
        self.assertEqual(entrada["origem"], {"nome": "Descoberta em mesa", "tipo": "outro"})
        self.assertIn("triste", entrada["categorias"])
        self.assertEqual(self._musicas()[-1], entrada)

    def test_sem_temas_vira_nao_classificado(self):
        entrada = adicionar_descoberta_ao_dataset("Bard's Song", LINK, [], caminho=self.arquivo)
        self.assertEqual(entrada["temas"], [NAO_CLASSIFICADO])

    def test_nao_duplica_pelo_link(self):
        adicionar_descoberta_ao_dataset("Bard's Song", LINK, ["triste"], caminho=self.arquivo)
        with self.assertRaises(MusicaJaNoDataset):
            adicionar_descoberta_ao_dataset("Outro título", "https://youtu.be/dQw4w9WgXcQ?t=5", [], caminho=self.arquivo)
        # nem se já estava no dataset desde antes
        with self.assertRaises(MusicaJaNoDataset):
            adicionar_descoberta_ao_dataset("Greenpath", _DATASET_TESTE[2]["link"], [], caminho=self.arquivo)
        self.assertEqual(len(self._musicas()), 2)

    def test_id_repetido_ganha_sufixo(self):
        adicionar_descoberta_ao_dataset("Tema", LINK, [], caminho=self.arquivo)
        entrada = adicionar_descoberta_ao_dataset("Tema", "https://www.youtube.com/watch?v=outro", [], caminho=self.arquivo)
        self.assertEqual(entrada["id"], "descoberta-em-mesa-tema-2")


class OpcoesFFmpeg(unittest.TestCase):
    def test_sem_headers(self):
        self.assertNotIn("-headers", opcoes_ffmpeg()["before_options"])

    def test_headers_sobrevivem_ao_shlex_do_discord(self):
        # discord.py quebra before_options com shlex.split; o User-Agent tem espaços e ';'.
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux) Firefox/1.0", "Accept": "*/*"}
        args = shlex.split(opcoes_ffmpeg(headers)["before_options"])
        self.assertEqual(args[:6], ["-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5"])
        self.assertEqual(
            args[args.index("-headers") + 1], "User-Agent: Mozilla/5.0 (X11; Linux) Firefox/1.0\r\nAccept: */*\r\n"
        )


if __name__ == "__main__":
    unittest.main()
