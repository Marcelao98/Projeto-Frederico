"""As mensagens do WebSocket /ws. O contrato é o de frontend/src/motor/tipos.ts.

Painel → Freddy:
    {"tipo": "comando", "id": 7, "comando": {"tipo": "adicionar", "musicas": [...], "onde": "fim"}}
    {"tipo": "ping"}
Freddy → painel:
    {"tipo": "ola", "protocolo": 1, "versao": "0.2.0", "som": "local"}   ao conectar
    {"tipo": "estado", "estado": {tocando, proximas, situacao, repetir, volume}}   a cada mudança
    {"tipo": "progresso", "posicao": 42.5, "duracao": 210}   2x por segundo, tocando
    {"tipo": "evento", "evento": {"tipo": "tocando_agora", "musica": {...}}}
    {"tipo": "resposta", "id": 7, "ok": true, "resultado": {...}}
    {"tipo": "resposta", "id": 7, "ok": false, "erro": "..."}
    {"tipo": "pong"}
    {"tipo": "discord", "discord": {...}}   o bot (o mesmo de GET /discord), a cada mudança
Os nomes dos campos são os do TypeScript (faixaId, temProxima...), sem conversão.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class Musica(BaseModel):
    model_config = ConfigDict(extra="ignore")
    titulo: str = Field(min_length=1, max_length=300)
    link: str = Field(min_length=1, max_length=2000)
    faixaId: str | None = None
    origem: str | None = None
    duracaoSegundos: float | None = Field(default=None, ge=0)


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Adicionar(_Base):
    tipo: Literal["adicionar"]
    musicas: list[Musica] = Field(max_length=500)
    onde: Literal["fim", "proxima", "agora"] | None = None


class SemArgumento(_Base):
    tipo: Literal["pular", "pausar", "continuar", "alternar_pausa", "parar", "limpar_fila", "embaralhar"]


class Repetir(_Base):
    tipo: Literal["repetir"]
    ligar: bool | None = None


class Volume(_Base):
    tipo: Literal["volume"]
    valor: float | None = None
    delta: float | None = None


class PorUid(_Base):
    tipo: Literal["remover", "tocar_item"]
    uid: str


class Mover(_Base):
    tipo: Literal["mover"]
    uid: str
    para: int


class BuscarPosicao(_Base):
    tipo: Literal["buscar_posicao"]
    segundos: float = Field(ge=0)


Comando = Annotated[
    Union[Adicionar, SemArgumento, Repetir, Volume, PorUid, Mover, BuscarPosicao],
    Field(discriminator="tipo"),
]
_validar = TypeAdapter(Comando)


def validar_comando(bruto: object) -> dict:
    """O comando como dict pro Motor. Levanta pydantic.ValidationError se vier torto."""
    return _validar.validate_python(bruto).model_dump(exclude_none=True)


def descrever_erro(e: Exception) -> str:
    from pydantic import ValidationError

    if isinstance(e, ValidationError):
        primeiro = e.errors()[0]
        local = ".".join(str(p) for p in primeiro.get("loc", ()))
        return f"comando inválido ({local}: {primeiro.get('msg')})"
    return str(e)
