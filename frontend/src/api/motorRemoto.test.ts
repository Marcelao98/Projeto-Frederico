import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MotorRemoto, type SocketMinimo } from "./motorRemoto";
import type { EstadoMotor, EventoMotor } from "../motor/tipos";

/** WebSocket de mentira: o teste faz o papel do Freddy. */
class SocketFalso implements SocketMinimo {
  readyState = 0;
  enviadas: Record<string, unknown>[] = [];
  onopen: ((e: unknown) => void) | null = null;
  onmessage: ((e: { data: unknown }) => void) | null = null;
  onclose: ((e: unknown) => void) | null = null;
  onerror: ((e: unknown) => void) | null = null;
  constructor(public url: string) {}
  send(dados: string) {
    this.enviadas.push(JSON.parse(dados));
  }
  close() {
    this.readyState = 3;
  }
  // do lado do "Freddy":
  abrir() {
    this.readyState = 1;
    this.onopen?.({});
    this.mandar({ tipo: "ola", protocolo: 1, versao: "0.2.0", som: "local" });
  }
  mandar(msg: unknown) {
    this.onmessage?.({ data: JSON.stringify(msg) });
  }
  cair() {
    this.readyState = 3;
    this.onclose?.({});
  }
}

const estado = (parcial: Partial<EstadoMotor>): EstadoMotor => ({
  tocando: null,
  proximas: [],
  situacao: "parado",
  repetir: false,
  volume: 50,
  ...parcial,
});

function novo() {
  const sockets: SocketFalso[] = [];
  const motor = new MotorRemoto("ws://127.0.0.1:47824/ws", (url) => {
    const s = new SocketFalso(url);
    sockets.push(s);
    return s;
  });
  return { motor, sockets, atual: () => sockets[sockets.length - 1] };
}

describe("MotorRemoto", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("conecta e fica conectado depois do 'ola'", () => {
    const { motor, atual } = novo();
    expect(motor.conexao()).toBe("conectando");
    atual().abrir();
    expect(motor.conexao()).toBe("conectado");
    expect(motor.versaoDoFreddy).toBe("0.2.0");
  });

  it("estado e progresso vêm do Freddy e avisam quem ouve", () => {
    const { motor, atual } = novo();
    atual().abrir();
    const avisos: string[] = [];
    motor.inscrever(() => avisos.push("estado"));
    motor.inscreverProgresso(() => avisos.push("progresso"));
    const tocando = { titulo: "Música 1", link: "https://youtu.be/v1", uid: "a" };
    atual().mandar({ tipo: "estado", estado: estado({ tocando, situacao: "tocando" }) });
    atual().mandar({ tipo: "progresso", posicao: 12, duracao: 200 });
    expect(motor.estado().tocando?.titulo).toBe("Música 1");
    expect(motor.progresso()).toEqual({ posicao: 12, duracao: 200 });
    expect(avisos).toEqual(["estado", "progresso"]);
  });

  it("comando vai com id e a promessa resolve com a resposta", async () => {
    const { motor, atual } = novo();
    atual().abrir();
    const promessa = motor.executar({ tipo: "volume", valor: 30 });
    expect(atual().enviadas).toEqual([{ tipo: "comando", id: 1, comando: { tipo: "volume", valor: 30 } }]);
    atual().mandar({ tipo: "resposta", id: 1, ok: true, resultado: { volume: 30 } });
    await expect(promessa).resolves.toEqual({ volume: 30 });
  });

  it("comando recusado vira erro", async () => {
    const { motor, atual } = novo();
    atual().abrir();
    const promessa = motor.executar({ tipo: "pular" });
    atual().mandar({ tipo: "resposta", id: 1, ok: false, erro: "comando inválido" });
    await expect(promessa).rejects.toThrow("comando inválido");
  });

  it("sem conexão, o comando falha na hora (não fica esperando)", async () => {
    const { motor } = novo();
    await expect(motor.executar({ tipo: "pular" })).rejects.toThrow("desconectado");
  });

  it("eventos do Freddy chegam pro chat", () => {
    const { motor, atual } = novo();
    atual().abrir();
    const eventos: EventoMotor[] = [];
    motor.aoEvento((e) => eventos.push(e));
    atual().mandar({ tipo: "evento", evento: { tipo: "fila_acabou" } });
    expect(eventos).toEqual([{ tipo: "fila_acabou" }]);
  });

  it("se a conexão cai: rejeita o que estava pendente, avisa e religa sozinho", async () => {
    const { motor, sockets, atual } = novo();
    atual().abrir();
    const situacoes: string[] = [];
    motor.inscreverConexao(() => situacoes.push(motor.conexao()));
    const promessa = motor.executar({ tipo: "pular" });
    atual().cair();
    await expect(promessa).rejects.toThrow("caiu");
    expect(motor.conexao()).toBe("reconectando");
    expect(sockets).toHaveLength(1);
    vi.advanceTimersByTime(500);
    expect(sockets).toHaveLength(2);
    atual().cair(); // ainda desligado: espera o dobro
    vi.advanceTimersByTime(500);
    expect(sockets).toHaveLength(2);
    vi.advanceTimersByTime(500);
    expect(sockets).toHaveLength(3);
    atual().abrir();
    expect(situacoes).toEqual(["reconectando", "conectado"]);
  });

  it("comando sem resposta expira", async () => {
    const { motor, atual } = novo();
    atual().abrir();
    const promessa = motor.executar({ tipo: "pular" });
    vi.advanceTimersByTime(15_000);
    await expect(promessa).rejects.toThrow("demorou");
  });

  it("o estado do Discord chega por fora do motor", () => {
    const { motor, atual } = novo();
    atual().abrir();
    const recebidos: unknown[] = [];
    motor.aoMensagem("discord", (d) => recebidos.push(d));
    atual().mandar({ tipo: "discord", discord: { situacao: "conectado" } });
    expect(recebidos).toEqual([{ situacao: "conectado" }]);
  });

  it("fechar não religa", () => {
    const { motor, sockets, atual } = novo();
    atual().abrir();
    motor.fechar();
    vi.advanceTimersByTime(10_000);
    expect(sockets).toHaveLength(1);
  });
});
