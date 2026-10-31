/**
 * Playlists salvas: uma lista de músicas com nome ("Sessão 12 — a cripta").
 *
 * Com o Freddy ligado, moram no backend (pasta do mestre, um lugar só pro
 * app e pro navegador). Sem ele, no navegador (localStorage), como antes.
 */

import { novoUid } from "../motor/fila";
import type { Musica } from "../nucleo/tipos";
import { criarArmazem } from "./armazem";
import type { ApiFreddy } from "./freddy";

export interface PlaylistSalva {
  id: string;
  nome: string;
  musicas: Musica[];
  atualizadaEm: number;
}

/** As do navegador (ficam guardadas mesmo usando o Freddy: são o backup). */
const doNavegador = criarArmazem<PlaylistSalva[]>([], "freddy.playlists");
/** Já perguntou se leva as do navegador pro Freddy (sim ou não, não pergunta de novo). */
const jaPerguntou = criarArmazem<boolean>(false, "freddy.playlists.levadas");

/** As playlists em uso: as do Freddy, se ligado; senão, as do navegador. */
export const playlists = criarArmazem<PlaylistSalva[]>(doNavegador.ler());

let api: ApiFreddy | null = null;
let aoFalharGravacao: (erro: unknown) => void = (e) => console.error("Playlist não foi salva no Freddy:", e);
/** Quem avisa a pessoa se o Freddy recusar uma gravação (o main.tsx põe no chat). */
export function definirAvisoDeFalha(f: (erro: unknown) => void) {
  aoFalharGravacao = f;
}

/** Só o que importa da música (sem o uid da fila). */
function limpa({ titulo, link, faixaId, origem, duracaoSegundos }: Musica): Musica {
  return { titulo, link, faixaId, origem, duracaoSegundos };
}

/** Salva com esse nome; se já existe uma com o mesmo nome, substitui. */
export function salvarPlaylist(nome: string, musicas: Musica[]): PlaylistSalva {
  const existente = playlists.ler().find((p) => p.nome.toLowerCase() === nome.toLowerCase());
  const playlist: PlaylistSalva = {
    id: existente?.id ?? novoUid(),
    nome,
    musicas: musicas.map(limpa),
    atualizadaEm: Date.now(),
  };
  const nova = (lista: PlaylistSalva[]) => [playlist, ...lista.filter((p) => p.id !== playlist.id)];
  playlists.escrever(nova);
  if (api) api.salvarPlaylist(playlist).catch(aoFalharGravacao);
  else doNavegador.escrever(nova);
  return playlist;
}

export function excluirPlaylist(id: string) {
  const sem = (lista: PlaylistSalva[]) => lista.filter((p) => p.id !== id);
  playlists.escrever(sem);
  if (api) api.excluirPlaylist(id).catch(aoFalharGravacao);
  else doNavegador.escrever(sem);
}

/**
 * Passa a usar as playlists do Freddy. Na primeira vez, se o Freddy não tem
 * nenhuma e o navegador tem, pergunta se leva (e não pergunta de novo).
 */
export async function usarPlaylistsDoFreddy(
  freddy: ApiFreddy,
  perguntar: (quantas: number) => boolean = (n) =>
    window.confirm(`Você tem ${n} playlist${n > 1 ? "s" : ""} salva${n > 1 ? "s" : ""} neste navegador. Levar pro Freddy?`),
) {
  api = freddy;
  let lista = await freddy.playlists();
  const locais = doNavegador.ler();
  if (!lista.length && locais.length && !jaPerguntou.ler()) {
    jaPerguntou.escrever(true);
    if (perguntar(locais.length)) {
      for (const p of [...locais].reverse()) await freddy.salvarPlaylist(p); // a mais nova fica no topo
      lista = await freddy.playlists();
    }
  }
  playlists.escrever(lista);
}

/** Pros testes: volta a usar só o navegador. */
export function usarPlaylistsDoNavegador() {
  api = null;
  playlists.escrever(doNavegador.ler());
}
