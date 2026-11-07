/**
 * Roda os casos de backend/freddy/salas/casos_contrato.json num Motor.
 * Usado por contrato.test.ts (MotorLocal) e contrato.remoto.test.ts
 * (MotorRemoto falando com o backend de verdade). O Python roda os mesmos
 * em backend/freddy/salas/test_contrato.py.
 */

import casos from "@contrato/casos_contrato.json";
import { expect } from "vitest";
import type { Musica } from "../comum/tipos";
import type { OuvinteReprodutor } from "../navegador/reprodutor";
import type { Comando, EventoMotor, Motor } from "./tipos";

export type Passo = Record<string, unknown>;
export interface Caso {
  nome: string;
  passos: Passo[];
}

export const CASOS: Caso[] = (casos as { casos: Caso[] }).casos;

/** O que o teste controla do reprodutor (só dá com o MotorLocal). */
export interface Bastidores {
  ouvinte(): OuvinteReprodutor;
  carregados(): string[];
  volume(): number;
}

const PASSOS_DE_BASTIDOR = ["reprodutor", "carregados", "volume_reprodutor"];

/** O caso só olha o que o motor mostra (dá pra rodar pela rede)? */
export function soPorFora(caso: Caso): boolean {
  return caso.passos.every((p) => !PASSOS_DE_BASTIDOR.some((k) => k in p));
}

const musica = (n: number): Musica => ({ titulo: `Música ${n}`, link: `https://youtu.be/v${n}` });

function expandirMusicas(spec: unknown): Musica[] {
  if (!Array.isArray(spec)) {
    const [de, ate] = (spec as { intervalo: [number, number] }).intervalo;
    return Array.from({ length: ate - de }, (_, i) => musica(de + i));
  }
  return spec.map((x) => (typeof x === "number" ? musica(x) : (x as Musica)));
}

function resumir(e: EventoMotor) {
  const r: Record<string, unknown> = { tipo: e.tipo };
  if ("musica" in e) r.titulo = e.musica.titulo;
  if ("motivo" in e) r.motivo = e.motivo;
  return r;
}

export async function rodarCaso(caso: Caso, motor: Motor, bastidores?: Bastidores) {
  const eventos: EventoMotor[] = [];
  const cancelar = motor.aoEvento((e) => eventos.push(e));
  try {
    for (const [i, passo] of caso.passos.entries()) {
      const onde = `passo ${i}: ${JSON.stringify(passo)}`;
      if ("executar" in passo) {
        const comando = { ...(passo.executar as Record<string, unknown>) };
        if ("musicas" in comando) comando.musicas = expandirMusicas(comando.musicas);
        if (typeof comando.uid === "string") {
          const uid = comando.uid;
          if (uid === "$tocando") comando.uid = motor.estado().tocando?.uid;
          else if (uid.startsWith("$proximas.")) comando.uid = motor.estado().proximas[Number(uid.split(".")[1])].uid;
        }
        const resultado = await motor.executar(comando as unknown as Comando);
        if ("resultado" in passo) expect(resultado, onde).toEqual(passo.resultado);
      } else if ("estado" in passo) {
        const e = motor.estado();
        for (const [chave, esperado] of Object.entries(passo.estado as Record<string, unknown>)) {
          const atual =
            chave === "tocando"
              ? (e.tocando?.titulo ?? null)
              : chave === "proximas"
                ? e.proximas.map((m) => m.titulo)
                : e[chave as keyof typeof e];
          expect(atual, `${onde} (${chave})`).toEqual(esperado);
        }
      } else if ("eventos" in passo) {
        expect(eventos.map(resumir), onde).toEqual(passo.eventos);
      } else if (bastidores && "reprodutor" in passo) {
        const o = bastidores.ouvinte();
        const acao = passo.reprodutor as keyof OuvinteReprodutor;
        if (acao === "erro" || acao === "titulo") o[acao](passo.arg as string);
        else o[acao]();
      } else if (bastidores && "carregados" in passo) {
        expect(bastidores.carregados(), onde).toEqual((passo.carregados as number[]).map((n) => musica(n).link));
      } else if (bastidores && "volume_reprodutor" in passo) {
        expect(bastidores.volume(), onde).toBe(passo.volume_reprodutor);
      } else {
        throw new Error(`passo desconhecido: ${onde}`);
      }
    }
  } finally {
    cancelar();
  }
}
