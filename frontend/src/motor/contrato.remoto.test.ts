/**
 * Os casos do contrato pela rede: MotorRemoto de verdade falando com o
 * backend de verdade. Pega diferença de protocolo (nome de campo, formato)
 * que os testes de cada lado sozinhos não pegam.
 *
 * Só roda com o Freddy ligado em modo de teste e FREDDY_E2E definido:
 *   (cd backend && python -m freddy --teste --porta 47899) &
 *   FREDDY_E2E=127.0.0.1:47899 npm test
 * O GitHub faz isso no app.yml. Casos que mexem no reprodutor ficam de fora.
 */

import { afterAll, beforeAll, describe, it } from "vitest";
import { CASOS, rodarCaso, soPorFora } from "./contratoCasos";
import { MotorRemoto } from "./motorRemoto";

const endereco = process.env.FREDDY_E2E;

describe.skipIf(!endereco)("contrato do Motor (MotorRemoto ↔ backend)", () => {
  let motor: MotorRemoto;

  beforeAll(async () => {
    motor = new MotorRemoto(`ws://${endereco}/ws`);
    for (let i = 0; i < 50 && motor.conexao() !== "conectado"; i++) await new Promise((r) => setTimeout(r, 100));
  });
  afterAll(() => motor?.fechar());

  for (const caso of CASOS.filter(soPorFora)) {
    it(caso.nome, async () => {
      // Cada caso começa do zero: fila vazia, volume padrão.
      await motor.executar({ tipo: "parar" });
      await motor.executar({ tipo: "volume", valor: 50 });
      await rodarCaso(caso, motor);
    });
  }
});
