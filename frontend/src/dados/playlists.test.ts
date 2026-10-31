import { afterEach, describe, expect, it } from "vitest";
import type { ApiFreddy } from "./freddy";
import {
  excluirPlaylist,
  playlists,
  salvarPlaylist,
  usarPlaylistsDoFreddy,
  usarPlaylistsDoNavegador,
  type PlaylistSalva,
} from "./playlists";

function freddyFalso(inicial: PlaylistSalva[] = []) {
  let lista = [...inicial];
  const chamadas: string[] = [];
  const api = {
    playlists: async () => lista,
    salvarPlaylist: async (p: PlaylistSalva) => {
      chamadas.push(`salvar ${p.nome}`);
      lista = [p, ...lista.filter((x) => x.id !== p.id)];
      return p;
    },
    excluirPlaylist: async (id: string) => {
      chamadas.push(`excluir ${id}`);
      lista = lista.filter((x) => x.id !== id);
    },
  } as unknown as ApiFreddy;
  return { api, chamadas, lista: () => lista };
}

const musica = { titulo: "M", link: "https://youtu.be/m" };

describe("playlists", () => {
  afterEach(() => {
    usarPlaylistsDoNavegador();
    for (const p of playlists.ler()) excluirPlaylist(p.id);
  });

  it("sem o Freddy, salva no navegador; mesmo nome substitui", () => {
    salvarPlaylist("Cripta", [musica]);
    salvarPlaylist("cripta", [musica, musica]);
    expect(playlists.ler().map((p) => [p.nome, p.musicas.length])).toEqual([["cripta", 2]]);
  });

  it("com o Freddy, usa as dele e grava lá", async () => {
    const f = freddyFalso([{ id: "x", nome: "Do Freddy", musicas: [], atualizadaEm: 1 }]);
    await usarPlaylistsDoFreddy(f.api, () => true);
    expect(playlists.ler().map((p) => p.nome)).toEqual(["Do Freddy"]);
    salvarPlaylist("Nova", [musica]);
    excluirPlaylist("x");
    await Promise.resolve();
    expect(f.chamadas).toEqual(["salvar Nova", "excluir x"]);
    expect(f.lista().map((p) => p.nome)).toEqual(["Nova"]);
  });

  it("primeira vez: oferece levar as do navegador, uma vez só", async () => {
    salvarPlaylist("Antiga", [musica]);
    salvarPlaylist("Mais nova", [musica]);
    const f = freddyFalso();
    let perguntas = 0;
    await usarPlaylistsDoFreddy(f.api, () => (perguntas++, true));
    expect(perguntas).toBe(1);
    expect(f.lista().map((p) => p.nome)).toEqual(["Mais nova", "Antiga"]);

    const outro = freddyFalso();
    await usarPlaylistsDoFreddy(outro.api, () => (perguntas++, true));
    expect(perguntas).toBe(1);
  });
});
