"""O que é só do motor do backend (o contrato comum está em test_contrato.py)."""

from __future__ import annotations

import unittest

from freddy.audio.reprodutor_falso import ReprodutorFalso
from freddy.salas import fila as F
from freddy.salas.motor import ComandoInvalido, Motor


def m(n: int) -> dict:
    return {"titulo": f"Música {n}", "link": f"https://youtu.be/v{n}"}


class TestMotor(unittest.TestCase):
    def test_comando_desconhecido_ou_sem_argumento(self):
        motor = Motor(ReprodutorFalso())
        with self.assertRaises(ComandoInvalido):
            motor.executar({"tipo": "dançar"})
        with self.assertRaises(ComandoInvalido):
            motor.executar({"tipo": "remover"})
        with self.assertRaises(ComandoInvalido):
            motor.executar({})

    def test_avisa_quem_ouve_a_cada_mudanca(self):
        motor = Motor(ReprodutorFalso())
        avisos = []
        cancelar = motor.inscrever(lambda: avisos.append(motor.estado()["situacao"]))
        motor.executar({"tipo": "adicionar", "musicas": [m(1)]})
        self.assertEqual(avisos, ["carregando"])
        cancelar()
        motor.executar({"tipo": "parar"})
        self.assertEqual(avisos, ["carregando"])

    def test_estado_e_um_instantaneo(self):
        motor = Motor(ReprodutorFalso())
        antes = motor.estado()
        self.assertIs(motor.estado(), antes)
        motor.executar({"tipo": "volume", "valor": 10})
        self.assertIsNot(motor.estado(), antes)
        self.assertEqual(antes["volume"], 50)

    def test_progresso_le_o_relogio_do_reprodutor(self):
        r = ReprodutorFalso(simular=True, duracao_simulada=200, agendar=lambda f: None)
        motor = Motor(r)
        self.assertFalse(motor.atualizar_progresso())  # nada tocando
        motor.executar({"tipo": "adicionar", "musicas": [{**m(1), "duracaoSegundos": 200}]})
        self.assertEqual(motor.progresso(), {"posicao": 0.0, "duracao": 200.0})
        motor.executar({"tipo": "buscar_posicao", "segundos": 42})
        self.assertTrue(motor.atualizar_progresso() or motor.progresso()["posicao"] == 42)
        self.assertEqual(motor.progresso()["posicao"], 42)

    def test_reprodutor_simulado_avisa_que_tocou(self):
        pendentes = []
        motor = Motor(ReprodutorFalso(simular=True, duracao_simulada=0, agendar=pendentes.append))
        motor.executar({"tipo": "adicionar", "musicas": [m(1), m(2)]})
        self.assertEqual(motor.estado()["situacao"], "carregando")
        pendentes.pop(0)()
        self.assertEqual(motor.estado()["situacao"], "tocando")
        motor.atualizar_progresso()  # duração 0: já acabou
        pendentes.pop(0)()  # o aviso de fim da Música 1
        self.assertEqual(motor.estado()["tocando"]["titulo"], "Música 2")


class TestFila(unittest.TestCase):
    def test_uid_diferencia_a_mesma_musica(self):
        r = F.adicionar(F.FILA_VAZIA, [m(1), m(1)])
        a, b = r.fila.proximas
        self.assertNotEqual(a["uid"], b["uid"])

    def test_mover_limita_a_posicao(self):
        f = F.adicionar(F.FILA_VAZIA, [m(1), m(2), m(3)]).fila
        uid = f.proximas[0]["uid"]
        self.assertEqual([x["titulo"] for x in F.mover(f, uid, 99).proximas], ["Música 2", "Música 3", "Música 1"])
        self.assertEqual([x["titulo"] for x in F.mover(f, uid, -5).proximas], ["Música 1", "Música 2", "Música 3"])
        self.assertIs(F.mover(f, "nada", 0), f)

    def test_embaralhar_mantem_as_mesmas(self):
        f = F.adicionar(F.FILA_VAZIA, [m(n) for n in range(10)]).fila
        e = F.embaralhar(f, aleatorio=lambda: 0.0)
        self.assertCountEqual([x["uid"] for x in e.proximas], [x["uid"] for x in f.proximas])
        self.assertNotEqual([x["uid"] for x in e.proximas], [x["uid"] for x in f.proximas])


if __name__ == "__main__":
    unittest.main()
