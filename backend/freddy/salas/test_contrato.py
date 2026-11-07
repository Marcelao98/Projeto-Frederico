"""Roda os casos de casos_contrato.json no Motor do backend.

Os mesmos casos rodam no MotorLocal (frontend/src/motor/contrato.test.ts):
é isso que garante que o painel se comporta igual com os dois motores.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from freddy.audio.reprodutor_falso import ReprodutorFalso
from freddy.salas.motor import Motor

CASOS = json.loads((Path(__file__).parent / "casos_contrato.json").read_text(encoding="utf-8"))["casos"]


def musica(n: int) -> dict:
    return {"titulo": f"Música {n}", "link": f"https://youtu.be/v{n}"}


def expandir_musicas(spec) -> list[dict]:
    if isinstance(spec, dict):
        de, ate = spec["intervalo"]
        return [musica(n) for n in range(de, ate)]
    return [musica(x) if isinstance(x, int) else x for x in spec]


def resolver_uid(motor: Motor, valor: str) -> str:
    if valor == "$tocando":
        return motor.estado()["tocando"]["uid"]
    if valor.startswith("$proximas."):
        return motor.estado()["proximas"][int(valor.split(".")[1])]["uid"]
    return valor


def resumir_evento(e: dict) -> dict:
    r = {"tipo": e["tipo"]}
    if "musica" in e:
        r["titulo"] = e["musica"]["titulo"]
    if "motivo" in e:
        r["motivo"] = e["motivo"]
    return r


class TestContratoDoMotor(unittest.TestCase):
    def test_casos(self):
        for caso in CASOS:
            with self.subTest(caso["nome"]):
                self.rodar(caso)

    def rodar(self, caso: dict):
        r = ReprodutorFalso()
        motor = Motor(r)
        eventos: list[dict] = []
        motor.ao_evento(eventos.append)

        for i, passo in enumerate(caso["passos"]):
            onde = f"passo {i}: {passo}"
            if "executar" in passo:
                comando = dict(passo["executar"])
                if "musicas" in comando:
                    comando["musicas"] = expandir_musicas(comando["musicas"])
                if "uid" in comando:
                    comando["uid"] = resolver_uid(motor, comando["uid"])
                resultado = motor.executar(comando)
                if "resultado" in passo:
                    self.assertEqual(resultado, passo["resultado"], onde)
            elif "reprodutor" in passo:
                o = r.ouvinte
                acao = passo["reprodutor"]
                if acao in ("erro", "titulo"):
                    getattr(o, acao)(passo["arg"])
                else:
                    getattr(o, acao)()
            elif "estado" in passo:
                e = motor.estado()
                for chave, esperado in passo["estado"].items():
                    if chave == "tocando":
                        atual = e["tocando"]["titulo"] if e["tocando"] else None
                    elif chave == "proximas":
                        atual = [m["titulo"] for m in e["proximas"]]
                    else:
                        atual = e[chave]
                    self.assertEqual(atual, esperado, f"{onde} ({chave})")
            elif "eventos" in passo:
                self.assertEqual([resumir_evento(e) for e in eventos], passo["eventos"], onde)
            elif "carregados" in passo:
                self.assertEqual(r.carregados, [musica(n)["link"] for n in passo["carregados"]], onde)
            elif "volume_reprodutor" in passo:
                self.assertEqual(r.volume, passo["volume_reprodutor"], onde)
            else:
                self.fail(f"passo desconhecido: {onde}")


if __name__ == "__main__":
    unittest.main()
