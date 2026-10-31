/// <reference types="vitest" />
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// O acervo (musicas.json + vocabulario.json) mora no Bardo, em
// modules/bardo/dataset, e é a mesma fonte que o backend Python vai usar.
// O painel lê direto de lá: nada de cópia pra ficar dessincronizada.
const dataset = fileURLToPath(new URL("../backend/modules/bardo/dataset", import.meta.url));
// Os casos do contrato do Motor (casos_contrato.json), rodados pelos testes
// do MotorLocal aqui e do Motor do backend lá.
const contrato = fileURLToPath(new URL("../backend/freddy/motor", import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@dataset": dataset, "@contrato": contrato } },
  server: { port: 5173, fs: { allow: [".", dataset] } },
  test: { environment: "node" },
});
