/**
 * Motor que mora no backend do Freddy (python -m freddy): fala por WebSocket.
 *
 * Mesmo contrato do MotorLocal: as telas não sabem a diferença. A fila, o
 * som e o relógio estão no backend; aqui fica só o último estado que ele
 * mandou. Se a conexão cai, avisa ("reconectando") e tenta de novo sozinho:
 * não troca escondido pro MotorLocal, senão a fila sumiria ou o som sairia
 * dobrado. Protocolo em backend/freddy/api/protocolo.py.
 */

import { VOLUME_PADRAO } from "../navegador/pedido";
import type {
  Comando,
  EstadoMotor,
  EventoMotor,
  Motor,
  NomeComando,
  Progresso,
  Resultado,
  SituacaoConexao,
} from "../motor/tipos";

export const PROTOCOLO = 1;
const PRAZO_DO_COMANDO_MS = 15_000;
const ESPERA_INICIAL_MS = 500;
const ESPERA_MAXIMA_MS = 5_000;

/** O pedaço do WebSocket que o motor usa (os testes passam um falso). */
export interface SocketMinimo {
  readonly readyState: number;
  send(dados: string): void;
  close(): void;
  onopen: ((e: unknown) => void) | null;
  onmessage: ((e: { data: unknown }) => void) | null;
  onclose: ((e: unknown) => void) | null;
  onerror: ((e: unknown) => void) | null;
}

const ABERTO = 1;

type MensagemDoFreddy =
  | { tipo: "ola"; protocolo: number; versao: string; som: string }
  | { tipo: "estado"; estado: EstadoMotor }
  | { tipo: "progresso"; posicao: number; duracao: number }
  | { tipo: "evento"; evento: EventoMotor }
  | { tipo: "resposta"; id: number | null; ok: boolean; resultado?: unknown; erro?: string }
  | { tipo: "pong" }
  | { tipo: "discord"; discord: unknown };

interface Pendente {
  resolver(r: unknown): void;
  rejeitar(e: Error): void;
  prazo: ReturnType<typeof setTimeout>;
}

export const ESTADO_INICIAL: EstadoMotor = {
  tocando: null,
  proximas: [],
  situacao: "parado",
  repetir: false,
  volume: VOLUME_PADRAO,
};

export class MotorRemoto implements Motor {
  private socket: SocketMinimo | null = null;
  private instantaneo: EstadoMotor = ESTADO_INICIAL;
  private prog: Progresso = { posicao: 0, duracao: 0 };
  private situacaoConexao: SituacaoConexao = "conectando";
  private proximoId = 1;
  private pendentes = new Map<number, Pendente>();
  private espera = ESPERA_INICIAL_MS;
  private religar: ReturnType<typeof setTimeout> | null = null;
  private fechado = false;
  /** Versão do Freddy do outro lado (do "ola"). */
  versaoDoFreddy: string | null = null;

  private ouvintes = new Set<() => void>();
  private ouvintesProgresso = new Set<() => void>();
  private ouvintesEvento = new Set<(e: EventoMotor) => void>();
  private ouvintesConexao = new Set<() => void>();
  private ouvintesExtras = new Map<string, Set<(dados: unknown) => void>>();

  constructor(
    private readonly url: string,
    private readonly criarSocket: (url: string) => SocketMinimo = (u) => new WebSocket(u) as unknown as SocketMinimo,
  ) {
    this.conectar();
  }

  estado = (): EstadoMotor => this.instantaneo;
  progresso = (): Progresso => this.prog;
  conexao = (): SituacaoConexao => this.situacaoConexao;

  inscrever = (ouvinte: () => void) => {
    this.ouvintes.add(ouvinte);
    return () => void this.ouvintes.delete(ouvinte);
  };
  inscreverProgresso = (ouvinte: () => void) => {
    this.ouvintesProgresso.add(ouvinte);
    return () => void this.ouvintesProgresso.delete(ouvinte);
  };
  aoEvento = (ouvinte: (e: EventoMotor) => void) => {
    this.ouvintesEvento.add(ouvinte);
    return () => void this.ouvintesEvento.delete(ouvinte);
  };
  inscreverConexao = (ouvinte: () => void) => {
    this.ouvintesConexao.add(ouvinte);
    return () => void this.ouvintesConexao.delete(ouvinte);
  };

