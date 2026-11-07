"""Pra onde o som da Mesa vai: a caixa de som, a call do Discord, nada (testes).
Depois: o mic virtual. Cada saída puxa os quadros no ritmo dela; com o
Discord ligado, ele manda no ritmo e a caixa toca a cópia (Mesa.ler_para_local)."""

from __future__ import annotations

from typing import Protocol


class Saida(Protocol):
    nome: str

    def comecar(self) -> None: ...
    def fechar(self) -> None: ...
