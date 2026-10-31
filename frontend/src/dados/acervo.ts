/**
 * O acervo de faixas e o vocabulário de categorias, prontos pra buscar.
 *
 * Hoje vem direto dos JSON do Bardo (modules/bardo/dataset). Quando o
 * backend existir, ele serve esses mesmos dados (e grava as descobertas);
 * as telas só enxergam a interface `Acervo`.
 */

import musicasJson from "@dataset/musicas.json";
import vocabularioJson from "@dataset/vocabulario.json";
import { MAX_RESULTADOS_DA_BUSCA, buscarPorTags, montarVocabulario, sortear, type Vocabulario } from "../nucleo/busca";
import { normalizar } from "../nucleo/texto";
import type { Faixa, VocabularioBruto } from "../nucleo/tipos";

export interface Contagem {
  nome: string;
  quantas: number;
}

export interface Acervo {
  faixas: Faixa[];
  vocabulario: Vocabulario;
  /** Categorias de busca, da mais usada pra menos. */
  categorias: Contagem[];
  /** Franquias (origens), da maior pra menor. */
  origens: (Contagem & { tipo: string })[];
  porId(id: string): Faixa | undefined;
  /** Busca booleana ("triste e bloodborne"). Vazio = nada. */
  buscar(texto: string): Faixa[];
  /** buscar() sorteando até MAX_RESULTADOS_DA_BUSCA, como o Bardo faz pra fila. */
  sortearDaBusca(texto: string): { escolhidas: Faixa[]; total: number };
}

export function montarAcervo(faixas: Faixa[], bruto: VocabularioBruto): Acervo {
  const vocabulario = montarVocabulario(bruto);
  const porId = new Map(faixas.map((f) => [f.id, f]));

  const contarCategorias = new Map<string, number>();
  const contarOrigens = new Map<string, { tipo: string; quantas: number }>();
  for (const f of faixas) {
    for (const c of f.categorias ?? []) contarCategorias.set(c, (contarCategorias.get(c) ?? 0) + 1);
    const o = contarOrigens.get(f.origem.nome) ?? { tipo: f.origem.tipo, quantas: 0 };
    o.quantas += 1;
    contarOrigens.set(f.origem.nome, o);
  }
  // Categorias do vocabulário sem faixa ainda também aparecem (com 0).
  for (const c of Object.keys(bruto.categorias)) if (!contarCategorias.has(c)) contarCategorias.set(c, 0);

  const categorias = [...contarCategorias].map(([nome, quantas]) => ({ nome, quantas }));
  categorias.sort((a, b) => b.quantas - a.quantas || a.nome.localeCompare(b.nome));
  const origens = [...contarOrigens].map(([nome, o]) => ({ nome, ...o }));
  origens.sort((a, b) => b.quantas - a.quantas);

  const buscar = (texto: string) => buscarPorTags(texto, faixas, vocabulario);
  return {
    faixas,
    vocabulario,
    categorias,
    origens,
    porId: (id) => porId.get(id),
    buscar,
    sortearDaBusca(texto) {
      const achadas = buscar(texto);
      return { escolhidas: sortear(achadas, MAX_RESULTADOS_DA_BUSCA), total: achadas.length };
    },
  };
}

export const acervoLocal: Acervo = montarAcervo(
  (musicasJson as { musicas: Faixa[] }).musicas,
  vocabularioJson as VocabularioBruto,
);

// As categorias ficam sem acento no JSON ("epico"); na tela, com.
const ROTULOS: Record<string, string> = {
  epico: "épico",
  misterio: "mistério",
  magico: "mágico",
  dramatico: "dramático",
  esperancoso: "esperançoso",
  exploracao: "exploração",
  nostalgico: "nostálgico",
  engracado: "engraçado",
  romantico: "romântico",
  vilao: "vilão",
};

const EMOJIS: Record<string, string> = {
  combate: "⚔️", triste: "😢", calmo: "🍃", sombrio: "🌑", epico: "🏔️", emocionante: "🔥",
  tenso: "😰", chefe: "👹", dramatico: "🎭", final: "🏁", magico: "✨", alegre: "😄",
  terror: "👻", nobreza: "👑", cidade: "🍺", misterio: "🔍", exploracao: "🧭", esperancoso: "🌅",
  sagrado: "⛪", engracado: "🤡", natureza: "🌲", masmorra: "🕳️", descanso: "🏕️", nostalgico: "📜",
  abertura: "🎬", vilao: "🦹", romantico: "💕",
};

export function rotuloCategoria(categoria: string): string {
  return ROTULOS[categoria] ?? categoria;
}

export function emojiCategoria(categoria: string): string {
  return EMOJIS[categoria] ?? "🎵";
}

/** Palavras pra autocompletar no chat: categorias e franquias que começam com `prefixo`. */
export function sugestoesDeBusca(acervo: Acervo, prefixo: string, maximo = 6): string[] {
  const p = normalizar(prefixo);
  if (!p) return [];
  const candidatas = [
    ...acervo.categorias.filter((c) => c.quantas > 0).map((c) => rotuloCategoria(c.nome)),
    ...acervo.origens.map((o) => o.nome),
  ];
  return candidatas.filter((c) => normalizar(c).startsWith(p) && normalizar(c) !== p).slice(0, maximo);
}
