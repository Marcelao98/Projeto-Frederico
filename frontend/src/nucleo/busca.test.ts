// Os testes de busca do Bardo (modules/bardo/test_service.py), traduzidos,
// mais a checagem do acervo real.
import { describe, expect, it } from "vitest";
import musicasJson from "@dataset/musicas.json";
import vocabularioJson from "@dataset/vocabulario.json";
import { buscarPorTags, categoriasDosTemas, montarVocabulario, sortear } from "./busca";
import type { Faixa } from "./tipos";

const faixa = (id: string, nome: string, origem: string, temas: string[]): Faixa => ({
  id,
  nome,
  link: `https://www.youtube.com/watch?v=${id}`,
  escopo: "faixa_individual",
  origem: { nome: origem, tipo: "jogo" },
  temas,
});

const ACERVO: Faixa[] = [
  faixa("bloodborne-cleric-beast", "Cleric Beast", "Bloodborne", ["boss fight", "terror", "opressivo"]),
  faixa("bloodborne-dream-refuge", "Dream Refuge (Character Creation)", "Bloodborne", ["calmo", "hub", "atmosférico"]),
  faixa("hollow-knight-greenpath", "Greenpath", "Hollow Knight", ["exploração", "sereno", "calmo"]),
  faixa("hollow-knight-radiance", "Radiance (Final Boss)", "Hollow Knight", ["boss fight", "épico", "coral"]),
];
const VAZIO = montarVocabulario({ categorias: {} });
const ids = (q: string, faixas = ACERVO, voc = VAZIO) => new Set(buscarPorTags(q, faixas, voc).map((f) => f.id));

describe("busca booleana", () => {
  it("tema simples", () => expect(ids("terror")).toEqual(new Set(["bloodborne-cleric-beast"])));
  it("E entre tema e origem", () => expect(ids("calmo e hollow knight")).toEqual(new Set(["hollow-knight-greenpath"])));
  it("E falha quando falta um termo", () => expect(ids("terror e hollow knight").size).toBe(0));
  it("OU junta dois grupos", () =>
    expect(ids("terror ou epico")).toEqual(new Set(["bloodborne-cleric-beast", "hollow-knight-radiance"])));
  it("sem nega", () => expect(ids("bloodborne sem terror")).toEqual(new Set(["bloodborne-dream-refuge"])));
  it("ignora preenchimento", () =>
    expect(ids("uma musica de boss fight")).toEqual(new Set(["bloodborne-cleric-beast", "hollow-knight-radiance"])));
  it("ignora acento e maiúscula", () => expect(ids("ÉPICO")).toEqual(new Set(["hollow-knight-radiance"])));
  it("nome da faixa", () => expect(ids("greenpath")).toEqual(new Set(["hollow-knight-greenpath"])));
  it("vazia", () => {
    expect(ids("").size).toBe(0);
    expect(ids("musica de").size).toBe(0);
  });
  it("sem resultado", () => expect(ids("dark souls").size).toBe(0));
  it("OU tem precedência menor que E", () =>
    expect(ids("boss fight e bloodborne ou greenpath")).toEqual(
      new Set(["bloodborne-cleric-beast", "hollow-knight-greenpath"]),
    ));
});

describe("sinônimos", () => {
  const voc = montarVocabulario({
    categorias: {
      triste: { palavras: ["tristeza", "trágico", "melancólico"], temas: ["vazio"] },
      chefe: { palavras: ["chefão", "boss fight"], temas: [] },
      epico: { palavras: ["grandioso"], temas: ["coral"] },
    },
  });
  const comCategorias: Faixa[] = [
    { ...ACERVO[0], temas: ["boss fight", "trágico"], categorias: ["chefe", "triste"] },
    { ...ACERVO[3], temas: ["boss fight", "coral"], categorias: ["chefe", "epico"] },
  ];
  const q = (texto: string) => ids(texto, comCategorias, voc);

  it("monta categorias dos temas", () =>
    expect(categoriasDosTemas(["Trágico", "coral", "piano"], voc)).toEqual(["epico", "triste"]));
  it.each(["triste", "tristeza", "melancolico", "tragico"])("sinônimo %s acha a categoria", (t) =>
    expect(q(t)).toEqual(new Set(["bloodborne-cleric-beast"])));
  it("tema só puxa a faixa, não a categoria", () => {
    expect(q("coral")).toEqual(new Set(["hollow-knight-radiance"]));
    expect(q("grandioso")).toEqual(new Set(["hollow-knight-radiance"]));
  });
  it("frase com várias palavras", () => {
    expect(q("chefao triste")).toEqual(new Set(["bloodborne-cleric-beast"]));
    expect(q("uma musica de chefao para chorar").size).toBe(0);
    expect(q("hollow knight")).toEqual(new Set(["hollow-knight-radiance"]));
  });
  it("feminino cai na mesma categoria", () => {
    const v = montarVocabulario({
      categorias: { alegre: { palavras: ["animado"] }, terror: { palavras: ["assustador"] } },
    });
    expect(v.sinonimos.get("animada")).toEqual(new Set(["alegre"]));
    expect(v.sinonimos.get("assustadora")).toEqual(new Set(["terror"]));
    expect(categoriasDosTemas(["Animada"], v)).toEqual(["alegre"]);
  });
  it("negação com sinônimo", () => expect(q("chefao sem tristeza")).toEqual(new Set(["hollow-knight-radiance"])));
});

describe("acervo real", () => {
  const faixas = (musicasJson as { musicas: Faixa[] }).musicas;
  const voc = montarVocabulario(vocabularioJson);

  it("toda categoria do acervo existe no vocabulário", () => {
    const conhecidas = new Set([...voc.porTema.values()].flatMap((s) => [...s]));
    for (const f of faixas) for (const c of f.categorias ?? []) expect(conhecidas, f.id).toContain(c);
  });

  it("busca de verdade acha coisa", () => {
    expect(buscarPorTags("triste e bloodborne", faixas, voc).length).toBeGreaterThan(0);
    expect(buscarPorTags("chefe sem elden ring", faixas, voc).every((f) => f.origem.nome !== "Elden Ring")).toBe(true);
  });
});

describe("sortear", () => {
  it("não repete e respeita o máximo", () => {
    const s = sortear([...Array(40).keys()], 15);
    expect(s).toHaveLength(15);
    expect(new Set(s).size).toBe(15);
  });
  it("devolve tudo se couber", () => expect(sortear([1, 2, 3], 15)).toEqual([1, 2, 3]));
});
