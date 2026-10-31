/**
 * Busca booleana no acervo: "triste e bloodborne", "boss fight sem elden ring",
 * "calmo e fire emblem ou hollow knight".
 *
 * Porta fiel de `buscar_por_tags` e do vocabulário do Bardo
 * (modules/bardo/service.py). Regras:
 *   - "e" = E, "ou" = OU (precedência menor), "sem"/"não" na frente nega o termo;
 *   - um termo bate se aparece (sem acento) no nome, origem, temas ou
 *     categorias da faixa, OU se é sinônimo de uma categoria dela;
 *   - termo de várias palavras tenta a frase inteira e, se não bater, cada palavra;
 *   - palavras de preenchimento ("uma", "música", "de", "clima"...) são ignoradas.
 */

import { normalizar, palavra } from "./texto";
import type { Faixa, VocabularioBruto } from "./tipos";

export const MAX_RESULTADOS_DA_BUSCA = 15;

const PALAVRAS_DE_PREENCHIMENTO = new Set([
  "musica", "musicas", "som", "sons", "faixa", "faixas", "trilha", "sonora",
  "algo", "alguma", "algum", "uma", "um", "umas", "uns",
  "de", "do", "da", "dos", "das", "a", "o", "as", "os",
  "para", "pra", "pro", "com", "no", "na", "nos", "nas", "em",
  "tipo", "bem", "muito", "mais", "clima", "cena", "hora", "estilo", "vibe",
]);

/**
 * vocabulario.json já normalizado.
 * sinonimos: palavra que as pessoas digitam → categorias que ela puxa.
 * porTema: tema cru do dataset → categorias que ele dá à faixa.
 */
export interface Vocabulario {
  sinonimos: Map<string, Set<string>>;
  porTema: Map<string, Set<string>>;
}

/** Acrescenta o feminino: "animado" → "animada", "assustador" → "assustadora". */
function comFeminino(palavras: Set<string>): Set<string> {
  const todas = new Set(palavras);
  for (const p of palavras) {
    if (p.includes(" ")) continue;
    if (p.endsWith("o") && !p.endsWith("ao")) todas.add(p.slice(0, -1) + "a");
    else if (p.endsWith("or")) todas.add(p + "a");
  }
  return todas;
}

function acrescentar(mapa: Map<string, Set<string>>, chave: string, valor: string) {
  let conjunto = mapa.get(chave);
  if (!conjunto) mapa.set(chave, (conjunto = new Set()));
  conjunto.add(valor);
}

export function montarVocabulario(bruto: VocabularioBruto): Vocabulario {
  const sinonimos = new Map<string, Set<string>>();
  const porTema = new Map<string, Set<string>>();
  for (const [categoria, spec] of Object.entries(bruto.categorias)) {
    const palavras = comFeminino(new Set([categoria, ...(spec.palavras ?? [])].map(normalizar)));
    for (const p of palavras) acrescentar(sinonimos, p, categoria);
    // Toda palavra também conta como tema; os "temas" só puxam a faixa.
    const temas = comFeminino(new Set((spec.temas ?? []).map(normalizar)));
    for (const t of new Set([...palavras, ...temas])) acrescentar(porTema, t, categoria);
  }
  return { sinonimos, porTema };
}

/** Categorias que os temas crus de uma faixa dão a ela, em ordem alfabética. */
export function categoriasDosTemas(temas: string[], vocabulario: Vocabulario): string[] {
  const categorias = new Set<string>();
  for (const tema of temas) for (const c of vocabulario.porTema.get(normalizar(tema)) ?? []) categorias.add(c);
  return [...categorias].sort();
}

type Termo = { negado: boolean; termo: string };
/** Grupos OU; cada grupo é uma lista de termos E. */
export type Consulta = Termo[][];

const OU_RE = palavra("ou", "gu");
// Com captura: o split devolve os separadores junto, como o re.split do Python.
const SEPARADOR_RE = palavra("e|sem|nao", "gu", true);

export function interpretarConsulta(texto: string): Consulta {
  const grupos: Consulta = [];
  for (const brutoOu of normalizar(texto).split(OU_RE)) {
    const pedacos = brutoOu.split(SEPARADOR_RE);
    const termos: Termo[] = [];
    let negadoAtual = false;
    for (const bruto of pedacos) {
      const pedaco = (bruto ?? "").trim();
      if (pedaco === "e" || pedaco === "sem" || pedaco === "nao") {
        negadoAtual = pedaco !== "e";
        continue;
      }
      const termo = pedaco
        .split(/\s+/)
        .filter((p) => p && !PALAVRAS_DE_PREENCHIMENTO.has(p))
        .join(" ");
      if (termo) termos.push({ negado: negadoAtual, termo });
      negadoAtual = false;
    }
    if (termos.length) grupos.push(termos);
  }
  return grupos;
}

function textoBuscavel(faixa: Faixa): string {
  return normalizar(
    [faixa.nome, faixa.origem.nome, faixa.origem.tipo, ...faixa.temas, ...(faixa.categorias ?? [])].join(" "),
  );
}

function contem(alvo: string, categorias: Set<string>, termo: string, vocabulario: Vocabulario): boolean {
  if (alvo.includes(termo)) return true;
  for (const c of vocabulario.sinonimos.get(termo) ?? []) if (categorias.has(c)) return true;
  return false;
}

function termoBate(alvo: string, categorias: Set<string>, { negado, termo }: Termo, vocabulario: Vocabulario) {
  // Primeiro a frase inteira ("boss fight"); se não bater, cada palavra ("luta chefe").
  const contido =
    contem(alvo, categorias, termo, vocabulario) ||
    (termo.includes(" ") && termo.split(" ").every((p) => contem(alvo, categorias, p, vocabulario)));
  return negado ? !contido : contido;
}

export function faixaBate(faixa: Faixa, consulta: Consulta, vocabulario: Vocabulario): boolean {
  const alvo = textoBuscavel(faixa);
  const categorias = new Set(faixa.categorias ?? []);
  return consulta.some((grupo) => grupo.every((t) => termoBate(alvo, categorias, t, vocabulario)));
}

/** As faixas que batem com a busca; vazio se nada bate ou se a busca só tinha preenchimento. */
export function buscarPorTags(texto: string, faixas: Faixa[], vocabulario: Vocabulario): Faixa[] {
  const consulta = interpretarConsulta(texto);
  if (!consulta.length) return [];
  return faixas.filter((f) => faixaBate(f, consulta, vocabulario));
}

/** Sorteia até `maximo` itens, sem repetir (o random.sample do Python). */
export function sortear<T>(itens: T[], maximo: number, aleatorio: () => number = Math.random): T[] {
  if (itens.length <= maximo) return [...itens];
  const copia = [...itens];
  for (let i = copia.length - 1; i > 0; i--) {
    const j = Math.floor(aleatorio() * (i + 1));
    [copia[i], copia[j]] = [copia[j], copia[i]];
  }
  return copia.slice(0, maximo);
}
