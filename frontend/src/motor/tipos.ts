/**
 * O contrato do motor de som: o que o painel pode pedir e o que ele enxerga.
 *
 * Dois motores implementam: o MotorLocal (toca no navegador, via YouTube) e
 * o MotorRemoto (fala com o backend Python, `python -m freddy`, por
 * WebSocket). As telas não sabem qual é. O backend tem a porta fiel deste
 * contrato em backend/freddy/salas/; os casos de casos_contrato.json rodam
 * nos dois lados. Mixer, soundboard e afins entram acrescentando comandos
 * em `Comandos` e campos em `EstadoMotor`.
 */

import type { Musica } from "../comum/tipos";

export const MAX_FILA = 50; // músicas esperando, sem contar a que toca (igual ao Bardo)

/** Uma música na fila. O `uid` diferencia a mesma música posta duas vezes. */
export interface ItemDaFila extends Musica {
  uid: string;
}

export type Situacao = "parado" | "carregando" | "tocando" | "pausado";

export interface EstadoMotor {
  tocando: ItemDaFila | null;
  proximas: ItemDaFila[];
  situacao: Situacao;
  repetir: boolean; // repete a faixa ATUAL, não a fila
  volume: number; // 0-100
}

export interface Progresso {
  posicao: number; // segundos
  duracao: number; // segundos; 0 = ainda não sabe
}

/** Onde as músicas novas entram na fila. */
export type Onde = "fim" | "proxima" | "agora";

/**
 * Cada comando: os argumentos e o que ele devolve. Pra criar um comando
 * novo (ex.: "mixer.volume_camada"), acrescente aqui e implemente nos DOIS
 * motores (motorLocal.ts e backend/freddy/salas/motor.py, mais a validação
 * em backend/freddy/api/protocolo.py) e um caso em casos_contrato.json.
 */
export interface Comandos {
  adicionar: {
    args: { musicas: Musica[]; onde?: Onde };
    // entraram: quantas couberam; posicao: da primeira (0 = começou a tocar).
    resultado: { entraram: number; posicao: number; comecou: boolean };
  };
  pular: { args: object; resultado: { pulou: boolean; temProxima: boolean; repetiaAntes: boolean } };
  pausar: { args: object; resultado: { ok: boolean } };
  continuar: { args: object; resultado: { ok: boolean } };
  alternar_pausa: { args: object; resultado: { ok: boolean } };
  parar: { args: object; resultado: { ok: boolean } };
  limpar_fila: { args: object; resultado: { removidas: number } };
  repetir: { args: { ligar?: boolean }; resultado: { repetir: boolean } };
  volume: { args: { valor?: number; delta?: number }; resultado: { volume: number } };
  remover: { args: { uid: string }; resultado: { ok: boolean } };
  mover: { args: { uid: string; para: number }; resultado: { ok: boolean } };
  tocar_item: { args: { uid: string }; resultado: { ok: boolean } };
  embaralhar: { args: object; resultado: { ok: boolean } };
  buscar_posicao: { args: { segundos: number }; resultado: { ok: boolean } };
}

export type NomeComando = keyof Comandos;
export type Comando<K extends NomeComando = NomeComando> = { [N in K]: { tipo: N } & Comandos[N]["args"] }[K];
export type Resultado<K extends NomeComando> = Comandos[K]["resultado"];

/** Coisas que acontecem sem ninguém pedir na hora: o chat conta pra mesa. */
export type EventoMotor =
  | { tipo: "tocando_agora"; musica: ItemDaFila }
  | { tipo: "fila_acabou" }
  | { tipo: "falha"; musica: ItemDaFila; motivo: string };

/** Só pra motor que mora longe (o MotorRemoto): como está a conexão. */
export type SituacaoConexao = "conectando" | "conectado" | "reconectando";

export interface Motor {
  estado(): EstadoMotor;
  progresso(): Progresso;
  /** Avisa quando o estado muda; devolve a função de cancelar. */
  inscrever(ouvinte: () => void): () => void;
  inscreverProgresso(ouvinte: () => void): () => void;
  aoEvento(ouvinte: (evento: EventoMotor) => void): () => void;
  executar<K extends NomeComando>(comando: Comando<K>): Promise<Resultado<K>>;
  /** Ausente = motor local, sempre "conectado". */
  conexao?(): SituacaoConexao;
  inscreverConexao?(ouvinte: () => void): () => void;
}
