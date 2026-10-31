/** As mensagens do chat. Ficam fora do componente pra sobreviver à troca de modo. */

import { criarArmazem } from "../../dados/armazem";
import type { Musica } from "../../nucleo/tipos";
import type { RespostaFreddy } from "./conversa";

export interface MensagemChat {
  id: number;
  autor: "voce" | "freddy";
  texto: string;
  musicas?: Musica[];
  quando: number;
}

const MAX_MENSAGENS = 200;
let proximoId = 1;

export const historico = criarArmazem<MensagemChat[]>([]);

export function registrar(autor: MensagemChat["autor"], { texto, musicas }: RespostaFreddy) {
  const mensagem: MensagemChat = { id: proximoId++, autor, texto, musicas, quando: Date.now() };
  historico.escrever((lista) => [...lista, mensagem].slice(-MAX_MENSAGENS));
}

export function limparHistorico() {
  historico.escrever([]);
}

/** O que você já mandou, do mais novo pro mais velho (pra ↑ e ↓ no campo). */
export function pedidosAnteriores(): string[] {
  return historico
    .ler()
    .filter((m) => m.autor === "voce")
    .map((m) => m.texto)
    .reverse();
}
