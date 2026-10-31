/**
 * Playlists salvas: uma lista de músicas com nome ("Sessão 12 — a cripta").
 * Hoje ficam no navegador; com o backend, vão pro disco do mestre.
 */

import { novoUid } from "../motor/fila";
import type { Musica } from "../nucleo/tipos";
import { criarArmazem } from "./armazem";

export interface PlaylistSalva {
  id: string;
  nome: string;
  musicas: Musica[];
  atualizadaEm: number;
}

export const playlists = criarArmazem<PlaylistSalva[]>([], "freddy.playlists");

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
  playlists.escrever((lista) => [playlist, ...lista.filter((p) => p.id !== playlist.id)]);
  return playlist;
}

export function excluirPlaylist(id: string) {
  playlists.escrever((lista) => lista.filter((p) => p.id !== id));
}
