import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MotorLocal } from "../../motor/motorLocal";
import type { OuvinteReprodutor, Reprodutor } from "../../motor/reprodutor";
import type { Musica } from "../../nucleo/tipos";
import { ligarNarrador, semNarrar, type Narrador } from "./narrador";

class Falso implements Reprodutor {
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

const m = (n: number): Musica => ({ titulo: `Música ${n}`, link: `https://youtu.be/v${n}` });

describe("narrador", () => {
  let narrador: Narrador;
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => {
    narrador?.desligar();
    vi.useRealTimers();
  });

  function novo() {
    const r = new Falso();
    const motor = new MotorLocal(r);
    const falas: string[] = [];
    narrador = ligarNarrador(motor, (t) => falas.push(t));
    return { r, motor, falas };
  }

  it("conta o que a Playlist fez", async () => {
    const { motor, falas } = novo();
    await motor.executar({ tipo: "adicionar", musicas: [m(1), m(2), m(3)] });
    vi.advanceTimersByTime(400);
    expect(falas).toEqual(["▶ Tocando **Música 1** · +2 na fila"]);
    await motor.executar({ tipo: "adicionar", musicas: [m(4)] });
    vi.advanceTimersByTime(400);
    expect(falas.at(-1)).toBe("+1 na fila");
    await motor.executar({ tipo: "pular" });
    vi.advanceTimersByTime(400);
    expect(falas.at(-1)).toBe("▶ Tocando **Música 2**");
    await motor.executar({ tipo: "limpar_fila" });
    vi.advanceTimersByTime(400);
    expect(falas.at(-1)).toBe("🧹 Fila vazia");
    await motor.executar({ tipo: "parar" });
    vi.advanceTimersByTime(400);
    expect(falas.at(-1)).toBe("⏹ Parou");
  });

  it("não repete o que o chat pediu", async () => {
    const { motor, falas } = novo();
    await semNarrar(() => motor.executar({ tipo: "adicionar", musicas: [m(1), m(2)] }));
    vi.advanceTimersByTime(400);
    await semNarrar(() => motor.executar({ tipo: "pular" }));
    vi.advanceTimersByTime(400);
    expect(falas).toEqual([]);
  });

  it("não repete a fila andando sozinha (o evento já conta)", async () => {
    const { r, motor, falas } = novo();
    await semNarrar(() => motor.executar({ tipo: "adicionar", musicas: [m(1), m(2)] }));
    r.ouvinte.fim();
    vi.advanceTimersByTime(400);
    r.ouvinte.fim();
    vi.advanceTimersByTime(400);
    expect(falas).toEqual([]);
  });

  it("reordenar e pausar não viram fala", async () => {
    const { motor, falas } = novo();
    await semNarrar(() => motor.executar({ tipo: "adicionar", musicas: [m(1), m(2), m(3)] }));
    const [a] = motor.estado().proximas;
    await motor.executar({ tipo: "mover", uid: a.uid, para: 1 });
    await motor.executar({ tipo: "pausar" });
    await motor.executar({ tipo: "embaralhar" });
    vi.advanceTimersByTime(400);
    expect(falas).toEqual([]);
  });
});
