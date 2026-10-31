/**
 * Os casos de backend/freddy/motor/casos_contrato.json, rodados no MotorLocal.
 * O backend roda os mesmos no Motor dele (test_contrato.py): os dois motores
 * se comportam igual, e o painel não sabe qual está usando.
 */

import { describe, it } from "vitest";
import { CASOS, rodarCaso } from "./contratoCasos";
import { MotorLocal } from "./motorLocal";
import type { OuvinteReprodutor, Reprodutor } from "./reprodutor";

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

describe("contrato do Motor (MotorLocal)", () => {
  for (const caso of CASOS) {
    it(caso.nome, async () => {
      const r = new ReprodutorFalso();
      await rodarCaso(caso, new MotorLocal(r), {
        ouvinte: () => r.ouvinte,
        carregados: () => r.carregados,
        volume: () => r.volume,
      });
    });
  }
});
