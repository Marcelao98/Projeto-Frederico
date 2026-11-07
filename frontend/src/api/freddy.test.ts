import { describe, expect, it, vi } from "vitest";
import { ApiFreddy, ErroDoFreddy, escolherFreddy, preferenciaEfetiva, vigiarFreddy } from "./freddy";

function falso(respostas: Record<string, { status?: number; corpo?: unknown } | "cai">) {
  const pedidos: { url: string; init?: RequestInit }[] = [];
  const buscar = (async (url: string, init?: RequestInit) => {
    pedidos.push({ url, init });
    const caminho = url.replace(/^http:\/\/[^/]+/, "");
    const r = respostas[caminho];
    if (!r || r === "cai") throw new TypeError("Failed to fetch");
    const status = r.status ?? 200;
    return new Response(status === 204 ? null : JSON.stringify(r.corpo ?? {}), { status });
  }) as unknown as typeof fetch;
  return { buscar, pedidos };
}

describe("ApiFreddy", () => {
  it("saúde: ligado ou desligado", async () => {
    const ligado = new ApiFreddy("x:1", falso({ "/saude": { corpo: { ok: true, versao: "0.2.0", protocolo: 1 } } }).buscar);
    expect((await ligado.saude())?.versao).toBe("0.2.0");
    const desligado = new ApiFreddy("x:1", falso({ "/saude": "cai" }).buscar);
    expect(await desligado.saude()).toBeNull();
  });

  it("erro do Freddy traz o motivo em português", async () => {
    const api = new ApiFreddy(
      "x:1",
      falso({ "/youtube/buscar": { status: 502, corpo: { detail: "o vídeo é privado" } } }).buscar,
    );
    await expect(api.buscarNoYoutube("x")).rejects.toThrow("o vídeo é privado");
  });

  it("busca livre sem resultado é null, não erro", async () => {
    const api = new ApiFreddy("x:1", falso({ "/youtube/buscar": { status: 404, corpo: { detail: "nada" } } }).buscar);
    expect(await api.buscarNoYoutube("x")).toBeNull();
  });

  it("aprender repetido vira ErroDoFreddy 409", async () => {
    const api = new ApiFreddy(
      "x:1",
      falso({ "/acervo/faixas": { status: 409, corpo: { detail: { erro: "essa música já está no acervo", faixa: {} } } } })
        .buscar,
    );
    const erro = await api.aprender({ titulo: "a", link: "b", temas: [] }).catch((e) => e);
    expect(erro).toBeInstanceOf(ErroDoFreddy);
    expect(erro.status).toBe(409);
    expect(erro.message).toBe("essa música já está no acervo");
  });

  it("playlists vão como JSON", async () => {
    const { buscar, pedidos } = falso({ "/playlists/a%20b": { corpo: { id: "a b" } }, "/playlists/z": { status: 204 } });
    const api = new ApiFreddy("x:1", buscar);
    await api.salvarPlaylist({ id: "a b", nome: "n", musicas: [], atualizadaEm: 1 });
    await api.excluirPlaylist("z");
    expect(pedidos.map((p) => p.init?.method)).toEqual(["PUT", "DELETE"]);
    expect(JSON.parse(String(pedidos[0].init?.body)).nome).toBe("n");
  });
});

describe("escolher o motor", () => {
  const ligado = () => new ApiFreddy("x:1", falso({ "/saude": { corpo: { ok: true } } }).buscar);
  const desligado = () => new ApiFreddy("x:1", falso({}).buscar);

  it("auto usa o Freddy só se ele responde", async () => {
    expect(await escolherFreddy("auto", ligado())).not.toBeNull();
    expect(await escolherFreddy("auto", desligado(), 2, 1)).toBeNull();
  });

  it("auto espera o Freddy que está acabando de ligar", async () => {
    let perguntas = 0;
    const api = new ApiFreddy("x:1", (async () => {
      perguntas += 1;
      if (perguntas < 3) throw new TypeError("Failed to fetch");
      return new Response(JSON.stringify({ ok: true }));
    }) as unknown as typeof fetch);
    expect(await escolherFreddy("auto", api, 4, 1)).not.toBeNull();
    expect(perguntas).toBe(3);
  });

  it("pelo navegador, avisa uma vez quando o Freddy liga", async () => {
    vi.useFakeTimers();
    let ligou = false;
    let avisos = 0;
    const api = new ApiFreddy("x:1", (async () => {
      if (!ligou) throw new TypeError("Failed to fetch");
      return new Response(JSON.stringify({ ok: true }));
    }) as unknown as typeof fetch);
    vigiarFreddy(() => avisos++, api, 1000);
    await vi.advanceTimersByTimeAsync(3000);
    expect(avisos).toBe(0);
    ligou = true;
    await vi.advanceTimersByTimeAsync(3000);
    expect(avisos).toBe(1);
    vi.useRealTimers();
  });

  it("navegador nunca usa; freddy usa mesmo desligado", async () => {
    expect(await escolherFreddy("navegador", ligado())).toBeNull();
    expect(await escolherFreddy("freddy", desligado())).not.toBeNull();
  });

  it("?motor= na URL ganha da preferência", () => {
    expect(preferenciaEfetiva("?motor=local")).toBe("navegador");
    expect(preferenciaEfetiva("?motor=freddy")).toBe("freddy");
    expect(preferenciaEfetiva("")).toBe("auto");
  });
});
