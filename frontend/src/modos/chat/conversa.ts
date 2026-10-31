/**
 * O "cérebro" do chat: texto da mesa → comando no motor → resposta do Freddy.
 *
 * Mesma ideia do cog do Bardo: interpretarPedido() decide o que é, o motor
 * faz, e aqui só se monta a resposta (com os mesmos textos da Natty). Sem
 * LLM. Não depende de React, então dá pra testar sozinho.
 */

import type { Acervo } from "../../dados/acervo";
import type { Motor } from "../../motor/tipos";
import { MAX_FILA } from "../../motor/tipos";
import { interpretarPedido, type Pedido } from "../../nucleo/pedido";
import { normalizar } from "../../nucleo/texto";
import { musicaDaFaixa, type Musica } from "../../nucleo/tipos";
import type { EventoMotor } from "../../motor/tipos";
import type { Faixa } from "../../nucleo/tipos";
import { ehComandoDeRevisao, separarTemas, tentarRevisao, type Revisao } from "./revisao";

export { separarTemas };

export interface RespostaFreddy {
  texto: string;
  /** Músicas citadas na resposta, pra tela mostrar como cartões. */
  musicas?: Musica[];
  /** "Era essa?": música achada na busca livre, que a mesa pode ensinar pro acervo. */
  pergunta?: Musica;
  /** "Tá certo?": os temas de uma faixa do acervo, pra confirmar ou corrigir. */
  revisao?: Revisao;
}

export interface Contexto {
  motor: Motor;
  acervo: Acervo;
  /** Descobre o título de um link colado; null se não der. */
  tituloDoLink?: (link: string) => Promise<string | null>;
  /** Busca livre no YouTube (só com o Freddy ligado); null se não achou. */
  buscarNoYoutube?: (texto: string) => Promise<Musica | null>;
  /** Grava temas novos numa faixa (só com o Freddy ligado). */
  editarTemas?: (faixaId: string, temas: string[]) => Promise<Faixa>;
}

/** O que precisa pra ensinar uma faixa (a ApiFreddy cumpre). */
export interface Professor {
  aprender(faixa: { titulo: string; link: string; temas: string[] }): Promise<{ nome: string }>;
}

const MUSICAS_MOSTRADAS_NA_FILA = 10;
const AJUDA_RE = /^(ajuda|socorro|help|comandos|\?|o que (voce|vc) (faz|sabe))/;
const NOMES_DO_FREDDY_RE = /^\s*(@?(freddy|fred|frederico|fredbot))[\s,!:.]*/i;

export const AJUDA = [
  "Eu entendo o mesmo que o Bardo da Natty, sem precisar de @:",
  "• **toca triste e bloodborne**: busca no acervo (`e`, `ou`, `sem`)",
  "• **toca <link do YouTube>**: toca ou põe na fila",
  "• **pula** · **pausa** · **continua** · **para**",
  "• **repete** (liga/desliga) · **para de repetir**",
  "• **fila** · **limpa a fila**",
  "• **volume 30** · **aumenta** · **abaixa** · **qual o volume?**",
  "",
  "Pra arrumar o acervo (com o Freddy ligado):",
  "• **temas**: mostra os temas da que toca, e você diz se tá certo",
  "• **temas: taverna, alegre**: troca os temas",
  "• **revisar** (ou **revisar hollow knight**): passa faixa por faixa",
].join("\n");

export type Previa =
  | { tipo: "busca"; busca: string; total: number }
  | { tipo: "link" }
  | { tipo: "comando"; acao: Pedido["acao"] }
  | { tipo: "acervo"; descricao: string }
  | { tipo: "ajuda" };

/** O que o Freddy vai entender, antes de mandar: a prévia embaixo do campo. */
export function previa(texto: string, acervo: Acervo): Previa | null {
  const semNome = texto.replace(NOMES_DO_FREDDY_RE, "");
  if (AJUDA_RE.test(normalizar(semNome))) return { tipo: "ajuda" };
  const doAcervo = ehComandoDeRevisao(semNome);
  if (doAcervo) return { tipo: "acervo", descricao: doAcervo };
  const pedido = interpretarPedido(semNome);
  if (!pedido) return null;
  if (pedido.acao === "tocar") {
    if (pedido.link) return { tipo: "link" };
    if (pedido.busca) return { tipo: "busca", busca: pedido.busca, total: acervo.buscar(pedido.busca).length };
  }
  return { tipo: "comando", acao: pedido.acao };
}

const VERBO_E_BUSCA_RE = /(?:^|\s)(?:toca|toque|tocar|bota|coloca|põe|poe|play|adiciona|adicione|add)\s+(.*)$/iu;
const SEPARADOR_DA_BUSCA_RE = /(?:^|\s)(?:e|ou|sem|n[ãa]o)\s+/giu;

/**
 * O termo que está sendo digitado na busca, pra autocompletar:
 * "toca triste e bloo" → { termo: "bloo", inicio: <onde "bloo" começa> }.
 */