  /** Mensagens do Freddy que não são do motor (ex.: "discord", o estado do bot). */
  aoMensagem(tipo: "discord", ouvinte: (dados: unknown) => void) {
    const ouvintes = this.ouvintesExtras.get(tipo) ?? new Set();
    ouvintes.add(ouvinte);
    this.ouvintesExtras.set(tipo, ouvintes);
    return () => void ouvintes.delete(ouvinte);
  }

  executar<K extends NomeComando>(comando: Comando<K>): Promise<Resultado<K>> {
    const socket = this.socket;
    if (!socket || socket.readyState !== ABERTO || this.situacaoConexao !== "conectado") {
      return Promise.reject(new Error("o Freddy está desconectado (confere se ele está ligado; tô tentando religar)"));
    }
    const id = this.proximoId++;
    return new Promise<Resultado<K>>((resolver, rejeitar) => {
      const prazo = setTimeout(() => {
        this.pendentes.delete(id);
        rejeitar(new Error("o Freddy demorou demais pra responder"));
      }, PRAZO_DO_COMANDO_MS);
      this.pendentes.set(id, { resolver: resolver as (r: unknown) => void, rejeitar, prazo });
      socket.send(JSON.stringify({ tipo: "comando", id, comando }));
    });
  }

  /** Desliga de vez (não tenta religar). */
  fechar() {
    this.fechado = true;
    if (this.religar !== null) clearTimeout(this.religar);
    this.socket?.close();
    this.socket = null;
  }

  // --- conexão -----------------------------------------------------------

  private conectar() {
    this.religar = null;
    let socket: SocketMinimo;
    try {
      socket = this.criarSocket(this.url);
    } catch {
      this.agendarReconexao();
      return;
    }
    this.socket = socket;
    socket.onmessage = (e) => {
      if (this.socket !== socket) return;
      this.receber(e.data);
    };
    socket.onclose = () => {
      if (this.socket !== socket) return;
      this.socket = null;
      this.cairConexao();
    };
    socket.onerror = () => {
      // O onclose vem logo depois e cuida de tudo.
    };
  }

  private cairConexao() {
    for (const [id, p] of this.pendentes) {
      clearTimeout(p.prazo);
      p.rejeitar(new Error("a conexão com o Freddy caiu"));
      this.pendentes.delete(id);
    }
    if (this.fechado) return;
    this.mudarConexao("reconectando");
    this.agendarReconexao();
  }

  private agendarReconexao() {
    if (this.fechado || this.religar !== null) return;
    this.religar = setTimeout(() => this.conectar(), this.espera);
    this.espera = Math.min(this.espera * 2, ESPERA_MAXIMA_MS);
  }

  private mudarConexao(situacao: SituacaoConexao) {
    if (situacao === this.situacaoConexao) return;
    this.situacaoConexao = situacao;
    for (const o of this.ouvintesConexao) o();
  }

  // --- mensagens ---------------------------------------------------------

  private receber(dados: unknown) {
    let msg: MensagemDoFreddy;
    try {
      msg = JSON.parse(String(dados)) as MensagemDoFreddy;
    } catch {
      return;
    }
    switch (msg.tipo) {
      case "ola":
        this.versaoDoFreddy = msg.versao;
        if (msg.protocolo !== PROTOCOLO) {
          console.warn(`Freddy fala o protocolo ${msg.protocolo}; o painel, o ${PROTOCOLO}. Atualize os dois.`);
        }
        this.espera = ESPERA_INICIAL_MS;
        this.mudarConexao("conectado");
        return;
      case "estado":
        this.instantaneo = msg.estado;
        for (const o of this.ouvintes) o();
        return;
      case "progresso":
        this.prog = { posicao: msg.posicao, duracao: msg.duracao };
        for (const o of this.ouvintesProgresso) o();
        return;
      case "evento":
        for (const o of this.ouvintesEvento) o(msg.evento);
        return;
      case "resposta": {
        if (msg.id === null) return;
        const p = this.pendentes.get(msg.id);
        if (!p) return;
        this.pendentes.delete(msg.id);
        clearTimeout(p.prazo);
        if (msg.ok) p.resolver(msg.resultado);
        else p.rejeitar(new Error(msg.erro ?? "o Freddy recusou o comando"));
        return;
      }
      case "pong":
        return;
      case "discord":
        for (const o of this.ouvintesExtras.get("discord") ?? []) o(msg.discord);
        return;
    }
  }
}
