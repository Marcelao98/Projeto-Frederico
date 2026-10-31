// Os testes de pedido do Bardo (modules/bardo/test_service.py), traduzidos.
import { describe, expect, it } from "vitest";
import { PASSO_VOLUME, interpretarPedido } from "./pedido";

const LINK = "https://www.youtube.com/watch?v=dQw4w9WgXcQ";

describe("tocar", () => {
  it.each(["toca", "toque", "tocar", "bota", "coloca", "põe", "play"])("gatilho %s com link", (verbo) => {
    expect(interpretarPedido(`freddy ${verbo} ${LINK}`)).toEqual({ acao: "tocar", link: LINK });
  });

  it("youtu.be com querystring", () => {
    const link = "https://youtu.be/dQw4w9WgXcQ?si=abc&list=PL123";
    expect(interpretarPedido(`freddy toca ${link}`)).toEqual({ acao: "tocar", link });
  });

  it("sem link vira busca", () => {
    expect(interpretarPedido("freddy toca triste e bloodborne")).toEqual({ acao: "tocar", busca: "triste e bloodborne" });
    expect(interpretarPedido("<@123> play boss fight!")).toEqual({ acao: "tocar", busca: "boss fight" });
    expect(interpretarPedido("Frederico, toca a música da taverna")).toEqual({
      acao: "tocar",
      busca: "a música da taverna",
    });
  });

  it("sem link nem busca", () => {
    expect(interpretarPedido("freddy toca")).toEqual({ acao: "tocar" });
  });

  it("'para' na frase não para", () => {
    expect(interpretarPedido(`freddy toca essa para mim ${LINK}`)).toEqual({ acao: "tocar", link: LINK });
    for (const texto of ["freddy toca uma música para relaxar", "freddy bota algo de taverna para o combate"]) {
      expect(interpretarPedido(texto)?.acao).toBe("tocar");
    }
  });

  it("adicionar é tocar", () => {
    for (const texto of [`freddy adiciona ${LINK}`, `freddy coloca na fila ${LINK}`, `freddy add ${LINK}`]) {
      expect(interpretarPedido(texto)).toEqual({ acao: "tocar", link: LINK });
    }
  });
});

describe("controles", () => {
  it.each(["freddy pausa", "freddy, pause a música", "freddy pausar"])("pausar: %s", (t) => {
    expect(interpretarPedido(t)).toEqual({ acao: "pausar" });
  });
  it.each(["freddy continua", "freddy volta a tocar", "freddy despausa", "freddy retoma"])("continuar: %s", (t) => {
    expect(interpretarPedido(t)).toEqual({ acao: "continuar" });
  });
  it.each(["freddy para", "freddy para de tocar", "freddy stop", "freddy chega", "freddy para a música"])(
    "parar: %s",
    (t) => expect(interpretarPedido(t)).toEqual({ acao: "parar" }),
  );
  it.each(["freddy", "freddy bom dia", "freddy rola 1d20", "freddy para de transcrever"])("não é pedido: %s", (t) => {
    expect(interpretarPedido(t)).toBeNull();
  });
  it.each(["freddy pula", "freddy próxima", "freddy proxima", "freddy toca a próxima", "freddy skip"])(
    "pular: %s",
    (t) => expect(interpretarPedido(t)).toEqual({ acao: "pular" }),
  );
  it.each(["freddy fila", "freddy mostra a fila", "freddy qual a playlist?"])("fila: %s", (t) => {
    expect(interpretarPedido(t)).toEqual({ acao: "fila" });
  });
  it.each(["freddy limpa a fila", "freddy esvazia a fila", "freddy zera a playlist"])("limpar fila: %s", (t) => {
    expect(interpretarPedido(t)).toEqual({ acao: "limpar_fila" });
  });
});

describe("repetir", () => {
  it.each(["freddy repete", "freddy, repete", "freddy repetir", "freddy repita essa", "freddy loop"])(
    "alterna: %s",
    (t) => expect(interpretarPedido(t)).toEqual({ acao: "repetir" }),
  );
  it.each([
    "freddy para de repetir",
    "freddy pare de repetir",
    "freddy repete não",
    "freddy não repete",
    "freddy chega de loop",
    "freddy desliga o repetir",
    "freddy tira o loop",
  ])("desliga: %s", (t) => expect(interpretarPedido(t)).toEqual({ acao: "repetir", ligar: false }));

  it("toca antes do repete é busca", () => {
    expect(interpretarPedido("freddy toca Repete Comigo")).toEqual({ acao: "tocar", busca: "Repete Comigo" });
  });
});

describe("volume", () => {
  it("absoluto e limitado", () => {
    expect(interpretarPedido("freddy volume 30")).toEqual({ acao: "volume", volume: 30 });
    expect(interpretarPedido("freddy coloca o volume em 75%")).toEqual({ acao: "volume", volume: 75 });
    expect(interpretarPedido("freddy volume 250")).toEqual({ acao: "volume", volume: 100 });
  });
  it("relativo", () => {
    expect(interpretarPedido("freddy aumenta o volume")).toEqual({ acao: "volume", delta: PASSO_VOLUME });
    expect(interpretarPedido("freddy abaixa")).toEqual({ acao: "volume", delta: -PASSO_VOLUME });
    expect(interpretarPedido("freddy mais baixo")).toEqual({ acao: "volume", delta: -PASSO_VOLUME });
  });
  it("pergunta", () => {
    expect(interpretarPedido("freddy qual o volume?")).toEqual({ acao: "volume" });
  });
});