export function termoEmDigitacao(texto: string): { termo: string; inicio: number } | null {
  const m = VERBO_E_BUSCA_RE.exec(texto);
  if (!m) return null;
  const busca = m[1];
  let inicio = texto.length - busca.length;
  for (const sep of busca.matchAll(SEPARADOR_DA_BUSCA_RE)) {
    inicio = texto.length - busca.length + sep.index + sep[0].length;
  }
  const termo = texto.slice(inicio);
  return termo.trim() ? { termo, inicio } : null;
}

const mostrar = (titulo: string) => `**${titulo.replace(/\*/g, "")}**`;

export async function responder(texto: string, ctx: Contexto): Promise<RespostaFreddy> {
  const semNome = texto.replace(NOMES_DO_FREDDY_RE, "");
  if (AJUDA_RE.test(normalizar(semNome))) return { texto: AJUDA };

  const daRevisao = await tentarRevisao(semNome, ctx, (t) => interpretarPedido(t) !== null);
  if (daRevisao) return daRevisao;

  const pedido = interpretarPedido(semNome);
  if (pedido === null) {
    return {
      texto:
        "Não entendi 🦜 Tenta **toca calmo e hollow knight**, **pula** ou **volume 30**. " +
        "Manda **ajuda** que eu mostro tudo.",
    };
  }
  return executarPedido(pedido, ctx);
}

async function executarPedido(pedido: Pedido, ctx: Contexto): Promise<RespostaFreddy> {
  const { motor, acervo, tituloDoLink } = ctx;
  switch (pedido.acao) {
    case "tocar": {
      if (pedido.link) {
        const titulo = (await tituloDoLink?.(pedido.link).catch(() => null)) ?? "Link do YouTube";
        const musica: Musica = { titulo, link: pedido.link };
        const r = await motor.executar({ tipo: "adicionar", musicas: [musica] });
        if (!r.entraram) return { texto: filaCheia() };
        return {
          texto: r.comecou
            ? `Tocando ${mostrar(titulo)} 🎵`
            : `Adicionei ${mostrar(titulo)} na fila (posição ${r.posicao}) 📜`,
          musicas: [musica],
        };
      }
      if (!pedido.busca) {
        return { texto: 'Me manda o link do YouTube, ou descreve o que quer ouvir (ex: "toca triste e bloodborne").' };
      }
      const { escolhidas, total } = acervo.sortearDaBusca(pedido.busca);
      if (!escolhidas.length) {
        if (ctx.buscarNoYoutube) return buscaLivre(pedido.busca, motor, ctx.buscarNoYoutube);
        return {
          texto:
            `Não achei nada pra "${pedido.busca}" no acervo 😕 ` +
            "Tenta outros termos, ou cola o link do YouTube. (Com o Freddy ligado eu procuro no YouTube também.)",
        };
      }
      const musicas = escolhidas.map(musicaDaFaixa);
      const aviso = total > escolhidas.length ? ` (achei ${total}, sorteei ${escolhidas.length})` : "";
      const r = await motor.executar({ tipo: "adicionar", musicas });
      if (!r.entraram) return { texto: filaCheia() };
      const entraram = musicas.slice(0, r.entraram);
      if (r.comecou) {
        const resto = r.entraram - 1;
        const complemento = resto ? `, mais ${resto} na fila` : "";
        return { texto: `Tocando ${mostrar(entraram[0].titulo)} 🎵${complemento}${aviso}`, musicas: entraram };
      }
      const plural = r.entraram > 1 ? "s" : "";
      return { texto: `Adicionei ${r.entraram} música${plural} na fila${aviso} 📜`, musicas: entraram };
    }
    case "pular": {
      const r = await motor.executar({ tipo: "pular" });
      if (!r.pulou) return { texto: "Não tem nada tocando." };
      const aviso = r.repetiaAntes ? " (repetição desligada)" : "";
      return { texto: r.temProxima ? `Pulei ⏭️${aviso}` : `Pulei ⏭️ A fila acabou.${aviso}` };
    }
    case "fila":
      return descreverFila(motor);
    case "limpar_fila": {
      const { removidas } = await motor.executar({ tipo: "limpar_fila" });
      if (!removidas) return { texto: "A fila já está vazia." };
      return { texto: `Limpei a fila (${removidas} música${removidas > 1 ? "s" : ""}) 🧹` };
    }
    case "pausar":
      return { texto: (await motor.executar({ tipo: "pausar" })).ok ? "Pausei ⏸️" : "Não tem nada tocando." };
    case "continuar":
      return { texto: (await motor.executar({ tipo: "continuar" })).ok ? "Continuando ▶️" : "Não tem nada pausado." };
    case "parar":
      return { texto: (await motor.executar({ tipo: "parar" })).ok ? "Parei ⏹️" : "Não estou tocando nada." };
    case "repetir": {
      const tocando = motor.estado().tocando;
      if (!tocando && pedido.ligar === undefined && !motor.estado().repetir) {
        return { texto: "Não tem nada tocando pra repetir." };
      }
      const { repetir } = await motor.executar({ tipo: "repetir", ligar: pedido.ligar });
      if (repetir && tocando) {
        return {
          texto:
            `🔁 Repetindo ${mostrar(tocando.titulo)}: quando acabar, volta do começo. ` +
            "Pra parar: **para de repetir** (ou **repete** de novo).",
        };
      }
      return { texto: "➡️ Repetição desligada. Quando essa acabar, sigo a fila." };
    }
    case "volume": {
      if (pedido.volume === undefined && pedido.delta === undefined) {
        return { texto: `O volume está em ${motor.estado().volume}%.` };
      }
      const { volume } = await motor.executar({ tipo: "volume", valor: pedido.volume, delta: pedido.delta });
      return { texto: `Volume em ${volume}% 🔊` };
    }
  }
}

