import { afterEach, describe, expect, it } from "vitest";
import { montarAcervo } from "../../estado/acervo";
import { MotorLocal } from "../../navegador/motorLocal";
import type { OuvinteReprodutor, Reprodutor } from "../../navegador/reprodutor";
import type { Faixa } from "../../comum/tipos";
import { musicaDaFaixa } from "../../comum/tipos";
import { responder } from "./conversa";
import { esquecerRevisao, revisaoAberta, separarTemas } from "./revisao";

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

const faixa = (id: string, nome: string, temas: string[], categorias: string[] = temas): Faixa => ({
  id,
  nome,
  link: `https://www.youtube.com/watch?v=${id}`,
  escopo: "faixa_individual",
  origem: { nome: "Hollow Knight", tipo: "jogo" },
  temas,
  categorias,
});

function ctx(comFreddy = true) {
  const faixas = [
    faixa("a", "Greenpath", ["calmo"]),
    faixa("b", "Mantis Lords", ["não classificado"], []),
    faixa("c", "City of Tears", ["triste"]),
  ];
  const acervo = montarAcervo(faixas, { categorias: { calmo: {}, triste: {}, chefe: {} } });
  const gravados: [string, string[]][] = [];
  const editarTemas = async (id: string, temas: string[]) => {
    gravados.push([id, temas]);
    return { ...faixas.find((f) => f.id === id)!, temas, categorias: temas.filter((t) => t === "chefe") };
  };
  return { motor: new MotorLocal(new Mudo()), acervo, gravados, editarTemas: comFreddy ? editarTemas : undefined };
}

describe("revisão de temas pelo chat", () => {
  afterEach(esquecerRevisao);

  it("'temas' mostra os da que toca e pergunta se tá certo", async () => {
    const c = ctx();
    expect((await responder("temas", c)).texto).toContain("Não tem nada tocando");
    await c.motor.executar({ tipo: "adicionar", musicas: [musicaDaFaixa(c.acervo.porId("a")!)] });
    const r = await responder("temas", c);
    expect(r.texto).toContain("**Greenpath** (Hollow Knight)");
    expect(r.texto).toContain("Temas: calmo");
    expect(r.texto).toContain("Tá certo?");
    expect(r.revisao?.faixaId).toBe("a");
    expect((await responder("tá certo!", c)).texto).toBe("👍 Anotado.");
    expect(revisaoAberta()).toBeNull();
  });

  it("'não' pede os temas e a próxima mensagem vira os temas", async () => {
    const c = ctx();
    await c.motor.executar({ tipo: "adicionar", musicas: [musicaDaFaixa(c.acervo.porId("a")!)] });
    await responder("temas", c);
    expect((await responder("não", c)).texto).toContain("me diz os temas certos");
    const r = await responder("chefe, épico e tenso", c);
    expect(c.gravados).toEqual([["a", ["chefe", "épico", "tenso"]]]);
    expect(r.texto).toContain("agora é chefe, épico, tenso (na busca: chefe)");
  });

  it("pedido de música no meio da revisão continua sendo pedido", async () => {
    const c = ctx();
    await c.motor.executar({ tipo: "adicionar", musicas: [musicaDaFaixa(c.acervo.porId("a")!)] });
    await responder("temas", c);
    await responder("não", c);
    expect((await responder("pula", c)).texto).toContain("Pulei");
    expect(c.gravados).toEqual([]);
  });

  it("'temas: a, b' troca direto os da que toca", async () => {
    const c = ctx();
    await c.motor.executar({ tipo: "adicionar", musicas: [musicaDaFaixa(c.acervo.porId("c")!)] });
    const r = await responder("Freddy, temas: Triste, chuva", c);
    expect(c.gravados).toEqual([["c", ["triste", "chuva"]]]);
    expect(r.texto).toContain("Pronto: **City of Tears**");
  });

  it("'revisar' passa uma por uma, as sem tema primeiro, até acabar", async () => {
    const c = ctx();
    const r1 = await responder("revisar", c);
    expect(r1.texto).toContain("Bora revisar 3 faixas (1 sem tema primeiro)");
    expect(r1.texto).toContain("Revisão 1 de 3 · **Mantis Lords**");
    expect(r1.texto).toContain("sem temas");
    expect((await responder("sim", c)).texto).toContain("me diz quais são");
    const r2 = await responder("chefe, épico", c);
    expect(r2.texto).toContain("Revisão 2 de 3 · **Greenpath**");
    const r3 = await responder("ok", c);
    expect(r3.revisao?.faixaId).toBe("c");
    const fim = await responder("certo", c);
    expect(fim.texto).toContain("Revisão terminada (3 faixas)");
    expect(fim.revisao).toBeUndefined();
  });

  it("'revisar <busca>' e 'para de revisar'", async () => {
    const c = ctx();
    expect((await responder("revisar triste", c)).texto).toContain("Revisão 1 de 1 · **City of Tears**");
    expect((await responder("para de revisar", c)).texto).toBe("Beleza, parei.");
    expect((await responder("revisar xyz", c)).texto).toContain("Não achei nada");
  });

  it("sem o Freddy, mostra mas não grava", async () => {
    const c = ctx(false);
    await c.motor.executar({ tipo: "adicionar", musicas: [musicaDaFaixa(c.acervo.porId("a")!)] });
    await responder("temas", c);
    expect((await responder("temas: chefe", c)).texto).toContain("preciso do Freddy ligado");
  });

  it("link colado não tem temas", async () => {
    const c = ctx();
    await c.motor.executar({ tipo: "adicionar", musicas: [{ titulo: "Vídeo", link: "https://youtu.be/x" }] });
    expect((await responder("temas", c)).texto).toContain("não está no acervo");
  });

  it("separa os temas digitados", () => {
    expect(separarTemas("Taverna, alegre e calmo.")).toEqual(["taverna", "alegre", "calmo"]);
    expect(separarTemas("épico; épico / sombrio | x")).toEqual(["épico", "sombrio"]);
  });
});
