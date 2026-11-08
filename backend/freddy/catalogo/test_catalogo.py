"""Catálogo novo: compila, confere as regras e roda os pedidos de ouro.

Pedidos de ouro (acervo/catalogo/pedidos_de_ouro.csv): cada frase diz o que
a consulta tem que entender (colunas 'entende') e, nas 10 primeiras músicas
de cada parte (partes separadas por ' > '), o que todas têm que ter ('deve')
e o que nenhuma pode ter com clareza ('nao_pode': marcação forte). Se o catálogo ainda não tem nenhuma
música que cumpra o 'deve' (pedidos de música geral antes da etapa 3), a
parte de resultado fica pendente; o 'entende' é conferido sempre.
"""

from __future__ import annotations

import csv
import re
import tempfile
import unittest
from pathlib import Path

from freddy.catalogo.compilar import PASTA_CATALOGO, carregar, compilar, conferir
from freddy.catalogo.consulta import Alvo, Catalogo

TOPO = 10


def _pedidos() -> list[dict]:
    with open(PASTA_CATALOGO / "pedidos_de_ouro.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _partes(campo: str, n: int) -> list[list[str]]:
    pedacos = [p.strip() for p in re.split(r"\s>\s?|^>\s|\s>$", campo)] if campo.strip() else []
    pedacos += [""] * (n - len(pedacos))
    return [[c for c in p.split("|") if c] for p in pedacos]


class TestCatalogo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.db = Path(cls._tmp.name) / "catalogo.db"
        cls.resultado = compilar(saida=cls.db)
        cls.cat = Catalogo(cls.db) if not cls.resultado.erros else None

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_compila_sem_erro(self):
        self.assertEqual(self.resultado.erros, [])

    def test_regras_pegam_musica_sem_clima(self):
        d = carregar()
        mid = next(m["id"] for m in d["musicas"] if m["revisar"] == "0")
        d["musica_tag"] = [l for l in d["musica_tag"] if l["musica"] != mid]
        self.assertTrue(any("menos de 2 climas" in e for e in conferir(d).erros))

    def test_regras_cobram_ano_e_fonte_oficial_fora_do_legado(self):
        d = carregar()
        m = next(m for m in d["musicas"] if not m["ano"])
        m["lote"] = "bloco-01"
        erros = conferir(d).erros
        self.assertTrue(any(m["id"] in e and "sem ano" in e for e in erros))
        self.assertTrue(any(m["id"] in e and "fonte oficial" in e for e in erros))

    def test_regras_pegam_giria_apontando_pro_nada(self):
        d = carregar()
        d["palavras"].append({"palavra": "xyz", "tipo": "genero", "alvo": "nao-existe", "peso": "1"})
        self.assertTrue(any("xyz" in e for e in conferir(d).erros))

    def test_toda_musica_do_acervo_migrou(self):
        import json
        from freddy.catalogo.compilar import RAIZ
        antigas = {m["id"] for m in json.loads((RAIZ / "acervo" / "musicas.json").read_text("utf-8"))["musicas"]}
        self.assertEqual(antigas, set(self.cat.musicas))

    def _cumpre(self, mid: str, cond: str, minimo: float = 0.0) -> bool:
        m = self.cat.musicas[mid]
        comp = re.fullmatch(r"(energia|animacao)(>=|<=)(\d)", cond)
        if comp:
            v = m[comp.group(1)]
            return v is not None and (v >= int(comp.group(3)) if comp.group(2) == ">=" else v <= int(comp.group(3)))
        tipo, alvo = cond.split(":", 1)
        return self.cat.forca(m, Alvo(tipo, alvo, 1.0)) > minimo

    def test_pedidos_de_ouro(self):
        pendentes = []
        for p in _pedidos():
            with self.subTest(pedido=p["id"], frase=p["frase"]):
                partes = self.cat.interpretar(p["frase"])
                esperado = _partes(p["entende"], len(partes))
                self.assertEqual(len(partes), max(len(esperado), 1), "número de partes")
                for parte, quer in zip(partes, esperado):
                    faltam = set(quer) - parte.alvos()
                    self.assertFalse(faltam, f"não entendeu {faltam}; entendeu {sorted(parte.alvos())}")
                respostas = self.cat.buscar(p["frase"], limite=TOPO)
                deves = _partes(p["deve"], len(respostas))
                naos = _partes(p["nao_pode"], len(respostas))
                for resp, deve, nao in zip(respostas, deves, naos):
                    existe = any(all(self._cumpre(mid, c) for c in deve) for mid in self.cat.musicas)
                    if deve and not existe:
                        pendentes.append(p["id"])
                        continue
                    ids = [a.musica for a in resp.achados]
                    self.assertTrue(ids, "não achou nada")
                    for mid in ids:
                        for c in deve:
                            self.assertTrue(self._cumpre(mid, c), f"{mid} não cumpre {c}")
                        for c in nao:
                            # 'não pode' = marcado com clareza (a curadoria), não um palpite fraco
                            self.assertFalse(self._cumpre(mid, c, 0.7), f"{mid} não podia ter {c}")
        self.__class__.pendentes = sorted(set(pendentes))


if __name__ == "__main__":
    unittest.main()
