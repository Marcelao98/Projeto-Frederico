"""O acervo: ler, ensinar faixa nova, corrigir faixa e a planilha (CSV)."""

from __future__ import annotations

from csv import Error as ErroDeCsv
from datetime import date

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from freddy.dados import planilha
from freddy.dados.acervo import FaixaNaoEncontrada
from freddy.dados.acervo_oficial import MusicaJaNoAcervo

rotas = APIRouter(prefix="/acervo")


class FaixaNova(BaseModel):
    titulo: str = Field(min_length=1, max_length=300)
    link: str = Field(min_length=1, max_length=2000)
    temas: list[str] = Field(default_factory=list, max_length=20)


class EdicaoDeFaixa(BaseModel):
    nome: str | None = Field(default=None, max_length=300)
    temas: list[str] | None = Field(default=None, max_length=30)
    comentario: str | None = Field(default=None, max_length=2000)


def _nome_da_planilha() -> str:
    return f"freddy-acervo-{date.today().isoformat()}.csv"


@rotas.get("")
def ler_acervo(request: Request):
    acervo = request.app.state.acervo
    return {"musicas": acervo.faixas(), "vocabulario": acervo.vocabulario()}


@rotas.post("/faixas", status_code=201)
def aprender(faixa: FaixaNova, request: Request):
    try:
        return request.app.state.acervo.aprender(faixa.titulo, faixa.link, faixa.temas)
    except MusicaJaNoAcervo as e:
        raise HTTPException(409, {"erro": "essa música já está no acervo", "faixa": e.musica}) from e


@rotas.patch("/faixas/{id_}")
def editar_faixa(id_: str, edicao: EdicaoDeFaixa, request: Request):
    campos = {"nome": edicao.nome, "temas": edicao.temas, "comentario_pessoal": edicao.comentario}
    try:
        return request.app.state.acervo.editar(id_, campos)
    except FaixaNaoEncontrada as e:
        raise HTTPException(404, "essa faixa não está no acervo") from e


@rotas.get("/planilha")
def baixar_planilha(request: Request):
    return Response(
        planilha.exportar(request.app.state.acervo),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{_nome_da_planilha()}"'},
    )


@rotas.post("/planilha/salvar")
def salvar_planilha(request: Request):
    destino = request.app.state.config.pasta_downloads / _nome_da_planilha()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(planilha.exportar(request.app.state.acervo), encoding="utf-8")
    return {"caminho": str(destino)}


@rotas.post("/planilha")
async def enviar_planilha(request: Request, aplicar: bool = False):
    corpo = await request.body()
    if len(corpo) > 5_000_000:
        raise HTTPException(413, "planilha grande demais")
    try:
        texto = corpo.decode("utf-8")
    except UnicodeDecodeError:
        texto = corpo.decode("latin-1")  # Excel antigo salva assim
    acervo = request.app.state.acervo
    try:
        resumo = planilha.comparar(acervo, texto)
    except (ValueError, ErroDeCsv) as e:
        raise HTTPException(400, f"não consegui ler a planilha: {e}") from e
    if aplicar:
        planilha.aplicar(acervo, resumo)
    return {**resumo.como_dict(), "aplicado": aplicar}
