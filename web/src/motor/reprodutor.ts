/**
 * Quem toca o som de fato. O MotorLocal decide o QUE tocar; o Reprodutor só
 * obedece. Hoje é o player do YouTube no navegador. Um reprodutor de arquivo
 * local (<audio>) ou um de teste implementam a mesma interface.
 */

export interface OuvinteReprodutor {
  tocando(): void;
  pausado(): void;
  fim(): void;
  erro(motivo: string): void;
  /** O título de verdade do vídeo, quando o player descobre. */
  titulo(titulo: string): void;
}

export interface Reprodutor {
  ouvir(ouvinte: OuvinteReprodutor): void;
  carregar(link: string): void;
  tocar(): void;
  pausar(): void;
  parar(): void;
  buscar(segundos: number): void;
  definirVolume(volume: number): void; // 0-100
  posicao(): number;
  duracao(): number;
}
