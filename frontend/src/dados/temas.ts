/**
 * As plumagens (temas). As cores moram em src/temas.css, uma regra
 * [data-tema="..."] por tema; aqui só a lista e a troca.
 * Pra criar um tema: um bloco novo no temas.css e uma linha aqui.
 */

import { criarArmazem } from "./armazem";

export interface Tema {
  id: string;
  nome: string;
  descricao: string;
  claro: boolean;
}

export const TEMAS: Tema[] = [
  { id: "albina", nome: "Albina", descricao: "Branca de olho rubi, o Frederico de verdade", claro: true },
  { id: "lutino", nome: "Lutino", descricao: "Creme e amarela, bochecha laranja", claro: true },
  { id: "cinza", nome: "Cinza silvestre", descricao: "A calopsita clássica, de noite", claro: false },
  { id: "canela", nome: "Canela", descricao: "Castanha e quente", claro: false },
  { id: "cara-branca", nome: "Cara-branca", descricao: "Cinza e branca, sem amarelo", claro: false },
];

export const TEMA_PADRAO = "albina";
/** A mesma chave que o script do index.html lê, pra não piscar o tema errado. */
export const CHAVE_DO_TEMA = "freddy.tema";

export const temaAtual = criarArmazem<string>(TEMA_PADRAO, CHAVE_DO_TEMA);

export function aplicarTema(id: string) {
  const tema = TEMAS.find((t) => t.id === id) ?? TEMAS[0];
  document.documentElement.dataset.tema = tema.id;
  document.querySelector('meta[name="color-scheme"]')?.setAttribute("content", tema.claro ? "light" : "dark");
}

export function proximoTema(id: string): string {
  const i = TEMAS.findIndex((t) => t.id === id);
  return TEMAS[(i + 1) % TEMAS.length].id;
}
