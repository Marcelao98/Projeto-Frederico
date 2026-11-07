/** As mensagens do chat. Ficam fora do componente pra sobreviver à troca de modo. */

import { criarArmazem } from "../../estado/armazem";
import type { Musica } from "../../comum/tipos";
import type { RespostaFreddy } from "./conversa";
import type { Revisao } from "./revisao";

export interface MensagemChat {
  id: number;
  autor: "voce" | "freddy";
  texto: string;
  musicas?: Musica[];
  /** "Era essa?" em aberto (some quando respondem). */
  pergunta?: Musica;
  /** "Tá certo?" sobre os temas de uma faixa (some quando respondem). */
  revisao?: Revisao;
  /** Aviso pequeno do narrador (o que mudou fora do chat). */
  discreta?: boolean;
  quando: number;
}

const MAX_MENSAGENS = 200;
let proximoId = 1;

export const historico = criarArmazem<MensagemChat[]>([]);

export function registrar(
  autor: MensagemChat["autor"],
  { texto, musicas, pergunta, revisao }: RespostaFreddy,
  discreta = false,
) {
  // Uma revisão nova (ou resposta digitada) fecha os botões das anteriores.
  if (autor === "voce" || revisao) fecharRevisoes();
  const mensagem: MensagemChat = { id: proximoId++, autor, texto, musicas, pergunta, revisao, discreta, quando: Date.now() };
  historico.escrever((lista) => [...lista, mensagem].slice(-MAX_MENSAGENS));
}

export function fecharRevisoes() {
  if (!historico.ler().some((m) => m.revisao)) return;
  historico.escrever((lista) => lista.map((m) => (m.revisao ? { ...m, revisao: undefined } : m)));
}

/** Fecha o "era essa?" de uma mensagem (já responderam). */
export function fecharPergunta(id: number) {
  historico.escrever((lista) => lista.map((m) => (m.id === id ? { ...m, pergunta: undefined } : m)));
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
