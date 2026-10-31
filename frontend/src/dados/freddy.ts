/**
 * O backend do Freddy (python -m freddy), visto do painel: descobrir se está
 * ligado e as rotas REST (acervo, playlists, YouTube). O motor em si fala
 * pelo WebSocket, no MotorRemoto.
 */

import type { Faixa, Musica, VocabularioBruto } from "../nucleo/tipos";
import { criarArmazem } from "./armazem";
import type { PlaylistSalva } from "./playlists";

export const ENDERECO_PADRAO = "127.0.0.1:47824";
const PRAZO_DA_SAUDE_MS = 800;

/** auto: usa o Freddy se ele estiver ligado; senão, o navegador. */
export type PreferenciaDeMotor = "auto" | "navegador" | "freddy";
export const preferenciaDeMotor = criarArmazem<PreferenciaDeMotor>("auto", "freddy.motor");
export const enderecoDoFreddy = criarArmazem<string>(ENDERECO_PADRAO, "freddy.endereco");

export interface Saude {
  ok: boolean;
  versao: string;
  protocolo: number;
  som: string;
}

export class ErroDoFreddy extends Error {
  constructor(
    mensagem: string,
    readonly status: number,
    readonly detalhe?: unknown,
  ) {
    super(mensagem);
  }
}

type Buscar = typeof fetch;

export class ApiFreddy {
  constructor(
    readonly endereco: string = ENDERECO_PADRAO,
    private readonly buscar: Buscar = (...a) => fetch(...a),
  ) {}

  get urlDoMotor() {
    return `ws://${this.endereco}/ws`;
  }

  private async pedir<T>(caminho: string, init?: RequestInit & { prazoMs?: number }): Promise<T> {
    const controle = new AbortController();
    const prazo = setTimeout(() => controle.abort(), init?.prazoMs ?? 20_000);
    try {
      const resposta = await this.buscar(`http://${this.endereco}${caminho}`, {
        ...init,
        headers: init?.body ? { "Content-Type": "application/json" } : undefined,
        signal: controle.signal,
      });
      if (resposta.status === 204) return undefined as T;
      const corpo = await resposta.json().catch(() => null);
      if (!resposta.ok) {
        const detalhe = (corpo as { detail?: unknown } | null)?.detail;
        const texto = typeof detalhe === "string" ? detalhe : ((detalhe as { erro?: string })?.erro ?? `erro ${resposta.status}`);
        throw new ErroDoFreddy(texto, resposta.status, detalhe);
      }
      return corpo as T;
    } finally {
      clearTimeout(prazo);
    }
  }

  /** null se o Freddy não respondeu (desligado). */
  async saude(prazoMs = PRAZO_DA_SAUDE_MS): Promise<Saude | null> {
    try {
      const s = await this.pedir<Saude>("/saude", { prazoMs });
      return s?.ok ? s : null;
    } catch {
      return null;
    }
  }

  acervo() {
    return this.pedir<{ musicas: Faixa[]; vocabulario: VocabularioBruto }>("/acervo");
  }

  /** "Era essa?": ensina a faixa. ErroDoFreddy 409 se já está no acervo. */
  aprender(faixa: { titulo: string; link: string; temas: string[] }) {
    return this.pedir<Faixa>("/acervo/faixas", { method: "POST", body: JSON.stringify(faixa) });
  }

  playlists() {
    return this.pedir<PlaylistSalva[]>("/playlists");
  }

  salvarPlaylist(p: PlaylistSalva) {
    return this.pedir<PlaylistSalva>(`/playlists/${encodeURIComponent(p.id)}`, { method: "PUT", body: JSON.stringify(p) });
  }

  excluirPlaylist(id: string) {
    return this.pedir<void>(`/playlists/${encodeURIComponent(id)}`, { method: "DELETE" });
  }

  async tituloDoLink(link: string): Promise<string | null> {
    try {
      return (await this.pedir<Musica>(`/youtube/info?link=${encodeURIComponent(link)}`, { prazoMs: 15_000 })).titulo;
    } catch {
      return null;
    }
  }

  /** Busca livre: o melhor resultado, ou null se o YouTube não achou nada. */
  async buscarNoYoutube(texto: string): Promise<Musica | null> {
    try {
      return await this.pedir<Musica>("/youtube/buscar", { method: "POST", body: JSON.stringify({ texto }), prazoMs: 30_000 });
    } catch (e) {
      if (e instanceof ErroDoFreddy && e.status === 404) return null;
      throw e;
    }
  }
}

/** O Freddy em uso, se o painel está falando com ele (null = só o navegador). */
export const freddy = criarArmazem<ApiFreddy | null>(null);

/** ?motor=navegador|freddy|auto na URL ganha da preferência (bom pra testar). */
export function preferenciaEfetiva(busca = typeof location !== "undefined" ? location.search : ""): PreferenciaDeMotor {
  const daUrl = new URLSearchParams(busca).get("motor");
  if (daUrl === "navegador" || daUrl === "local") return "navegador";
  if (daUrl === "freddy" || daUrl === "auto") return daUrl;
  return preferenciaDeMotor.ler();
}

/**
 * Qual motor usar: o Freddy (devolve a API) ou o navegador (null).
 * "auto" pergunta ao Freddy se ele está ligado; "freddy" usa mesmo
 * desligado (o MotorRemoto fica tentando religar).
 */
export async function escolherFreddy(
  preferencia: PreferenciaDeMotor = preferenciaEfetiva(),
  api: ApiFreddy = new ApiFreddy(enderecoDoFreddy.ler()),
): Promise<ApiFreddy | null> {
  if (preferencia === "navegador") return null;
  if (preferencia === "freddy") return api;
  return (await api.saude()) ? api : null;
}