/** Nada no acervo: procura no YouTube, toca, e pergunta se era essa (como o Bardo). */
async function buscaLivre(
  busca: string,
  motor: Motor,
  buscarNoYoutube: (texto: string) => Promise<Musica | null>,
): Promise<RespostaFreddy> {
  let musica: Musica | null;
  try {
    musica = await buscarNoYoutube(busca);
  } catch (e) {
    const motivo = e instanceof Error ? e.message : String(e);
    return { texto: `Não achei "${busca}" no acervo, e o YouTube deu problema (${motivo}) 😕` };
  }
  if (!musica) return { texto: `Não achei nada pra "${busca}", nem no acervo nem no YouTube 😕` };
  const r = await motor.executar({ tipo: "adicionar", musicas: [musica] });
  if (!r.entraram) return { texto: filaCheia() };
  const onde = r.comecou ? "tocando" : `na fila (posição ${r.posicao})`;
  return {
    texto:
      `Não tinha "${busca}" no acervo, então procurei no YouTube: ${mostrar(musica.titulo)}, ${onde} 🔎\n` +
      "**Era essa?** Se for, me diz os climas dela que eu guardo no acervo.",
    musicas: [musica],
    pergunta: musica,
  };
}

/**
 * A resposta ao "era essa?": `temas` null = não era (pula, se ainda toca);
 * senão guarda no acervo com esses climas (vazio = "não classificado").
 */
export async function responderEraEssa(
  musica: Musica,
  temas: string[] | null,
  { motor, professor }: { motor: Motor; professor: Professor },
): Promise<RespostaFreddy> {
  if (temas === null) {
    if (motor.estado().tocando?.link === musica.link) {
      await motor.executar({ tipo: "pular" });
      return { texto: "Beleza, pulei essa. Tenta descrever de outro jeito, ou cola o link do YouTube." };
    }
    return { texto: "Beleza, não guardei." };
  }
  try {
    await professor.aprender({ titulo: musica.titulo, link: musica.link, temas });
  } catch (e) {
    const status = (e as { status?: number }).status;
    if (status === 409) return { texto: `Essa já estava no acervo 😉` };
    return { texto: `Não consegui guardar (${e instanceof Error ? e.message : String(e)}) 😕` };
  }
  const como = temas.length ? `como ${temas.map((t) => `**${t}**`).join(", ")}` : "sem clima (fica como **não classificado**)";
  return { texto: `Guardei ${mostrar(musica.titulo)} no acervo ${como} 🪶 Da próxima vez eu acho sozinho.` };
}

function filaCheia() {
  return `A fila já tem ${MAX_FILA} músicas. Espera andar um pouco ou pede **limpa a fila**.`;
}

function duracao(segundos?: number) {
  if (!segundos) return "";
  const m = Math.floor(segundos / 60);
  return ` (${m}:${String(Math.floor(segundos % 60)).padStart(2, "0")})`;
}

function descreverFila(motor: Motor): RespostaFreddy {
  const { tocando, proximas, repetir } = motor.estado();
  if (!tocando) return { texto: "Não tem nada tocando, e a fila está vazia." };
  const linhas = [`🎵 Tocando: ${mostrar(tocando.titulo)}${duracao(tocando.duracaoSegundos)}${repetir ? " 🔁 (repetindo)" : ""}`];
  if (!proximas.length) linhas.push("A fila está vazia.");
  else {
    linhas.push("📜 Próximas:");
    proximas.slice(0, MUSICAS_MOSTRADAS_NA_FILA).forEach((m, i) => linhas.push(`${i + 1}. ${m.titulo}${duracao(m.duracaoSegundos)}`));
    if (proximas.length > MUSICAS_MOSTRADAS_NA_FILA) linhas.push(`… e mais ${proximas.length - MUSICAS_MOSTRADAS_NA_FILA}`);
  }
  return { texto: linhas.join("\n") };
}

/** O que o Freddy fala sozinho quando a fila anda (o "avisar" do Bardo). */
export function falaDoEvento(evento: EventoMotor): RespostaFreddy {
  switch (evento.tipo) {
    case "tocando_agora":
      return { texto: `Tocando agora ${mostrar(evento.musica.titulo)} 🎵` };
    case "fila_acabou":
      return { texto: "A fila acabou. Pede mais uma? 🦜" };
    case "falha":
      return { texto: `Não consegui tocar ${mostrar(evento.musica.titulo)} (${evento.motivo}), pulei.` };
  }
}
