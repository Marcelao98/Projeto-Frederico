import { describe, expect, it } from "vitest";
import type { Musica } from "../nucleo/tipos";
import { MotorLocal } from "./motorLocal";
import type { OuvinteReprodutor, Reprodutor } from "./reprodutor";
import { MAX_FILA, type EventoMotor } from "./tipos";

/** Reprodutor de mentira: guarda o que mandaram e deixa o teste disparar os eventos. */
class ReprodutorFalso implements Reprodutor {
  ouvinte!: OuvinteReprodutor;
  carregados: string[] = [];
  volume = 0;
  ouvir(o: OuvinteReprodutor) {
    this.ouvinte = o;
  }
  carregar(link: string) {
    this.carregados.push(link);
  }
  tocar() {}
  pausar() {}
  parar() {}
  buscar() {}
  definirVolume(v: number) {
    this.volume = v;
  }
  posicao() {
    return 0;
  }
  duracao() {
    return 0;
  }
}

const m = (n: number): Musica => ({ titulo: `Música ${n}`, link: `https://youtu.be/v${n}` });

function novo() {
  const r = new ReprodutorFalso();
  const motor = new MotorLocal(r);
  const eventos: EventoMotor[] = [];
  motor.aoEvento((e) => eventos.push(e));
  return { r, motor, eventos };
}

