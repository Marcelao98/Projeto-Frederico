/// <reference types="vitest" />
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// O acervo (musicas.json + vocabulario.json) mora em acervo/, na raiz: é a
// mesma fonte que o backend usa. O painel lê direto de lá: nada de cópia.
const acervo = fileURLToPath(new URL("../acervo", import.meta.url));
// Os casos do contrato do Motor (casos_contrato.json), rodados pelos testes
// do MotorLocal aqui e do Motor do backend lá.
const contrato = fileURLToPath(new URL("../backend/freddy/salas", import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@acervo": acervo, "@contrato": contrato } },
  server: { port: 5173, fs: { allow: [".", acervo] } },
  test: { environment: "node" },
});
