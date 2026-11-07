import { afterEach, describe, expect, it } from "vitest";
import {
  acharPlaylist,
  adicionarNaPlaylist,
  excluirPlaylist,
  moverNaPlaylist,
  playlists,
  removerDaPlaylist,
  renomearPlaylist,
  salvarPlaylist,
} from "../../estado/playlists";
import { MotorLocal } from "../../navegador/motorLocal";
import type { OuvinteReprodutor, Reprodutor } from "../../navegador/reprodutor";
import type { Musica } from "../../comum/tipos";
import { previa, responder } from "./conversa";
import { montarAcervo } from "../../estado/acervo";

class Mudo implements Reprodutor {
  ouvir(_: OuvinteReprodutor) {}
  carregar() {}
  tocar() {}
  pausar() {}
  parar() {}
  buscar() {}
  definirVolume() {}
  posicao() {
    return 0;
  }
  duracao() {
    return 0;
  }
}

const m = (n: number): Musica => ({ titulo: `Música ${n}`, link: `https://www.youtube.com/watch?v=v${n}` });
const varias = (de: number, ate: number) => Array.from({ length: ate - de }, (_, i) => m(de + i));

function ctx() {
  return { motor: new MotorLocal(new Mudo()), acervo: montarAcervo([], { categorias: {} }) };
}

afterEach(() => {
  for (const p of playlists.ler()) excluirPlaylist(p.id);
});

describe("editar playlist salva", () => {
  it("renomear recusa nome repetido e vazio", () => {
    const a = salvarPlaylist("Sessão 12", [m(1)]);
    salvarPlaylist("Cripta", [m(2)]);
    expect(renomearPlaylist(a.id, "  cripta ")).toBe('já existe uma playlist "cripta"');
    expect(renomearPlaylist(a.id, " ")).toBe("o nome não pode ficar vazio");
    expect(renomearPlaylist(a.id, "Sessão 12 — a cripta")).toBeNull();
    expect(playlists.ler()[0].nome).toBe("Sessão 12 — a cripta");
  });

  it("pôr, tirar e mover música; mesmo vídeo não repete", () => {
    const p = salvarPlaylist("Taverna", [m(1), m(2)]);
    expect(adicionarNaPlaylist(p.id, m(3))).toBe("entrou");
    expect(adicionarNaPlaylist(p.id, { titulo: "outro nome", link: "https://youtu.be/v2" })).toBe("ja_estava");
    expect(adicionarNaPlaylist("nada", m(4))).toBe("sem_playlist");
    moverNaPlaylist(p.id, 2, 0);
    removerDaPlaylist(p.id, 1);
    expect(playlists.ler()[0].musicas.map((x) => x.titulo)).toEqual(["Música 3", "Música 2"]);
  });

  it("acha pelo nome sem precisar ser exato", () => {
    const lista = [
      salvarPlaylist("Sessão 12 — a cripta", []),
      salvarPlaylist("Sessão 13", []),
      salvarPlaylist("Taverna do Javali", []),
    ];
    const nomes = (t: string) => acharPlaylist(t, lista).map((p) => p.nome);
    expect(nomes("sessao 12")).toEqual(["Sessão 12 — a cripta"]);
    expect(nomes("Sessão 13")).toEqual(["Sessão 13"]);
    expect(nomes("sessão")).toEqual(["Sessão 12 — a cripta", "Sessão 13"]);
    expect(nomes("javali")).toEqual(["Taverna do Javali"]);
    expect(nomes("cripta 12")).toEqual(["Sessão 12 — a cripta"]);
    expect(nomes("dragão")).toEqual([]);
  });
});

describe("playlists pelo chat", () => {
  it("lista (ou diz que não tem)", async () => {
    const c = ctx();
    expect((await responder("playlists", c)).texto).toContain("Nenhuma playlist salva");
    salvarPlaylist("Cripta", [m(1), m(2)]);
    const r = await responder("quais as playlists?", c);
    expect(r.texto).toContain("**Cripta** (2 músicas)");
  });

  it("salva a fila (a que toca + as próximas) e atualiza com o mesmo nome", async () => {
    const c = ctx();
    expect((await responder("salva a fila como Sessão 12", c)).texto).toContain("fila está vazia");
    await c.motor.executar({ tipo: "adicionar", musicas: [m(1), m(2), m(3)] });
    expect((await responder("salva a fila como Sessão 12", c)).texto).toBe("Salvei a playlist **Sessão 12** com 3 músicas 💾");
    expect(playlists.ler()[0].musicas.map((x) => x.titulo)).toEqual(["Música 1", "Música 2", "Música 3"]);
    expect((await responder('Freddy, salva a fila como "sessão 12"', c)).texto).toContain("Atualizei");
    expect(playlists.ler()).toHaveLength(1);
  });

  it("toca a playlist: troca a fila inteira", async () => {
    const c = ctx();
    salvarPlaylist("Sessão 12 — a cripta", [m(10), m(11)]);
    await c.motor.executar({ tipo: "adicionar", musicas: [m(1), m(2)] });
    const r = await responder("toca a playlist sessao 12", c);
    expect(r.texto).toContain("Tocando a playlist **Sessão 12 — a cripta** 🎵 (2 músicas)");
    expect(c.motor.estado().tocando?.titulo).toBe("Música 10");
    expect(c.motor.estado().proximas.map((x) => x.titulo)).toEqual(["Música 11"]);
  });

  it("põe a playlist na fila: acrescenta sem parar o que toca", async () => {
    const c = ctx();
    salvarPlaylist("Cripta", [m(10), m(11)]);
    await c.motor.executar({ tipo: "adicionar", musicas: [m(1)] });
    expect((await responder("põe a playlist cripta na fila", c)).texto).toContain("Pus a playlist **Cripta** na fila (2 músicas)");
    expect(c.motor.estado().tocando?.titulo).toBe("Música 1");
    expect(c.motor.estado().proximas).toHaveLength(2);
  });

  it("avisa quando não cabe tudo na fila", async () => {
    const c = ctx();
    salvarPlaylist("Enorme", varias(0, 62));
    const r = await responder("toca a playlist enorme", c);
    expect(r.texto).toContain("Entraram 51 de 62: a fila encheu");
  });

  it("nome que bate com várias pergunta qual; nome que não existe lista as que tem", async () => {
    const c = ctx();
    salvarPlaylist("Sessão 12", [m(1)]);
    salvarPlaylist("Sessão 13", [m(2)]);
    expect((await responder("toca a playlist sessão", c)).texto).toContain("Tenho mais de uma");
    expect((await responder("toca a playlist dragão", c)).texto).toContain('Não achei a playlist "dragão". Tenho:');
    expect(c.motor.estado().tocando).toBeNull();
  });

  it("'mostra a fila' continua sendo a fila, e a prévia entende os comandos novos", async () => {
    const c = ctx();
    expect((await responder("fila", c)).texto).toContain("fila está vazia");
    expect(previa("toca a playlist cripta", c.acervo)).toEqual({ tipo: "acervo", descricao: "tocar a playlist (troca a fila)" });
    expect(previa("salva a fila como x", c.acervo)).toEqual({ tipo: "acervo", descricao: "salvar a fila como playlist" });
  });
});
