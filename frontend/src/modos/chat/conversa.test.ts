import { describe, expect, it } from "vitest";
import { montarAcervo } from "../../dados/acervo";
import { MotorLocal } from "../../motor/motorLocal";
import type { OuvinteReprodutor, Reprodutor } from "../../motor/reprodutor";
import type { Faixa } from "../../nucleo/tipos";
import { AJUDA, previa, responder, responderEraEssa, separarTemas, termoEmDigitacao } from "./conversa";

class Mudo implements Reprodutor {
  ouvinte!: OuvinteReprodutor;
  ouvir(o: OuvinteReprodutor) {
    this.ouvinte = o;
  }
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

const faixa = (id: string, nome: string, origem: string, categorias: string[]): Faixa => ({
  id,
  nome,
  link: `https://www.youtube.com/watch?v=${id}`,
  escopo: "faixa_individual",
  origem: { nome: origem, tipo: "jogo" },
  temas: categorias,
  categorias,
});

function ctx() {
  const acervo = montarAcervo(
    [
      faixa("a", "Cleric Beast", "Bloodborne", ["chefe", "terror"]),
      faixa("b", "Hunter's Dream", "Bloodborne", ["calmo", "triste"]),
      faixa("c", "Greenpath", "Hollow Knight", ["calmo", "exploracao"]),
    ],
    { categorias: { calmo: { palavras: ["tranquilo"] }, triste: {}, chefe: {}, terror: {}, exploracao: {} } },
  );
  const reprodutor = new Mudo();
  return { motor: new MotorLocal(reprodutor), acervo, reprodutor };
}

describe("conversa", () => {
  it("busca no acervo e toca, aceitando o nome do Freddy na frente", async () => {
    const c = ctx();
    const r = await responder("Freddy, toca triste e bloodborne", c);
    expect(r.texto).toBe("Tocando **Hunter's Dream** 🎵");
    expect(r.musicas?.map((m) => m.faixaId)).toEqual(["b"]);
    expect((await responder("toca tranquilo", c)).texto).toBe("Adicionei 2 músicas na fila 📜");
  });

  it("link colado usa o título descoberto", async () => {
    const c = ctx();
    const r = await responder("toca https://youtu.be/xyz", { ...c, tituloDoLink: async () => "Garçom" });
    expect(r.texto).toBe("Tocando **Garçom** 🎵");
    const r2 = await responder("bota https://youtu.be/abc", c);
    expect(r2.texto).toBe("Adicionei **Link do YouTube** na fila (posição 1) 📜");
  });

  it("controles respondem como o Bardo", async () => {
    const c = ctx();
    expect((await responder("pula", c)).texto).toBe("Não tem nada tocando.");
    expect((await responder("repete", c)).texto).toBe("Não tem nada tocando pra repetir.");
    await responder("toca calmo", c);
    c.reprodutor.ouvinte.tocando();
    expect((await responder("repete", c)).texto).toMatch(/^🔁 Repetindo/);
    expect((await responder("fila", c)).texto).toMatch(/🔁 \(repetindo\)/);
    expect((await responder("pausa", c)).texto).toBe("Pausei ⏸️");
    expect((await responder("continua", c)).texto).toBe("Continuando ▶️");
    expect((await responder("volume 30", c)).texto).toBe("Volume em 30% 🔊");
    expect((await responder("qual o volume?", c)).texto).toBe("O volume está em 30%.");
    expect((await responder("pula", c)).texto).toBe("Pulei ⏭️ (repetição desligada)");
    expect((await responder("para", c)).texto).toBe("Parei ⏹️");
  });

  it("não achou, ajuda e não entendi", async () => {
    const c = ctx();
    expect((await responder("toca dark souls", c)).texto).toMatch(/^Não achei nada pra "dark souls"/);
    expect((await responder("ajuda", c)).texto).toBe(AJUDA);
    expect((await responder("fred, socorro", c)).texto).toBe(AJUDA);
    expect((await responder("bom dia", c)).texto).toMatch(/^Não entendi/);
  });
});

describe("prévia e autocompletar", () => {
  it("prévia diz o que vai acontecer", () => {
    const { acervo } = ctx();
    expect(previa("freddy toca calmo", acervo)).toEqual({ tipo: "busca", busca: "calmo", total: 2 });
    expect(previa("pula", acervo)).toEqual({ tipo: "comando", acao: "pular" });
    expect(previa("toca https://youtu.be/x", acervo)).toEqual({ tipo: "link" });
    expect(previa("oi", acervo)).toBeNull();
  });

  it("acha o termo que está sendo digitado", () => {
    expect(termoEmDigitacao("toca triste e bloo")).toEqual({ termo: "bloo", inicio: 14 });
    expect(termoEmDigitacao("Freddy, bota cal")).toEqual({ termo: "cal", inicio: 13 });
    expect(termoEmDigitacao("toca chefe sem eld")).toEqual({ termo: "eld", inicio: 15 });
    expect(termoEmDigitacao("pula")).toBeNull();
    expect(termoEmDigitacao("toca ")).toBeNull();
  });

  it("sem nada no acervo e com o Freddy: busca no YouTube e pergunta se era essa", async () => {
    const c = ctx();
    const achada = { titulo: "Taverna Medieval", link: "https://www.youtube.com/watch?v=tav" };
    const r = await responder("toca taverna medieval", { ...c, buscarNoYoutube: async () => achada });
    expect(r.texto).toContain("procurei no YouTube: **Taverna Medieval**, tocando");
    expect(r.pergunta).toEqual(achada);
    expect(c.motor.estado().tocando?.link).toBe(achada.link);

    const nada = await responder("toca xyz", { ...c, buscarNoYoutube: async () => null });
    expect(nada.texto).toContain("nem no acervo nem no YouTube");
    const erro = await responder("toca xyz", {
      ...c,
      buscarNoYoutube: async () => {
        throw new Error("o vídeo é privado");
      },
    });
    expect(erro.texto).toContain("(o vídeo é privado)");
    expect((await responder("toca xyz", c)).texto).toContain("Com o Freddy ligado");
  });

  it("era essa? sim guarda com os climas; não pula se ainda toca", async () => {
    const c = ctx();
    const musica = { titulo: "Taverna", link: "https://youtu.be/t" };
    const aprendidas: unknown[] = [];
    const professor = {
      aprender: async (f: { temas: string[] }) => {
        aprendidas.push(f);
        return { nome: "Taverna" };
      },
    };
    const sim = await responderEraEssa(musica, ["taverna", "alegre"], { motor: c.motor, professor });
    expect(sim.texto).toContain("como **taverna**, **alegre**");
    expect(aprendidas).toEqual([{ titulo: "Taverna", link: "https://youtu.be/t", temas: ["taverna", "alegre"] }]);

    await c.motor.executar({ tipo: "adicionar", musicas: [musica] });
    const nao = await responderEraEssa(musica, null, { motor: c.motor, professor });
    expect(nao.texto).toContain("pulei");
    expect(c.motor.estado().tocando).toBeNull();

    const repetida = await responderEraEssa(musica, [], {
      motor: c.motor,
      professor: { aprender: () => Promise.reject(Object.assign(new Error("já"), { status: 409 })) },
    });
    expect(repetida.texto).toContain("já estava no acervo");
  });

  it("separa os climas digitados", () => {
    expect(separarTemas("Taverna, alegre e calmo")).toEqual(["taverna", "alegre", "calmo"]);
    expect(separarTemas("  ")).toEqual([]);
    expect(separarTemas("épico; épico / sombrio")).toEqual(["épico", "sombrio"]);
  });
});
