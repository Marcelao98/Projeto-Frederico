/** Preferências da tela, guardadas no navegador. */
import { criarArmazem } from "./armazem";

const telaPequena = typeof window !== "undefined" && window.matchMedia?.("(max-width: 760px)").matches;

export const modoAtual = criarArmazem<string>("chat", "freddy.modo");
/** No celular o vídeo flutua por cima do conteúdo: começa fechado. */
export const videoAberto = criarArmazem<boolean>(!telaPequena, "freddy.video");
