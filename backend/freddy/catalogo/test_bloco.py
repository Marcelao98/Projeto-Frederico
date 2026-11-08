"""Escolha do link oficial e da gravação do MusicBrainz (freddy.catalogo.bloco)."""

import unittest

from freddy.catalogo.bloco import escolher_gravacao, escolher_video


def v(titulo, canal, vid="x"):
    return {"title": titulo, "channel": canal, "id": vid, "duration": 200}


class TestEscolherVideo(unittest.TestCase):
    def test_prefere_topic_ao_clipe_e_ao_cover(self):
        videos = [
            v("Evidências - Cover no violão", "Fulano Covers", "cover"),
            v("Chitãozinho & Xororó - Evidências (Clipe Oficial)", "Chitãozinho e Xororó", "clipe"),
            v("Evidências", "Chitãozinho & Xororó - Topic", "topic"),
        ]
        escolhido, motivo = escolher_video("Chitãozinho & Xororó", "Evidências", videos)
        self.assertEqual(escolhido["id"], "topic")
        self.assertIn("Topic", motivo)

    def test_vevo(self):
        videos = [v("Queen - Bohemian Rhapsody (Official Video Remastered)", "Queen Official", "a"),
                  v("Bohemian Rhapsody", "QueenVEVO", "b")]
        escolhido, _ = escolher_video("Queen", "Bohemian Rhapsody", videos)
        self.assertEqual(escolhido["id"], "b")

    def test_sem_oficial_nao_escolhe(self):
        videos = [v("Garçom - Reginaldo Rossi (letra)", "Letras BR"), v("Garçom karaokê", "Karaokê Brasil")]
        escolhido, motivo = escolher_video("Reginaldo Rossi", "Garçom", videos)
        self.assertIsNone(escolhido)
        self.assertIn("nenhum", motivo)

    def test_ao_vivo_so_quando_pedido(self):
        videos = [v("Primeiros Erros (Chove) - Ao Vivo", "Capital Inicial - Topic", "vivo")]
        self.assertIsNone(escolher_video("Capital Inicial", "Primeiros Erros (Chove)", videos)[0])
        self.assertEqual(escolher_video("Capital Inicial", "Primeiros Erros (Chove)", videos, ao_vivo=True)[0]["id"], "vivo")

    def test_dupla_com_e_no_nome_do_canal(self):
        videos = [v("Pense em Mim", "Leandro e Leonardo - Topic", "t")]
        self.assertEqual(escolher_video("Leandro & Leonardo", "Pense em Mim", videos)[0]["id"], "t")

    def test_titulo_tem_que_bater(self):
        videos = [v("Outra Música", "Djavan - Topic")]
        self.assertIsNone(escolher_video("Djavan", "Oceano", videos)[0])


class TestEscolherGravacao(unittest.TestCase):
    def g(self, titulo, artista, data, score=100, gid="g"):
        return {"id": gid, "title": titulo, "score": score, "first-release-date": data,
                "artist-credit": [{"name": artista, "artist": {"name": artista}}]}

    def test_pega_o_lancamento_mais_antigo(self):
        grav = [self.g("Evidências", "Chitãozinho & Xororó", "2005-01-01", gid="coletanea"),
                self.g("Evidências", "Chitãozinho & Xororó", "1990-05-01", gid="original")]
        escolhida, _ = escolher_gravacao("Chitãozinho & Xororó", "Evidências", grav)
        self.assertEqual(escolhida["id"], "original")

    def test_ignora_outro_artista_e_nota_baixa(self):
        grav = [self.g("Evidências", "Banda Cover", "1985"), self.g("Evidências", "Chitãozinho & Xororó", "1990", score=50)]
        self.assertIsNone(escolher_gravacao("Chitãozinho & Xororó", "Evidências", grav)[0])

    def test_dois_artistas(self):
        grav = [self.g("Águas de Março", "Elis Regina", "1974")]
        self.assertIsNotNone(escolher_gravacao("Elis Regina & Tom Jobim", "Águas de Março", grav)[0])



class TestImportar(unittest.TestCase):
    """Um bloco pequeno, já 'conferido', passa pela importação e o catálogo compila."""

    def test_bloco_conferido_entra_e_compila(self):
        import csv
        import shutil
        import tempfile
        from pathlib import Path

        from freddy.catalogo.bloco import COLUNAS
        from freddy.catalogo.compilar import PASTA_CATALOGO, compilar
        from freddy.catalogo.importar import importar

        with tempfile.TemporaryDirectory() as tmp:
            cat = Path(tmp) / "catalogo"
            shutil.copytree(PASTA_CATALOGO, cat, ignore=shutil.ignore_patterns("blocos"))
            (cat / "blocos").mkdir()
            base = dict.fromkeys(COLUNAS, "")
            linhas = [
                {**base, "artista": "Chitãozinho & Xororó", "titulo": "Evidências", "ano": "1989",
                 "genero": "sertanejo-romantico", "idioma": "pt", "tem_voz": "1", "energia": "3", "animacao": "2",
                 "climas": "sofrido|romantico", "ocasioes": "karaoke", "temas": "amor", "popularidade": "98",
                 "essencial": "1", "canta_junto": "1", "explicita": "0", "ao_vivo": "0"},
                {**base, "artista": "Fulano", "titulo": "Sem Link", "ano": "2001", "genero": "pop",
                 "idioma": "pt", "tem_voz": "1", "energia": "3", "animacao": "3", "climas": "alegre|animado",
                 "popularidade": "10", "essencial": "0", "canta_junto": "0", "explicita": "0", "ao_vivo": "0"},
            ]

            def grava(nome, cab, rows):
                with open(cat / "blocos" / nome, "w", encoding="utf-8", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=cab, delimiter=";", lineterminator="\n")
                    w.writeheader()
                    w.writerows(rows)

            grava("bloco-02.csv", COLUNAS, linhas)
            grava("bloco-02.musicbrainz.csv", ["artista", "titulo", "ano_lista", "ano_mb", "confere", "mbid", "duracao", "motivo"],
                  [{"artista": "Chitãozinho & Xororó", "titulo": "Evidências", "ano_lista": "1989", "ano_mb": "1990",
                    "confere": "NÃO", "mbid": "abc", "duracao": "270", "motivo": ""}])
            grava("bloco-02.youtube.csv", ["artista", "titulo", "endereco", "canal", "oficial", "duracao", "motivo"],
                  [{"artista": "Chitãozinho & Xororó", "titulo": "Evidências", "endereco": "https://www.youtube.com/watch?v=x",
                    "canal": "Chitãozinho & Xororó - Topic", "oficial": "1", "duracao": "270", "motivo": "Topic"},
                   {"artista": "Fulano", "titulo": "Sem Link", "endereco": "", "canal": "", "oficial": "0",
                    "duracao": "", "motivo": "nenhum upload oficial nos resultados"}])

            rel = importar(cat)
            self.assertEqual(rel.por_bloco["bloco-02"]["entrou"], 1)
            self.assertEqual(len(rel.pendentes), 1)
            self.assertEqual(len(rel.anos_corrigidos), 1)
            r = compilar(cat, saida=Path(tmp) / "c.db")
            self.assertEqual(r.erros, [])
            importar(cat)  # de novo: não duplica
            with open(cat / "musicas.csv", encoding="utf-8") as f:
                novas = [m for m in csv.DictReader(f, delimiter=";") if m["lote"] == "bloco-02"]
            self.assertEqual([(m["titulo"], m["ano"]) for m in novas], [("Evidências", "1990")])


if __name__ == "__main__":
    unittest.main()
