/**
 * Motor que roda inteiro no navegador: guarda a fila e manda o Reprodutor
 * tocar. É o "Bardo sem Discord" do painel, até o backend existir.
 */

import { VOLUME_PADRAO, limitarVolume } from "../nucleo/pedido";
import * as F from "./fila";
import type { Reprodutor } from "./reprodutor";
import type {
  Comando,
  EstadoMotor,
  EventoMotor,
  ItemDaFila,
  Motor,
  NomeComando,
  Progresso,
  Resultado,
  Situacao,
} from "./tipos";

const INTERVALO_DO_PROGRESSO_MS = 500;

export class MotorLocal implements Motor {
  private fila: F.Fila = F.FILA_VAZIA;
  private situacao: Situacao = "parado";
  private volume = VOLUME_PADRAO;
  private instantaneo: EstadoMotor;
  private prog: Progresso = { posicao: 0, duracao: 0 };
  private ouvintes = new Set<() => void>();
  private ouvintesProgresso = new Set<() => void>();
  private ouvintesEvento = new Set<(e: EventoMotor) => void>();
  private relogio: ReturnType<typeof setInterval> | null = null;

  constructor(private readonly reprodutor: Reprodutor) {
    this.instantaneo = this.montarEstado();
    reprodutor.definirVolume(this.volume);
    reprodutor.ouvir({
      tocando: () => this.mudar({ situacao: "tocando" }),
      pausado: () => this.mudar({ situacao: "pausado" }),
      fim: () => this.aoTerminar(),
      erro: (motivo) => this.aoFalhar(motivo),
      titulo: (titulo) => this.aoDescobrirTitulo(titulo),
    });
  }

  estado = (): EstadoMotor => this.instantaneo;
  progresso = (): Progresso => this.prog;

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

  async executar<K extends NomeComando>(comando: Comando<K>): Promise<Resultado<K>> {
    return this.rodar(comando as Comando) as Resultado<K>;
  }

  private rodar(c: Comando): Resultado<NomeComando> {
    switch (c.tipo) {
      case "adicionar": {
        const nadaTocava = this.fila.tocando === null;
        const onde = c.onde ?? "fim";
        const r = F.adicionar(this.fila, c.musicas, nadaTocava && onde !== "agora" ? "fim" : onde);
        if (!r.entraram) return { entraram: 0, posicao: -1, comecou: false };
        if (nadaTocava || onde === "agora") {
          // "agora" já põe a primeira tocando; avançar aqui jogaria ela fora.
          this.fila = nadaTocava && onde !== "agora" ? F.avancar(r.fila) : r.fila;
          this.tocarAtual();
          return { entraram: r.entraram, posicao: 0, comecou: true };
        }
        this.mudarFila(r.fila);
        return { entraram: r.entraram, posicao: r.posicao, comecou: false };
      }
      case "pular": {
        if (!this.fila.tocando) return { pulou: false, temProxima: false, repetiaAntes: false };
        // Pular é "chega dessa": desliga o repetir, senão a próxima também
        // entraria em loop sem ninguém pedir.
        const repetiaAntes = this.fila.repetir;
        const temProxima = this.fila.proximas.length > 0;
        this.fila = F.avancar({ ...this.fila, repetir: false });
        this.tocarAtual();
        if (!temProxima) this.emitir({ tipo: "fila_acabou" });
        return { pulou: true, temProxima, repetiaAntes };
      }
      case "pausar": {
        if (this.situacao !== "tocando" && this.situacao !== "carregando") return { ok: false };
        this.reprodutor.pausar();
        this.mudar({ situacao: "pausado" });
        return { ok: true };
      }
      case "continuar": {
        if (this.situacao !== "pausado") return { ok: false };
        this.reprodutor.tocar();
        this.mudar({ situacao: "tocando" });
        return { ok: true };
      }
      case "alternar_pausa":
        return this.situacao === "pausado" ? this.rodar({ tipo: "continuar" }) : this.rodar({ tipo: "pausar" });
      case "parar": {
        const tinha = this.fila.tocando !== null;
        this.fila = F.resetar();
        this.tocarAtual();
        return { ok: tinha };
      }
      case "limpar_fila": {
        const removidas = this.fila.proximas.length;
        this.mudarFila(F.limpar(this.fila));
        return { removidas };
      }
      case "repetir": {
        const repetir = c.ligar ?? !this.fila.repetir;
        this.mudarFila({ ...this.fila, repetir: repetir && this.fila.tocando !== null });
        return { repetir: this.fila.repetir };
      }
      case "volume": {
        const volume = limitarVolume(c.valor ?? this.volume + (c.delta ?? 0));
        this.volume = volume;
        this.reprodutor.definirVolume(volume);
        this.mudar({});
        return { volume };
      }
      case "remover": {
        const antes = this.fila.proximas.length;
        this.mudarFila(F.remover(this.fila, c.uid));
        return { ok: this.fila.proximas.length < antes };
      }
      case "mover":
        this.mudarFila(F.mover(this.fila, c.uid, c.para));
        return { ok: true };
      case "tocar_item": {
        const nova = F.tocarItem(this.fila, c.uid);
        if (nova === this.fila) return { ok: false };
        this.fila = nova;
        this.tocarAtual();
        return { ok: true };
      }
      case "embaralhar":
        this.mudarFila(F.embaralhar(this.fila));
        return { ok: true };
      case "buscar_posicao":
        if (!this.fila.tocando) return { ok: false };
        this.reprodutor.buscar(c.segundos);
        this.prog = { ...this.prog, posicao: c.segundos };
        this.avisarProgresso();
        return { ok: true };
    }
  }