describe("MotorLocal", () => {
  it("a primeira começa a tocar e as outras entram na fila", async () => {
    const { r, motor } = novo();
    expect(await motor.executar({ tipo: "adicionar", musicas: [m(1), m(2)] })).toEqual({
      entraram: 2,
      posicao: 0,
      comecou: true,
    });
    expect(motor.estado().tocando?.titulo).toBe("Música 1");
    expect(motor.estado().proximas.map((x) => x.titulo)).toEqual(["Música 2"]);
    expect(r.carregados).toEqual(["https://youtu.be/v1"]);
    expect(await motor.executar({ tipo: "adicionar", musicas: [m(3)] })).toEqual({
      entraram: 1,
      posicao: 2,
      comecou: false,
    });
  });

  it("quando acaba, segue a fila e avisa", async () => {
    const { r, motor, eventos } = novo();
    await motor.executar({ tipo: "adicionar", musicas: [m(1), m(2)] });
    r.ouvinte.fim();
    expect(motor.estado().tocando?.titulo).toBe("Música 2");
    expect(eventos).toEqual([{ tipo: "tocando_agora", musica: motor.estado().tocando }]);
    r.ouvinte.fim();
    expect(motor.estado().tocando).toBeNull();
    expect(motor.estado().situacao).toBe("parado");
    expect(eventos.at(-1)).toEqual({ tipo: "fila_acabou" });
  });

  it("repetir toca a mesma de novo; pular desliga", async () => {
    const { r, motor } = novo();
    await motor.executar({ tipo: "adicionar", musicas: [m(1), m(2)] });
    expect(await motor.executar({ tipo: "repetir" })).toEqual({ repetir: true });
    r.ouvinte.fim();
    expect(motor.estado().tocando?.titulo).toBe("Música 1");
    expect(r.carregados).toEqual(["https://youtu.be/v1", "https://youtu.be/v1"]);
    expect(await motor.executar({ tipo: "pular" })).toEqual({ pulou: true, temProxima: true, repetiaAntes: true });
    expect(motor.estado().repetir).toBe(false);
    expect(motor.estado().tocando?.titulo).toBe("Música 2");
  });

  it("repetir sem nada tocando não liga", async () => {
    const { motor } = novo();
    expect(await motor.executar({ tipo: "repetir" })).toEqual({ repetir: false });
  });

  it("falha avisa, desliga o repetir e segue", async () => {
    const { r, motor, eventos } = novo();
    await motor.executar({ tipo: "adicionar", musicas: [m(1), m(2)] });
    await motor.executar({ tipo: "repetir" });
    r.ouvinte.erro("vídeo removido");
    expect(eventos[0]).toMatchObject({ tipo: "falha", motivo: "vídeo removido", musica: { titulo: "Música 1" } });
    expect(motor.estado().tocando?.titulo).toBe("Música 2");
    expect(motor.estado().repetir).toBe(false);
  });

  it("parar limpa tudo", async () => {
    const { motor } = novo();
    await motor.executar({ tipo: "adicionar", musicas: [m(1), m(2)] });
    expect(await motor.executar({ tipo: "parar" })).toEqual({ ok: true });
    expect(motor.estado()).toMatchObject({ tocando: null, proximas: [], situacao: "parado" });
  });

  it("pausar e continuar dependem da situação", async () => {
    const { r, motor } = novo();
    expect(await motor.executar({ tipo: "pausar" })).toEqual({ ok: false });
    await motor.executar({ tipo: "adicionar", musicas: [m(1)] });
    r.ouvinte.tocando();
    expect(await motor.executar({ tipo: "continuar" })).toEqual({ ok: false });
    expect(await motor.executar({ tipo: "pausar" })).toEqual({ ok: true });
    expect(await motor.executar({ tipo: "continuar" })).toEqual({ ok: true });
  });

  it("volume absoluto e relativo, limitado a 0-100", async () => {
    const { r, motor } = novo();
    expect(await motor.executar({ tipo: "volume", delta: 20 })).toEqual({ volume: 70 });
    expect(await motor.executar({ tipo: "volume", valor: 130 })).toEqual({ volume: 100 });
    expect(r.volume).toBe(100);
  });

  it("modo playlist: tocar agora, próxima, mover, remover, tocar item", async () => {
    const { motor } = novo();
    await motor.executar({ tipo: "adicionar", musicas: [m(1), m(2), m(3)] });
    await motor.executar({ tipo: "adicionar", musicas: [m(9)], onde: "proxima" });
    expect(motor.estado().proximas.map((x) => x.titulo)).toEqual(["Música 9", "Música 2", "Música 3"]);

    const [nove, dois, tres] = motor.estado().proximas;
    await motor.executar({ tipo: "mover", uid: nove.uid, para: 2 });
    expect(motor.estado().proximas.map((x) => x.uid)).toEqual([dois.uid, tres.uid, nove.uid]);

    await motor.executar({ tipo: "remover", uid: tres.uid });
    expect(motor.estado().proximas.map((x) => x.uid)).toEqual([dois.uid, nove.uid]);

    await motor.executar({ tipo: "tocar_item", uid: nove.uid });
    expect(motor.estado().tocando?.uid).toBe(nove.uid);
    expect(motor.estado().proximas.map((x) => x.uid)).toEqual([dois.uid]);

    await motor.executar({ tipo: "adicionar", musicas: [m(7)], onde: "agora" });
    expect(motor.estado().tocando?.titulo).toBe("Música 7");
  });

  it("respeita o limite da fila", async () => {
    const { motor } = novo();
    const muitas = Array.from({ length: MAX_FILA + 10 }, (_, i) => m(i));
    const r = await motor.executar({ tipo: "adicionar", musicas: muitas });
    // Como no Bardo: entram 50, uma começa a tocar e 49 esperam. Cabe mais uma.
    expect(r.entraram).toBe(MAX_FILA);
    expect((await motor.executar({ tipo: "adicionar", musicas: [m(998)] })).entraram).toBe(1);
    expect((await motor.executar({ tipo: "adicionar", musicas: [m(999)] })).entraram).toBe(0);
  });

  it("link colado ganha o título do vídeo; faixa do acervo mantém o nome", async () => {
    const { r, motor } = novo();
    await motor.executar({ tipo: "adicionar", musicas: [m(1)] });
    r.ouvinte.titulo("Nome Real do Vídeo");
    expect(motor.estado().tocando?.titulo).toBe("Nome Real do Vídeo");
    await motor.executar({ tipo: "adicionar", musicas: [{ ...m(2), faixaId: "x" }], onde: "agora" });
    r.ouvinte.titulo("Outro nome");
    expect(motor.estado().tocando?.titulo).toBe("Música 2");
  });
});
