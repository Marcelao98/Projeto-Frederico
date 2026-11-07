"""O acervo oficial (freddy.dados.acervo_oficial): acrescentar faixa descoberta."""

import json
import tempfile
import unittest
from pathlib import Path

from freddy.dados.acervo_oficial import MusicaJaNoAcervo, adicionar_descoberta
from freddy.nucleo.vocabulario import NAO_CLASSIFICADO

LINK = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
GREENPATH = {
    "id": "hollow-knight-greenpath",
    "nome": "Greenpath",
    "link": "https://www.youtube.com/watch?v=ccc",
    "escopo": "faixa_individual",
    "origem": {"nome": "Hollow Knight", "tipo": "jogo"},
    "temas": ["exploração", "sereno", "calmo"],
    "comentario_pessoal": "",
}


class AdicionarDescoberta(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.arquivo = Path(pasta.name) / "musicas.json"
        self.arquivo.write_text(
            json.dumps({"_comentario": "teste", "musicas": [GREENPATH]}, ensure_ascii=False), encoding="utf-8"
        )

    def _musicas(self):
        return json.loads(self.arquivo.read_text(encoding="utf-8"))["musicas"]

    def test_grava_com_temas_e_categorias(self):
        entrada = adicionar_descoberta("Bard's Song", LINK, ["triste"], caminho=self.arquivo)
        self.assertEqual(entrada["id"], "descoberta-em-mesa-bards-song")
        self.assertEqual(entrada["origem"], {"nome": "Descoberta em mesa", "tipo": "outro"})
        self.assertIn("triste", entrada["categorias"])
        self.assertEqual(self._musicas()[-1], entrada)

    def test_sem_temas_vira_nao_classificado(self):
        entrada = adicionar_descoberta("Bard's Song", LINK, [], caminho=self.arquivo)
        self.assertEqual(entrada["temas"], [NAO_CLASSIFICADO])

    def test_nao_duplica_pelo_link(self):
        adicionar_descoberta("Bard's Song", LINK, ["triste"], caminho=self.arquivo)
        with self.assertRaises(MusicaJaNoAcervo):
            adicionar_descoberta("Outro título", "https://youtu.be/dQw4w9WgXcQ?t=5", [], caminho=self.arquivo)
        # nem se já estava no acervo desde antes
        with self.assertRaises(MusicaJaNoAcervo):
            adicionar_descoberta("Greenpath", GREENPATH["link"], [], caminho=self.arquivo)
        self.assertEqual(len(self._musicas()), 2)

    def test_id_repetido_ganha_sufixo(self):
        adicionar_descoberta("Tema", LINK, [], caminho=self.arquivo)
        entrada = adicionar_descoberta("Tema", "https://www.youtube.com/watch?v=outro", [], caminho=self.arquivo)
        self.assertEqual(entrada["id"], "descoberta-em-mesa-tema-2")


if __name__ == "__main__":
    unittest.main()
