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

/** O que mudar numa faixa do acervo (o resto fica como está). */
export interface EdicaoDeFaixa {
  nome?: string;
  temas?: string[];
  comentario?: string;
}

/** O que a planilha enviada muda no acervo (antes e depois de aplicar). */
export interface ResumoDaPlanilha {
  mudaram: number;
  novas: number;
  ignoradas: { linha: number; motivo: string }[];
  totalIgnoradas: number;
  exemplos: { id: string; nome: string; antes: string[]; depois: string[] }[];
  aplicado: boolean;
}

/** O bot do Discord, como o Freddy conta (GET /discord e as mensagens "discord" do /ws). */
export interface EstadoDiscord {
  configurado: boolean;
  doAmbiente: boolean;
  situacao: "desligado" | "conectando" | "conectado" | "erro";
  erro: string | null;
  bot: { id: string; nome: string; avatar: string } | null;
  convite: string | null;
  servidores: { id: string; nome: string; icone: string | null; canais: { id: string; nome: string; pessoas: number }[] }[];
  canal: { id: string; nome: string; servidorId: string; servidor: string } | null;
  ouvirAqui: boolean;
  /** false no --sem-som: conecta, mas não tem som pra mandar. */
  podeTocar: boolean;
  /** O que está indo pra call agora (null fora da call). */
  transmissao?: Transmissao | null;
}

/** O medidor do som indo pra call (backend/freddy/bot/saida.py). */
export interface Transmissao {
  conectado: boolean;
  tocando: boolean;
  quadros: number;
  quadrosComSom: number;
  /** O Discord pede 50 por segundo. */
  quadrosPorSegundo: number;
  comSomPorSegundo: number;
  /** 0 a 32767. */
  nivel: number;
  segundosDesdeUltimo: number | null;
}

/** O modo debug: GET /diagnostico. */
export interface Diagnostico {
  bot: EstadoDiscord["situacao"];
  canal: string | null;
  transmissao: Transmissao | null;
  mesa: {
    musica: "sem música" | "carregando" | "tocando" | "engasgou" | "pausada" | "assobiando";
    bufferSegundos: number;
    nivelLocal: number;
    mudoLocal: boolean;
  } | null;
  motor: { situacao: string; titulo: string | null };
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
        headers: init?.headers ?? (init?.body ? { "Content-Type": "application/json" } : undefined),
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

  /** Corrige nome/temas/comentário de uma faixa; devolve como ficou (categorias recalculadas). */
  editarFaixa(id: string, edicao: EdicaoDeFaixa) {
    return this.pedir<Faixa>(`/acervo/faixas/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(edicao) });
  }

  /** Salva o acervo em CSV na pasta Downloads; devolve onde. */
  salvarPlanilha() {
    return this.pedir<{ caminho: string }>("/acervo/planilha/salvar", { method: "POST" });
  }

  /** Manda a planilha editada: sem `aplicar`, só o resumo do que mudaria. */
  enviarPlanilha(texto: string, aplicar: boolean) {
    return this.pedir<ResumoDaPlanilha>(`/acervo/planilha?aplicar=${aplicar}`, {
      method: "POST",
      body: texto,
      headers: { "Content-Type": "text/csv; charset=utf-8" },
      prazoMs: 60_000,
    });
  }

  // --- Discord --------------------------------------------------------------

  discord() {
    return this.pedir<EstadoDiscord>("/discord");
  }

  /** Guarda o token (na pasta do Freddy, nunca no git) e conecta o bot. */
  guardarTokenDoDiscord(token: string) {
    return this.pedir<EstadoDiscord>("/discord/token", { method: "PUT", body: JSON.stringify({ token }), prazoMs: 45_000 });
  }

  /** Conecta de novo com o token já guardado (depois de cair, por exemplo). */
  religarDiscord() {
    return this.pedir<EstadoDiscord>("/discord/religar", { method: "POST", prazoMs: 45_000 });
  }

  esquecerTokenDoDiscord() {
    return this.pedir<EstadoDiscord>("/discord/token", { method: "DELETE" });
  }

  entrarNaCall(canalId: string) {
    return this.pedir<EstadoDiscord>("/discord/entrar", { method: "POST", body: JSON.stringify({ canalId }), prazoMs: 30_000 });
  }

  sairDaCall() {
    return this.pedir<EstadoDiscord>("/discord/sair", { method: "POST" });
  }

  ouvirAqui(ligado: boolean) {
    return this.pedir<EstadoDiscord>("/discord/ouvir-aqui", { method: "PUT", body: JSON.stringify({ ligado }) });
  }

  /** O teste da call: o Frederico assobia só pelo Discord (o PC fica mudo). Volta quando acaba. */
  assobiar() {
    return this.pedir<EstadoDiscord>("/discord/assobio", { method: "POST", prazoMs: 15_000 });
  }

  diagnostico() {
    return this.pedir<Diagnostico>("/diagnostico", { prazoMs: 3_000 });
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

/** O bot do Discord (null = ainda não sabe, ou sem Freddy). */
export const discord = criarArmazem<EstadoDiscord | null>(null);

/** ?motor=navegador|freddy|auto na URL ganha da preferência (bom pra testar). */
export function preferenciaEfetiva(busca = typeof location !== "undefined" ? location.search : ""): PreferenciaDeMotor {
  const daUrl = new URLSearchParams(busca).get("motor");
  if (daUrl === "navegador" || daUrl === "local") return "navegador";
  if (daUrl === "freddy" || daUrl === "auto") return daUrl;
  return preferenciaDeMotor.ler();
}

/** Quantas vezes perguntar se o Freddy está ligado ao abrir (ele pode estar acabando de ligar). */
const TENTATIVAS_AO_ABRIR = 4;
const ESPERA_ENTRE_TENTATIVAS_MS = 600;
const espera = (ms: number) => new Promise((r) => setTimeout(r, ms));

/**
 * Qual motor usar: o Freddy (devolve a API) ou o navegador (null).
 * "auto" pergunta ao Freddy se ele está ligado, algumas vezes, porque o app
 * pode abrir junto com ele (uns 3 s no total, só quando ele não responde);
 * "freddy" usa mesmo desligado (o MotorRemoto fica tentando religar).
 */
export async function escolherFreddy(
  preferencia: PreferenciaDeMotor = preferenciaEfetiva(),
  api: ApiFreddy = new ApiFreddy(enderecoDoFreddy.ler()),
  tentativas = TENTATIVAS_AO_ABRIR,
  esperaMs = ESPERA_ENTRE_TENTATIVAS_MS,
): Promise<ApiFreddy | null> {
  if (preferencia === "navegador") return null;
  if (preferencia === "freddy") return api;
  for (let i = 0; i < tentativas; i++) {
    if (await api.saude()) return api;
    if (i < tentativas - 1) await espera(esperaMs);
  }
  return null;
}

/**
 * Tocando pelo navegador, fica de olho: se o Freddy ligar depois, chama
 * `aoLigar` (uma vez). Devolve a função de parar de olhar.
 */
export function vigiarFreddy(
  aoLigar: () => void,
  api: ApiFreddy = new ApiFreddy(enderecoDoFreddy.ler()),
  intervaloMs = 5000,
): () => void {
  let parado = false;
  const relogio = setInterval(async () => {
    if (parado) return;
    if (await api.saude()) {
      parado = true;
      clearInterval(relogio);
      aoLigar();
    }
  }, intervaloMs);
  return () => {
    parado = true;
    clearInterval(relogio);
  };
}

/** O Freddy ligou depois que o painel abriu pelo navegador (a tela oferece trocar). */
export const freddyLigouDepois = criarArmazem<boolean>(false);
