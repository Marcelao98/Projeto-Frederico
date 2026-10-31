/** O formato do acervo: o mesmo de modules/bardo/dataset/musicas.json. */

export interface Origem {
  nome: string;
  tipo: string; // "jogo", "anime", "visual novel", "outro"...
}

export interface Faixa {
  id: string;
  nome: string;
  link: string;
  escopo: "faixa_individual" | "album_completo" | string;
  origem: Origem;
  temas: string[];
  categorias?: string[];
  comentario_pessoal?: string;
}

export interface VocabularioBruto {
  categorias: Record<string, { palavras?: string[]; temas?: string[] }>;
}

/** O que vai pra fila: um link e um título. A faixa do acervo, se veio de lá. */
export interface Musica {
  titulo: string;
  link: string;
  faixaId?: string;
  origem?: string;
  duracaoSegundos?: number;
}

export function musicaDaFaixa(faixa: Faixa): Musica {
  return { titulo: faixa.nome, link: faixa.link, faixaId: faixa.id, origem: faixa.origem.nome };
}
