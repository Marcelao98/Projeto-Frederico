"""O motor de som: guarda a fila e manda o Reprodutor tocar.

Porta fiel de frontend/src/motor/motorLocal.ts: os mesmos comandos, os
mesmos resultados, os mesmos eventos (o arquivo casos_contrato.json é rodado
pelos testes dos dois lados). Não sabe nada de rede: quem fala com o painel
é o freddy.api. Tudo roda numa thread só (a do servidor).
"""

from __future__ import annotations

from typing import Callable

from freddy.audio.reprodutor import Reprodutor
from freddy.motor import fila as F
from modules.bardo.service import VOLUME_PADRAO, limitar_volume

Ouvinte = Callable[[], None]
OuvinteEvento = Callable[[dict], None]


class ComandoInvalido(Exception):
    """Comando que o motor não conhece, ou sem os argumentos."""


class Motor:
    def __init__(self, reprodutor: Reprodutor):
        self.reprodutor = reprodutor
        self.fila: F.Fila = F.FILA_VAZIA
        self.situacao = "parado"
        self.volume = VOLUME_PADRAO
        self._prog = {"posicao": 0.0, "duracao": 0.0}
        self._ouvintes: list[Ouvinte] = []
        self._ouvintes_evento: list[OuvinteEvento] = []
        self._instantaneo = self._montar_estado()
        reprodutor.definir_volume(self.volume)
        reprodutor.ouvir(self._Ouvinte(self))

    class _Ouvinte:
        def __init__(self, motor: "Motor"):
            self.m = motor

        def tocando(self):
            self.m._mudar("tocando")

        def pausado(self):
            self.m._mudar("pausado")

        def fim(self):
            self.m._ao_terminar()

        def erro(self, motivo: str):
            self.m._ao_falhar(motivo)

        def titulo(self, titulo: str):
            self.m._ao_descobrir_titulo(titulo)

    # --- o que o servidor enxerga ------------------------------------------

    def estado(self) -> dict:
        return self._instantaneo

    def progresso(self) -> dict:
        return dict(self._prog)

    def inscrever(self, ouvinte: Ouvinte) -> Callable[[], None]:
        self._ouvintes.append(ouvinte)
        return lambda: self._ouvintes.remove(ouvinte)

    def ao_evento(self, ouvinte: OuvinteEvento) -> Callable[[], None]:
        self._ouvintes_evento.append(ouvinte)
        return lambda: self._ouvintes_evento.remove(ouvinte)

    def atualizar_progresso(self) -> bool:
        """Lê o relógio do reprodutor (o servidor chama 2x por segundo). True se mudou."""
        if self.fila.tocando is None:
            return False
        posicao = self.reprodutor.posicao()
        duracao = self.reprodutor.duracao() or self._prog["duracao"]
        if posicao == self._prog["posicao"] and duracao == self._prog["duracao"]:
            return False
        self._prog = {"posicao": posicao, "duracao": duracao}
        return True

    def executar(self, comando: dict) -> dict:
        tipo = comando.get("tipo")
        metodo = getattr(self, f"_cmd_{tipo}", None) if isinstance(tipo, str) else None
        if metodo is None:
            raise ComandoInvalido(f"comando desconhecido: {tipo!r}")
        try:
            return metodo(comando)
        except (KeyError, TypeError, ValueError) as e:
            raise ComandoInvalido(f"argumentos inválidos pra {tipo}: {e}") from e

    # --- comandos (os mesmos de Comandos, no tipos.ts) ---------------------

    def _cmd_adicionar(self, c: dict) -> dict:
        nada_tocava = self.fila.tocando is None
        onde = c.get("onde") or "fim"
        r = F.adicionar(self.fila, list(c["musicas"]), "fim" if nada_tocava and onde != "agora" else onde)
        if not r.entraram:
            return {"entraram": 0, "posicao": -1, "comecou": False}
        if nada_tocava or onde == "agora":
            self.fila = F.avancar(r.fila) if nada_tocava else r.fila
            self._tocar_atual()
            return {"entraram": r.entraram, "posicao": 0, "comecou": True}
        self._mudar_fila(r.fila)
        return {"entraram": r.entraram, "posicao": r.posicao, "comecou": False}

    def _cmd_pular(self, _c: dict) -> dict:
        if self.fila.tocando is None:
            return {"pulou": False, "temProxima": False, "repetiaAntes": False}
        # Pular é "chega dessa": desliga o repetir, senão a próxima também
        # entraria em loop sem ninguém pedir.
        repetia_antes = self.fila.repetir
        tem_proxima = len(self.fila.proximas) > 0
        self.fila = F.avancar(F.Fila(self.fila.tocando, self.fila.proximas, False))
        self._tocar_atual()
        if not tem_proxima:
            self._emitir({"tipo": "fila_acabou"})
        return {"pulou": True, "temProxima": tem_proxima, "repetiaAntes": repetia_antes}

    def _cmd_pausar(self, _c: dict) -> dict:
        if self.situacao not in ("tocando", "carregando"):
            return {"ok": False}
        self.reprodutor.pausar()
        self._mudar("pausado")
        return {"ok": True}

    def _cmd_continuar(self, _c: dict) -> dict:
        if self.situacao != "pausado":
            return {"ok": False}
        self.reprodutor.tocar()
        self._mudar("tocando")
        return {"ok": True}

    def _cmd_alternar_pausa(self, _c: dict) -> dict:
        return self._cmd_continuar({}) if self.situacao == "pausado" else self._cmd_pausar({})

    def _cmd_parar(self, _c: dict) -> dict:
        tinha = self.fila.tocando is not None
        self.fila = F.resetar()
        self._tocar_atual()
        return {"ok": tinha}

    def _cmd_limpar_fila(self, _c: dict) -> dict:
        removidas = len(self.fila.proximas)
        self._mudar_fila(F.limpar(self.fila))
        return {"removidas": removidas}

    def _cmd_repetir(self, c: dict) -> dict:
        ligar = c.get("ligar")
        repetir = (not self.fila.repetir) if ligar is None else bool(ligar)
        self._mudar_fila(F.Fila(self.fila.tocando, self.fila.proximas, repetir and self.fila.tocando is not None))
        return {"repetir": self.fila.repetir}

    def _cmd_volume(self, c: dict) -> dict:
        valor = c.get("valor")
        alvo = valor if valor is not None else self.volume + (c.get("delta") or 0)
        self.volume = limitar_volume(round(alvo))
        self.reprodutor.definir_volume(self.volume)
        self._mudar()
        return {"volume": self.volume}

    def _cmd_remover(self, c: dict) -> dict:
        antes = len(self.fila.proximas)
        self._mudar_fila(F.remover(self.fila, c["uid"]))
        return {"ok": len(self.fila.proximas) < antes}

    def _cmd_mover(self, c: dict) -> dict:
        self._mudar_fila(F.mover(self.fila, c["uid"], int(c["para"])))
        return {"ok": True}

    def _cmd_tocar_item(self, c: dict) -> dict:
        nova = F.tocar_item(self.fila, c["uid"])
        if nova is self.fila:
            return {"ok": False}
        self.fila = nova
        self._tocar_atual()
        return {"ok": True}

    def _cmd_embaralhar(self, _c: dict) -> dict:
        self._mudar_fila(F.embaralhar(self.fila))
        return {"ok": True}

    def _cmd_buscar_posicao(self, c: dict) -> dict:
        if self.fila.tocando is None:
            return {"ok": False}
        segundos = float(c["segundos"])
        self.reprodutor.buscar(segundos)
        self._prog = {**self._prog, "posicao": segundos}
        return {"ok": True}

    # --- tocar -------------------------------------------------------------

    def _tocar_atual(self) -> None:
        atual = self.fila.tocando
        self._prog = {"posicao": 0.0, "duracao": float((atual or {}).get("duracaoSegundos") or 0)}
        if atual is None:
            self.reprodutor.parar()
            self._mudar("parado")
            return
        self.reprodutor.carregar(atual["link"])
        self._mudar("carregando")

    def _ao_terminar(self) -> None:
        acabou = self.fila.tocando
        if acabou is None:
            return
        if self.fila.repetir:
            self.reprodutor.carregar(acabou["link"])
            self._mudar("carregando")
            return
        self._seguir_fila()

    def _ao_falhar(self, motivo: str) -> None:
        falhou = self.fila.tocando
        if falhou is None:
            return
        self._emitir({"tipo": "falha", "musica": falhou, "motivo": motivo})
        self.fila = F.Fila(self.fila.tocando, self.fila.proximas, False)
        self._seguir_fila()

    def _seguir_fila(self) -> None:
        self.fila = F.avancar(self.fila)
        self._tocar_atual()
        if self.fila.tocando is not None:
            self._emitir({"tipo": "tocando_agora", "musica": self.fila.tocando})
        else:
            self._emitir({"tipo": "fila_acabou"})

    def _ao_descobrir_titulo(self, titulo: str) -> None:
        """Link colado vem sem título; quando o reprodutor descobre, a fila mostra o certo."""
        atual = self.fila.tocando
        if atual is None or atual.get("faixaId") or not titulo or atual.get("titulo") == titulo:
            return
        self._mudar_fila(F.Fila({**atual, "titulo": titulo}, self.fila.proximas, self.fila.repetir))

    # --- estado ------------------------------------------------------------

    def _mudar_fila(self, fila: F.Fila) -> None:
        self.fila = fila
        self._mudar()

    def _mudar(self, situacao: str | None = None) -> None:
        if situacao:
            self.situacao = situacao
        self._instantaneo = self._montar_estado()
        for o in list(self._ouvintes):
            o()

    def _montar_estado(self) -> dict:
        return {
            "tocando": self.fila.tocando,
            "proximas": list(self.fila.proximas),
            "situacao": self.situacao,
            "repetir": self.fila.repetir,
            "volume": self.volume,
        }

    def _emitir(self, evento: dict) -> None:
        for o in list(self._ouvintes_evento):
            o(evento)
