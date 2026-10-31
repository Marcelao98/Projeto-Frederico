/**
 * A fila: a música que toca e as que esperam. Só estado, sem tocar nada.
 *
 * Equivalente à classe Fila do Bardo, mais o que o modo Playlist precisa
 * (remover, mover, tocar um item da fila, embaralhar). Imutável: cada
 * operação devolve uma fila nova, que é o que o React gosta.
 */

import type { Musica } from "../nucleo/tipos";
import { MAX_FILA, type ItemDaFila, type Onde } from "./tipos";

export interface Fila {
  tocando: ItemDaFila | null;
  proximas: ItemDaFila[];
  repetir: boolean;
}

export const FILA_VAZIA: Fila = { tocando: null, proximas: [], repetir: false };

let contador = 0;
export function novoUid(): string {
  contador += 1;
  return `${Date.now().toString(36)}-${contador.toString(36)}`;
}

export function comoItem(musica: Musica): ItemDaFila {
  return { ...musica, uid: novoUid() };
}

/**
 * Põe as músicas que couberem (até MAX_FILA esperando).
 * "fim" vai pro fim; "proxima" entra na frente da fila; "agora" toca a
 * primeira já (a que tocava sai) e o resto vira as próximas.
 */
export function adicionar(fila: Fila, musicas: Musica[], onde: Onde = "fim") {
  const itens = musicas.map(comoItem);
  if (!itens.length) return { fila, entraram: 0, posicao: -1 };

  if (onde === "agora") {
    const [primeira, ...resto] = itens;
    const cabem = Math.max(MAX_FILA - fila.proximas.length, 0);
    const entram = resto.slice(0, cabem);
    return {
      fila: { tocando: primeira, proximas: [...entram, ...fila.proximas], repetir: false },
      entraram: 1 + entram.length,
      posicao: 0,
    };
  }

  const cabem = Math.max(MAX_FILA - fila.proximas.length, 0);
  const entram = itens.slice(0, cabem);
  if (!entram.length) return { fila, entraram: 0, posicao: -1 };
  const proximas = onde === "proxima" ? [...entram, ...fila.proximas] : [...fila.proximas, ...entram];
  const posicao = onde === "proxima" ? 1 : fila.proximas.length + 1;
  return { fila: { ...fila, proximas }, entraram: entram.length, posicao };
}

/** A próxima vira a que toca (null se acabou). */
export function avancar(fila: Fila): Fila {
  const [proxima = null, ...resto] = fila.proximas;
  return { ...fila, tocando: proxima, proximas: resto };
}

/** Tira as que esperam; a atual continua. */
export function limpar(fila: Fila): Fila {
  return { ...fila, proximas: [] };
}

/** Esvazia tudo, inclusive a atual, e desliga o repetir. */
export function resetar(): Fila {
  return FILA_VAZIA;
}

export function remover(fila: Fila, uid: string): Fila {
  return { ...fila, proximas: fila.proximas.filter((m) => m.uid !== uid) };
}

/** Move a música `uid` pra posição `para` (0 = a próxima a tocar). */
export function mover(fila: Fila, uid: string, para: number): Fila {
  const de = fila.proximas.findIndex((m) => m.uid === uid);
  if (de < 0) return fila;
  const proximas = [...fila.proximas];
  const [item] = proximas.splice(de, 1);
  proximas.splice(Math.max(0, Math.min(para, proximas.length)), 0, item);
  return { ...fila, proximas };
}

/** Pula direto pra música `uid` da fila: as que vinham antes dela continuam esperando. */
export function tocarItem(fila: Fila, uid: string): Fila {
  const item = fila.proximas.find((m) => m.uid === uid);
  if (!item) return fila;
  return { tocando: item, proximas: fila.proximas.filter((m) => m.uid !== uid), repetir: false };
}

export function embaralhar(fila: Fila, aleatorio: () => number = Math.random): Fila {
  const proximas = [...fila.proximas];
  for (let i = proximas.length - 1; i > 0; i--) {
    const j = Math.floor(aleatorio() * (i + 1));
    [proximas[i], proximas[j]] = [proximas[j], proximas[i]];
  }
  return { ...fila, proximas };
}
