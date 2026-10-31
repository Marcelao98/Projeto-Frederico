/**
 * Utilitários de texto compartilhados pelo núcleo.
 *
 * O Bardo é Python, e o `\b` e o `\w` do `re` do Python entendem acento.
 * Os do JavaScript não entendem, nem com a flag `u`: `/\bpõe\b/` falha em
 * "natty põe". Por isso as regex do núcleo usam `palavra()`, que monta a
 * fronteira de palavra com classes Unicode.
 */

/** Letra, número ou "_", em qualquer alfabeto: o `\w` do Python. */
export const CARACTERE_DE_PALAVRA = "\\p{L}\\p{N}_";

const ANTES = `(?<![${CARACTERE_DE_PALAVRA}])`;
const DEPOIS = `(?![${CARACTERE_DE_PALAVRA}])`;

/** `\b(alternativas)\b` com acento: palavra("toca|põe") acha "põe" em "natty põe". */
export function palavra(alternativas: string, flags = "iu", capturar = false): RegExp {
  return new RegExp(`${ANTES}(${capturar ? "" : "?:"}${alternativas})${DEPOIS}`, flags);
}

/** Só a fronteira da esquerda, como `\b(\d{1,3})` no Python. */
export function comecoDePalavra(padrao: string, flags = "iu"): RegExp {
  return new RegExp(`${ANTES}${padrao}`, flags);
}

/** Minúsculas, sem acento e sem espaço nas pontas, pra "É Pico" bater com "epico". */
export function normalizar(texto: string): string {
  return texto.toLowerCase().trim().normalize("NFD").replace(/\p{Mn}/gu, "");
}

/** "Queen's Gardens" vira "queens-gardens" (sem acento, só [a-z0-9-]). */
export function slug(texto: string): string {
  return normalizar(texto)
    .replace(/['’]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

/** Tira os caracteres de `chars` das pontas, como o `str.strip(chars)` do Python. */
export function aparar(texto: string, chars: string): string {
  let inicio = 0;
  let fim = texto.length;
  while (inicio < fim && chars.includes(texto[inicio])) inicio++;
  while (fim > inicio && chars.includes(texto[fim - 1])) fim--;
  return texto.slice(inicio, fim);
}
