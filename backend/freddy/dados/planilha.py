"""O acervo como planilha (CSV), pra arrumar muita faixa de uma vez.

Baixa, abre no LibreOffice ou no Excel, mexe na coluna `temas` (ou no nome,
ou no comentário), salva como CSV e manda de volta. Antes de aplicar, o
Freddy mostra o resumo do que vai mudar.

- Separador `;` e acentos com BOM: o Excel brasileiro abre direto.
- `temas` separados por vírgula: "taverna, alegre, calmo".
- `categorias` é só pra consulta (sai dos temas); mudar ali não faz nada.
- Linha sem `id` mas com link do YouTube vira faixa nova.
- Apagar a linha NÃO apaga a faixa: ninguém perde o acervo sem querer.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field

from freddy.dados.acervo import Acervo, limpar_temas
from freddy.nucleo.texto import extrair_link_youtube, video_id

COLUNAS = ("id", "nome", "franquia", "link", "temas", "categorias", "comentario")
_SEPARADOR_DE_TEMAS = re.compile(r"\s*[,;|/]\s*")


def separar_temas(texto: str) -> list[str]:
    return limpar_temas([t for t in _SEPARADOR_DE_TEMAS.split(texto or "") if t.strip()])


def exportar(acervo: Acervo) -> str:
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", lineterminator="\r\n")
    escritor.writerow(COLUNAS)
    for f in acervo.faixas():
        escritor.writerow(
            [
                f["id"],
                f["nome"],
                f["origem"]["nome"],
                f["link"],
                ", ".join(f.get("temas", [])),
                ", ".join(f.get("categorias", [])),
                f.get("comentario_pessoal", ""),
            ]
        )
    return "﻿" + saida.getvalue()


@dataclass
class Resumo:
    mudancas: dict[str, dict] = field(default_factory=dict)  # id → campos novos
    novas: list[tuple[str, str, list[str]]] = field(default_factory=list)  # (nome, link, temas)
    ignoradas: list[dict] = field(default_factory=list)  # {linha, motivo}
    exemplos: list[dict] = field(default_factory=list)  # algumas mudanças, pra tela mostrar

    def como_dict(self) -> dict:
        return {
            "mudaram": len(self.mudancas),
            "novas": len(self.novas),
            "ignoradas": self.ignoradas[:50],
            "totalIgnoradas": len(self.ignoradas),
            "exemplos": self.exemplos[:20],
        }


def _ler(texto: str) -> list[dict]:
    texto = texto.lstrip("﻿")
    primeira = texto.split("\n", 1)[0]
    delimitador = ";" if primeira.count(";") >= primeira.count(",") else ","
    leitor = csv.DictReader(io.StringIO(texto), delimiter=delimitador)
    if not leitor.fieldnames:
        raise ValueError("a planilha está vazia")
    leitor.fieldnames = [(c or "").strip().lower() for c in leitor.fieldnames]
    faltando = {"id", "temas"} - set(leitor.fieldnames)
    if faltando:
        raise ValueError(f"faltam as colunas: {', '.join(sorted(faltando))} (baixe a planilha do Freddy e edite ela)")
    return list(leitor)


def comparar(acervo: Acervo, texto: str) -> Resumo:
    """O que a planilha muda no acervo (sem gravar nada)."""
    linhas = _ler(texto)
    atuais = {f["id"]: f for f in acervo.faixas()}
    videos = {video_id(f["link"]) for f in atuais.values()}
    resumo = Resumo()
    for n, linha in enumerate(linhas, start=2):  # linha 1 é o cabeçalho
        id_ = (linha.get("id") or "").strip()
        nome = (linha.get("nome") or "").strip()
        temas = separar_temas(linha.get("temas") or "")
        if not id_:
            link = extrair_link_youtube(linha.get("link") or "")
            if not link and not nome and not temas:
                continue  # linha em branco
            if not link:
                resumo.ignoradas.append({"linha": n, "motivo": "sem id e sem link do YouTube"})
            elif video_id(link) in videos:
                resumo.ignoradas.append({"linha": n, "motivo": "esse vídeo já está no acervo"})
            elif not nome:
                resumo.ignoradas.append({"linha": n, "motivo": "faixa nova sem nome"})
            else:
                videos.add(video_id(link))
                resumo.novas.append((nome, link, temas))
            continue
        atual = atuais.get(id_)
        if atual is None:
            resumo.ignoradas.append({"linha": n, "motivo": f"não conheço o id {id_!r}"})
            continue
        campos: dict = {}
        if temas and temas != atual.get("temas"):
            campos["temas"] = temas
        if nome and nome != atual["nome"]:
            campos["nome"] = nome
        if "comentario" in linha and (linha["comentario"] or "").strip() != (atual.get("comentario_pessoal") or ""):
            campos["comentario_pessoal"] = (linha["comentario"] or "").strip()
        if campos:
            resumo.mudancas[id_] = campos
            if len(resumo.exemplos) < 20:
                resumo.exemplos.append(
                    {"id": id_, "nome": atual["nome"], "antes": atual.get("temas", []), "depois": campos.get("temas", atual.get("temas", []))}
                )
    return resumo


def aplicar(acervo: Acervo, resumo: Resumo) -> None:
    if resumo.mudancas:
        acervo.editar_varias(resumo.mudancas)
    if resumo.novas:
        acervo.aprender_varias(resumo.novas)