  // --- tocar -------------------------------------------------------------

  private tocarAtual() {
    const atual = this.fila.tocando;
    this.prog = { posicao: 0, duracao: atual?.duracaoSegundos ?? 0 };
    this.avisarProgresso();
    if (!atual) {
      this.reprodutor.parar();
      this.pararRelogio();
      this.mudar({ situacao: "parado" });
      return;
    }
    this.reprodutor.carregar(atual.link);
    this.ligarRelogio();
    this.mudar({ situacao: "carregando" });
  }

  private aoTerminar() {
    const acabou = this.fila.tocando;
    if (!acabou) return;
    if (this.fila.repetir) {
      this.reprodutor.carregar(acabou.link);
      this.mudar({ situacao: "carregando" });
      return;
    }
    this.seguirFila();
  }

  private aoFalhar(motivo: string) {
    const falhou = this.fila.tocando;
    if (!falhou) return;
    this.emitir({ tipo: "falha", musica: falhou, motivo });
    this.fila = { ...this.fila, repetir: false };
    this.seguirFila();
  }

  private seguirFila() {
    this.fila = F.avancar(this.fila);
    this.tocarAtual();
    if (this.fila.tocando) this.emitir({ tipo: "tocando_agora", musica: this.fila.tocando });
    else this.emitir({ tipo: "fila_acabou" });
  }

  /** Link colado vem sem título; quando o player descobre, a fila mostra o certo. */
  private aoDescobrirTitulo(titulo: string) {
    const atual = this.fila.tocando;
    if (!atual || atual.faixaId || !titulo || atual.titulo === titulo) return;
    this.mudarFila({ ...this.fila, tocando: { ...atual, titulo } });
  }

  private ligarRelogio() {
    if (this.relogio !== null) return;
    this.relogio = setInterval(() => {
      const posicao = this.reprodutor.posicao();
      const duracao = this.reprodutor.duracao() || this.prog.duracao;
      if (posicao !== this.prog.posicao || duracao !== this.prog.duracao) {
        this.prog = { posicao, duracao };
        this.avisarProgresso();
      }
    }, INTERVALO_DO_PROGRESSO_MS);
  }

  private pararRelogio() {
    if (this.relogio !== null) clearInterval(this.relogio);
    this.relogio = null;
  }

  // --- estado ------------------------------------------------------------

  private mudarFila(fila: F.Fila) {
    this.fila = fila;
    this.mudar({});
  }

  private mudar(parcial: { situacao?: Situacao }) {
    if (parcial.situacao) this.situacao = parcial.situacao;
    this.instantaneo = this.montarEstado();
    for (const o of this.ouvintes) o();
  }

  private montarEstado(): EstadoMotor {
    return {
      tocando: this.fila.tocando,
      proximas: this.fila.proximas,
      situacao: this.situacao,
      repetir: this.fila.repetir,
      volume: this.volume,
    };
  }

  private avisarProgresso() {
    for (const o of this.ouvintesProgresso) o();
  }

  private emitir(evento: EventoMotor) {
    for (const o of this.ouvintesEvento) o(evento);
  }
}

export type { ItemDaFila };
