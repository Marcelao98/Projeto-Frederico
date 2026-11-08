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


if __name__ == "__main__":
    unittest.main()
