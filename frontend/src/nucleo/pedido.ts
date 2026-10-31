/**
 * Pedidos em linguagem natural: "toca triste e bloodborne", "pula", "volume 30".
 *
 * Porta fiel de `interpretar_pedido` do Bardo (modules/bardo/service.py), com
 * as mesmas regras e a mesma ordem de checagem: quem muda uma, muda a outra.
 * Os testes de pedido.test.ts são os do test_service.py traduzidos.
 * Sem LLM: é só regex, previsível e instantâneo.
 */

import { CARACTERE_DE_PALAVRA, aparar, comecoDePalavra, palavra } from "./texto";
import { URL_YOUTUBE_GLOBAL_RE, extrairLinkYoutube } from "./youtube";

export const VOLUME_PADRAO = 50; // %
export const PASSO_VOLUME = 20; // %: quanto "aumenta"/"abaixa" mexe

const TOCAR_RE = palavra("toca|toque|tocar|bota|coloca|põe|poe|play|adiciona|adicione|add");
const PULAR_RE = palavra("pula|pule|pular|pr[oó]xima|skip|next");
const FILA_RE = palavra("fila|playlist|queue");
const LIMPAR_RE = palavra("limpa|limpe|limpar|esvazia|esvazie|apaga|zera|clear");
const PAUSAR_RE = palavra("pausa|pause|pausar");
const CONTINUAR_RE = palavra("continua|continue|continuar|despausa|retoma|volta|resume");
const PARAR_RE = palavra("para|pare|parar|stop|chega|desliga|sai|sair");
const REPETIR_RE = palavra("repete|repetir|repita|loop");
// "para de repetir", "repete não", "chega de loop", "desliga o repetir".
const DESLIGAR_REPETIR_RE = palavra("n[ãa]o|para|pare|parar|chega|desliga|tira");
const VOLUME_RE = palavra("volume");
const AUMENTAR_RE = palavra("aumenta|sobe|mais alto");
const DIMINUIR_RE = palavra("abaixa|baixa|diminui|mais baixo");
const NUMERO_RE = comecoDePalavra("(\\d{1,3})\\s*%?");
const PARA_DE_RE = new RegExp(`^\\s+de\\s+([${CARACTERE_DE_PALAVRA}]+)`, "iu");
const O_QUE_O_FREDDY_PARA = new Set(["tocar", "tocando", "cantar", "cantando", "música", "musica", "som", "barulho"]);

/**
 * O que pediram pro Freddy fazer com a música.
 *
 * - tocar: `link` se mandaram um link, senão `busca` (o que vem depois do
 *   verbo); os dois ausentes = pediram pra tocar sem dizer o quê.
 * - volume: `volume` absoluto, ou `delta` (+/-PASSO_VOLUME); nenhum dos dois
 *   é pergunta ("qual o volume?").
 * - repetir: `ligar` false = desligar; ausente = alternar.
 */
export type Pedido =
  | { acao: "tocar"; link?: string; busca?: string }
  | { acao: "volume"; volume?: number; delta?: number }
  | { acao: "repetir"; ligar?: false }
  | { acao: "pular" | "fila" | "limpar_fila" | "pausar" | "continuar" | "parar" };

/** Traduz um pedido em linguagem natural num Pedido, ou null se não for de música. */
export function interpretarPedido(texto: string): Pedido | null {
  const link = extrairLinkYoutube(texto);
  // O link sai antes das outras regras: "para" ou "volta" dentro de uma URL
  // não pode virar comando.
  const semLink = texto.replace(URL_YOUTUBE_GLOBAL_RE, " ");

  if (link && TOCAR_RE.test(semLink)) return { acao: "tocar", link };
  // Fila antes de parar/tocar: "limpa a fila" não é "para", e "toca a
  // próxima" é pular, não pedido sem link.
  if (FILA_RE.test(semLink) && LIMPAR_RE.test(semLink)) return { acao: "limpar_fila" };

  // Repetir antes de parar: "para de repetir" desliga o loop, não para a
  // música. Mas se "toca" vem antes, é busca ("toca Repete Comigo").
  const repetir = REPETIR_RE.exec(semLink);
  const tocar = TOCAR_RE.exec(semLink);
  if (repetir && !(tocar && tocar.index < repetir.index)) {
    return DESLIGAR_REPETIR_RE.test(semLink) ? { acao: "repetir", ligar: false } : { acao: "repetir" };
  }
  if (PULAR_RE.test(semLink)) return { acao: "pular" };
  if (FILA_RE.test(semLink)) return { acao: "fila" };
  if (VOLUME_RE.test(semLink) || AUMENTAR_RE.test(semLink) || DIMINUIR_RE.test(semLink)) {
    return pedidoDeVolume(semLink);
  }
  if (PAUSAR_RE.test(semLink)) return { acao: "pausar" };
  if (CONTINUAR_RE.test(semLink)) return { acao: "continuar" };

  // Quem vem primeiro decide: em "toca uma música para relaxar" o "para" é
  // preposição; em "para de tocar" é comando.
  const parar = PARAR_RE.exec(semLink);
  if (parar && paraDeOutraCoisa(semLink.slice(parar.index + parar[0].length))) {
    // "para de transcrever" é de outro módulo: só "para de tocar/cantar/música".
    return null;
  }
  if (parar && !(tocar && tocar.index < parar.index)) return { acao: "parar" };
  if (tocar) {
    // O nome do Freddy vem antes do verbo, então o que sobra depois dele é a busca.
    const busca = aparar(semLink.slice(tocar.index + tocar[0].length), " \t\n,.!?:;");
    return busca ? { acao: "tocar", busca } : { acao: "tocar" };
  }
  return null;
}

/** True em "para de X" quando X não é música: "para de transcrever", "para de pausar". */
function paraDeOutraCoisa(depoisDoPara: string): boolean {
  const m = PARA_DE_RE.exec(depoisDoPara);
  return m !== null && !O_QUE_O_FREDDY_PARA.has(m[1].toLowerCase());
}

function pedidoDeVolume(texto: string): Pedido {
  const numero = NUMERO_RE.exec(texto);
  if (numero) return { acao: "volume", volume: limitarVolume(Number(numero[1])) };
  if (AUMENTAR_RE.test(texto)) return { acao: "volume", delta: PASSO_VOLUME };
  if (DIMINUIR_RE.test(texto)) return { acao: "volume", delta: -PASSO_VOLUME };
  return { acao: "volume" };
}

export function limitarVolume(volume: number): number {
  return Math.max(0, Math.min(100, Math.round(volume)));
}
