/**
 * Playlists salvas: uma lista de músicas com nome ("Sessão 12 — a cripta").
 *
 * Com o Freddy ligado, moram no backend (pasta do mestre, um lugar só pro
 * app e pro navegador). Sem ele, no navegador (localStorage), como antes.
 */

import { novoUid } from "../navegador/fila";
import { normalizar } from "../comum/texto";
import { videoId } from "../comum/youtube";
import type { Musica } from "../comum/tipos";
import { criarArmazem } from "./armazem";
import type { ApiFreddy } from "../api/freddy";

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

/** Grava (no Freddy ou no navegador) e põe no topo da lista. */
function gravar(playlist: PlaylistSalva): PlaylistSalva {
  const nova = (lista: PlaylistSalva[]) => [playlist, ...lista.filter((p) => p.id !== playlist.id)];
  playlists.escrever(nova);
  if (api) api.salvarPlaylist(playlist).catch(aoFalharGravacao);
  else doNavegador.escrever(nova);
  return playlist;
}

const mesmoNome = (a: string, b: string) => normalizar(a) === normalizar(b);

export function playlistPorId(id: string): PlaylistSalva | undefined {
  return playlists.ler().find((p) => p.id === id);
}

/** Salva com esse nome; se já existe uma com o mesmo nome, substitui. */
export function salvarPlaylist(nome: string, musicas: Musica[]): PlaylistSalva {
  const existente = playlists.ler().find((p) => mesmoNome(p.nome, nome));
  return gravar({ id: existente?.id ?? novoUid(), nome: nome.trim(), musicas: musicas.map(limpa), atualizadaEm: Date.now() });
}

function mudar(id: string, mudanca: (p: PlaylistSalva) => Partial<PlaylistSalva>): PlaylistSalva | null {
  const atual = playlistPorId(id);
  if (!atual) return null;
  return gravar({ ...atual, ...mudanca(atual), atualizadaEm: Date.now() });
}

/** Troca o nome. Recusa (devolve o motivo) se outra já tem esse nome. */
export function renomearPlaylist(id: string, nome: string): string | null {
  const limpo = nome.trim();
  if (!limpo) return "o nome não pode ficar vazio";
  if (playlists.ler().some((p) => p.id !== id && mesmoNome(p.nome, limpo))) return `já existe uma playlist "${limpo}"`;
  mudar(id, () => ({ nome: limpo }));
  return null;
}

/** Põe a música no fim da playlist. "ja_estava" se o mesmo vídeo já está lá. */
export function adicionarNaPlaylist(id: string, musica: Musica): "entrou" | "ja_estava" | "sem_playlist" {
  const atual = playlistPorId(id);
  if (!atual) return "sem_playlist";
  if (atual.musicas.some((m) => videoId(m.link) === videoId(musica.link))) return "ja_estava";
  mudar(id, (p) => ({ musicas: [...p.musicas, limpa(musica)] }));
  return "entrou";
}

export function removerDaPlaylist(id: string, indice: number) {
  mudar(id, (p) => ({ musicas: p.musicas.filter((_, i) => i !== indice) }));
}

/** Move a música da posição `de` pra `para` (contando do 0). */
export function moverNaPlaylist(id: string, de: number, para: number) {
  mudar(id, (p) => {
    const musicas = [...p.musicas];
    if (de < 0 || de >= musicas.length) return {};
    const [m] = musicas.splice(de, 1);
    musicas.splice(Math.max(0, Math.min(para, musicas.length)), 0, m);
    return { musicas };
  });
}

/**
 * Acha a playlist pelo que a pessoa digitou ("sessao 12" acha "Sessão 12 —
 * a cripta"). Nome igual ganha; senão, as que começam com o texto; senão, as
 * que têm todas as palavras. Mais de uma = ambígua (a tela pergunta qual).
 */
export function acharPlaylist(texto: string, lista: PlaylistSalva[] = playlists.ler()): PlaylistSalva[] {
  const alvo = normalizar(texto).replace(/[^\p{L}\p{N} ]/gu, " ").replace(/\s+/g, " ").trim();
  if (!alvo) return [];
  const limpo = (n: string) => normalizar(n).replace(/[^\p{L}\p{N} ]/gu, " ").replace(/\s+/g, " ").trim();
  const iguais = lista.filter((p) => limpo(p.nome) === alvo);
  if (iguais.length) return iguais;
  const comecam = lista.filter((p) => limpo(p.nome).startsWith(alvo));
  if (comecam.length) return comecam;
  const palavras = alvo.split(" ");
  return lista.filter((p) => {
    const nome = ` ${limpo(p.nome)} `;
    return palavras.every((w) => nome.includes(` ${w}`));
  });
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
