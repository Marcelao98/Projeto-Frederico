/**
 * O narrador: o chat conta o que mudou na fila fora dele (pela Playlist, pela
 * barra do player, por outra aba no Freddy). "▶ Tocando Greenpath", "+5 na
 * fila", "⏹ Parou".
 *
 * Não repete o que já foi dito: o que o próprio chat pediu (ele já respondeu,
 * por isso o chat "silencia" o narrador enquanto trabalha) e a fila andando
 * sozinha (essa o evento tocando_agora já conta). Reordenar e tirar música
 * não viram fala: seria barulho.
 */

import type { EstadoMotor, Motor } from "../../motor/tipos";

const ESPERA_MS = 300; // junta mudanças em sequência (e espera o evento chegar, no Freddy)

export interface Narrador {
  /** Roda `tarefa` sem narrar o que ela mudar. */
  silenciar<T>(tarefa: () => Promise<T>): Promise<T>;
  desligar(): void;
}

let ativo: Narrador | null = null;

/** Pro chat: faz o pedido sem o narrador repetir (sem narrador ligado, só faz). */
export function semNarrar<T>(tarefa: () => Promise<T>): Promise<T> {
  return ativo ? ativo.silenciar(tarefa) : tarefa();
}

const negrito = (t: string) => `**${t.replace(/\*/g, "")}**`;

export function ligarNarrador(motor: Motor, falar: (texto: string) => void, esperaMs = ESPERA_MS): Narrador {
  let anterior: EstadoMotor = motor.estado();
  const jaContados = new Set<string>(); // uids que o evento tocando_agora já anunciou
  let acabouSozinha = false;
  let silencio = 0;
  let relogio: ReturnType<typeof setTimeout> | null = null;

  const cancelar = () => {
    if (relogio !== null) clearTimeout(relogio);
    relogio = null;
  };

  const recomecar = () => {
    cancelar();
    anterior = motor.estado();
    jaContados.clear();
    acabouSozinha = false;
  };

  function narrar() {
    relogio = null;
    const atual = motor.estado();
    const falas: string[] = [];
    const trocou = atual.tocando?.uid !== anterior.tocando?.uid;
    if (trocou && atual.tocando && !jaContados.has(atual.tocando.uid)) falas.push(`▶ Tocando ${negrito(atual.tocando.titulo)}`);
    if (trocou && !atual.tocando && !acabouSozinha) falas.push("⏹ Parou");

    const antes = new Set(anterior.proximas.map((m) => m.uid));
    if (anterior.tocando) antes.add(anterior.tocando.uid);
    const novas = atual.proximas.filter((m) => !antes.has(m.uid)).length;
    if (novas) falas.push(`+${novas} na fila`);
    else if (!trocou && anterior.proximas.length > 0 && atual.proximas.length === 0) falas.push("🧹 Fila vazia");

    recomecar();
    if (falas.length) falar(falas.join(" · "));
  }

  const pararDeOuvirEstado = motor.inscrever(() => {
    if (silencio || relogio !== null) return;
    relogio = setTimeout(narrar, esperaMs);
  });
  const pararDeOuvirEventos = motor.aoEvento((e) => {
    if (e.tipo === "tocando_agora") jaContados.add(e.musica.uid);
    if (e.tipo === "fila_acabou") acabouSozinha = true;
  });

  const narrador: Narrador = {
    async silenciar(tarefa) {
      silencio += 1;
      cancelar();
      try {
        return await tarefa();
      } finally {
        silencio -= 1;
        if (!silencio) recomecar(); // o que o chat mudou vira o novo "antes"
      }
    },
    desligar() {
      cancelar();
      pararDeOuvirEstado();
      pararDeOuvirEventos();
      if (ativo === narrador) ativo = null;
    },
  };
  ativo = narrador;
  return narrador;
}
