/**
 * Reprodutor com o player oficial do YouTube (IFrame API) embutido na página.
 * Toca no navegador: serve pra usar o painel sozinho, antes do backend.
 */

import { videoId } from "../nucleo/youtube";
import type { OuvinteReprodutor, Reprodutor } from "./reprodutor";

declare global {
  interface Window {
    onYouTubeIframeAPIReady?: () => void;
  }
}

let apiCarregando: Promise<void> | null = null;

function carregarApi(): Promise<void> {
  if (window.YT?.Player) return Promise.resolve();
  if (apiCarregando) return apiCarregando;
  apiCarregando = new Promise((resolver, rejeitar) => {
    const anterior = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      anterior?.();
      resolver();
    };
    const script = document.createElement("script");
    script.src = "https://www.youtube.com/iframe_api";
    script.onerror = () => rejeitar(new Error("não consegui carregar o player do YouTube"));
    document.head.appendChild(script);
  });
  return apiCarregando;
}

// https://developers.google.com/youtube/iframe_api_reference#onError
const MOTIVOS: Record<number, string> = {
  2: "link inválido",
  5: "o navegador não conseguiu tocar esse vídeo",
  100: "vídeo removido ou privado",
  101: "o dono do vídeo não deixa tocar fora do YouTube",
  150: "o dono do vídeo não deixa tocar fora do YouTube",
};

export class ReprodutorYoutube implements Reprodutor {
  private player: YT.Player | null = null;
  private pronto = false;
  private ouvinte: OuvinteReprodutor | null = null;
  private pendente: (() => void) | null = null;
  private volume = 50;
  private carregou = false; // carregar() já rodou; senão o "parado" inicial não é fim

  constructor(elemento: HTMLElement) {
    carregarApi()
      .then(() => this.criar(elemento))
      .catch((e: Error) => this.ouvinte?.erro(e.message));
  }

  ouvir(ouvinte: OuvinteReprodutor) {
    this.ouvinte = ouvinte;
  }

  private criar(elemento: HTMLElement) {
    const alvo = document.createElement("div");
    elemento.replaceChildren(alvo);
    this.player = new YT.Player(alvo, {
      width: "100%",
      height: "100%",
      playerVars: { autoplay: 1, controls: 0, disablekb: 1, rel: 0, playsinline: 1 },
      events: {
        onReady: () => {
          this.pronto = true;
          this.player?.setVolume(this.volume);
          this.pendente?.();
          this.pendente = null;
        },
        onStateChange: (e) => this.aoMudar(e.data),
        onError: (e) => this.ouvinte?.erro(MOTIVOS[e.data as number] ?? `erro ${e.data} do YouTube`),
      },
    });
  }

  private aoMudar(estado: YT.PlayerState) {
    switch (estado) {
      case YT.PlayerState.PLAYING: {
        const titulo = (this.player as YT.Player & { getVideoData?: () => { title?: string } })?.getVideoData?.()
          ?.title;
        if (titulo) this.ouvinte?.titulo(titulo);
        this.ouvinte?.tocando();
        break;
      }
      case YT.PlayerState.PAUSED:
        this.ouvinte?.pausado();
        break;
      case YT.PlayerState.ENDED:
        if (this.carregou) this.ouvinte?.fim();
        break;
    }
  }

  private quandoPronto(acao: () => void) {
    if (this.pronto && this.player) acao();
    else this.pendente = acao;
  }

  carregar(link: string) {
    this.carregou = true;
    this.quandoPronto(() => this.player?.loadVideoById(videoId(link)));
  }
  tocar() {
    this.quandoPronto(() => this.player?.playVideo());
  }
  pausar() {
    this.quandoPronto(() => this.player?.pauseVideo());
  }
  parar() {
    this.carregou = false;
    this.quandoPronto(() => this.player?.stopVideo());
  }
  buscar(segundos: number) {
    this.quandoPronto(() => this.player?.seekTo(segundos, true));
  }
  definirVolume(volume: number) {
    this.volume = volume;
    if (this.pronto) this.player?.setVolume(volume);
  }
  posicao() {
    return this.pronto ? (this.player?.getCurrentTime() ?? 0) : 0;
  }
  duracao() {
    return this.pronto ? (this.player?.getDuration() ?? 0) : 0;
  }
}
