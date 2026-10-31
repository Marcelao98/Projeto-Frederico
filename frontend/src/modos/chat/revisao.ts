/**
 * Revisar os temas do acervo pelo chat: o Freddy mostra os temas de uma
 * faixa e a pessoa diz se está certo ou corrige.
 *
 *   "temas"            → os temas da música que toca, com "tá certo?"
 *   "temas: a, b, c"   → troca os temas (da que está em revisão, ou da que toca)
 *   "revisar [busca]"  → passa faixa por faixa (as "não classificado" primeiro)
 *   "tá certo" / "não" → responde a revisão aberta (os botões fazem o mesmo)
 *
 * Gravar precisa do Freddy (o acervo mora nele). Só o painel tem isso: o
 * interpretador de pedidos (pedido.ts, gêmeo do Python) não muda.
 */

import { rotuloCategoria, type Acervo } from "../../dados/acervo";
import { normalizar } from "../../nucleo/texto";
import type { Faixa } from "../../nucleo/tipos";
import type { Motor } from "../../motor/tipos";

export const NAO_CLASSIFICADO = "não classificado";

/** A pergunta "tá certo?" sobre uma faixa, que a tela mostra com botões. */
export interface Revisao {
  faixaId: string;
  titulo: string;
  origem: string;
  temas: string[];
  categorias: string[];
  /** Faz parte de um "revisar": respondeu, vem a próxima. */
  emSessao: boolean;
}

export interface ContextoDeRevisao {
  motor: Motor;
  acervo: Acervo;
  /** Grava os temas no Freddy e devolve a faixa como ficou (undefined = Freddy desligado). */
  editarTemas?: (faixaId: string, temas: string[]) => Promise<Faixa>;
}

export interface FalaDaRevisao {
  texto: string;
  revisao?: Revisao;
}

const DEFINIR_RE = /^(?:temas|tags|tema|tag)\s*[:=]\s*(.*)$/s;
const MOSTRAR_RE = /^(?:quais (?:sao )?(?:os )?)?(?:temas|tags|climas)(?: (?:dessa|desta|da que (?:ta )?toca(?:ndo)?|dela))?\s*\??$/;
const REVISAR_RE = /^revis(?:a|ar|ao)\b\s*(.*)$/;
const PARAR_RE = /^(?:para|parar|chega|sair|encerra|encerrar)(?: (?:de|a) revis(?:ar|ao))$/;
const CERTO_RE = /^(?:sim|s|ta certo|esta certo|certo|certinho|isso|isso mesmo|ok|ta|ta bom|beleza|correto|perfeito|👍)[!. ]*$/;
const ERRADO_RE = /^(?:nao|n|errado|ta errado|esta errado|nada a ver|nope)[!. ]*$/;

let aberta: (Revisao & { esperandoTemas: boolean }) | null = null;
let sessao: { ids: string[]; i: number } | null = null;

/** A revisão esperando resposta (pra tela saber se os botões ainda valem). */
export function revisaoAberta(): Revisao | null {
  return aberta;
}

/** Pros testes e pro "limpar conversa". */
export function esquecerRevisao() {
  aberta = null;
  sessao = null;
}

/** "taverna, alegre e calmo" → ["taverna", "alegre", "calmo"]. */
export function separarTemas(texto: string): string[] {
  const temas = texto
    .split(/\s*(?:[,;/|\n]|\s\be\b\s)\s*/iu)
    .map((t) => t.trim().toLowerCase().replace(/[.!?]+$/, ""))
    .filter((t) => t.length > 1);
  return [...new Set(temas)].slice(0, 12);
}

const negrito = (t: string) => `**${t.replace(/\*/g, "")}**`;

function descrever(r: Revisao, posicao: string): string {
  const titulo = `${posicao}${negrito(r.titulo)} (${r.origem})`;
  const semTema = !r.temas.length || (r.temas.length === 1 && r.temas[0] === NAO_CLASSIFICADO);
  if (semTema) return `${titulo}\nAinda está **sem temas**. Quais são? (ex.: taverna, alegre)`;
  const busca = r.categorias.length ? r.categorias.map(rotuloCategoria).join(", ") : "nenhuma categoria (a busca não acha ela)";
  return `${titulo}\nTemas: ${r.temas.join(", ")}\nNa busca entra como: ${busca}\n**Tá certo?**`;
}

function abrir(faixa: Faixa, emSessao: boolean): FalaDaRevisao {
  const revisao: Revisao = {
    faixaId: faixa.id,
    titulo: faixa.nome,
    origem: faixa.origem.nome,
    temas: faixa.temas,
    categorias: faixa.categorias ?? [],
    emSessao,
  };
  const semTema = !faixa.temas.length || (faixa.temas.length === 1 && faixa.temas[0] === NAO_CLASSIFICADO);
  aberta = { ...revisao, esperandoTemas: semTema };
  const posicao = emSessao && sessao ? `Revisão ${sessao.i + 1} de ${sessao.ids.length} · ` : "";
  return { texto: descrever(revisao, posicao), revisao };
}

function proxima(acervo: Acervo): FalaDaRevisao {
  while (sessao && sessao.i + 1 < sessao.ids.length) {
    sessao.i += 1;
    const faixa = acervo.porId(sessao.ids[sessao.i]);
    if (faixa) return abrir(faixa, true);
  }
  const total = sessao?.ids.length ?? 0;
  esquecerRevisao();
  return { texto: `Revisão terminada (${total} faixa${total === 1 ? "" : "s"}) 🎉 Valeu!` };
}

/** Depois de responder: segue a sessão, ou fecha. */
function depois(texto: string, acervo: Acervo, emSessao: boolean): FalaDaRevisao {
  if (!emSessao) {
    aberta = null;
    return { texto };
  }
  const seguinte = proxima(acervo);
  return { texto: `${texto}\n\n${seguinte.texto}`, revisao: seguinte.revisao };
}

/** A resposta a uma revisão aberta: "certo", "parar" ou os temas novos. */
export async function responderRevisao(
  resposta: "certo" | "parar" | { temas: string[] },
  ctx: ContextoDeRevisao,
): Promise<FalaDaRevisao> {
  const r = aberta;
  if (!r) return { texto: "Não tem revisão aberta. Manda **revisar** ou **temas**." };
  if (resposta === "parar") {
    const feitas = sessao ? sessao.i : 0;
    esquecerRevisao();
    return { texto: feitas ? `Parei a revisão (${feitas} revisada${feitas > 1 ? "s" : ""}). Continua quando quiser.` : "Beleza, parei." };
  }
  if (resposta === "certo") return depois("👍 Anotado.", ctx.acervo, r.emSessao);
  if (!ctx.editarTemas) return { texto: "Pra mudar o acervo eu preciso do Freddy ligado (python -m freddy)." };
  if (!resposta.temas.length) return { texto: "Não peguei nenhum tema. Manda separado por vírgula (ex.: taverna, alegre)." };
  const faixa = await ctx.editarTemas(r.faixaId, resposta.temas);
  const busca = faixa.categorias?.length ? ` (na busca: ${faixa.categorias.map(rotuloCategoria).join(", ")})` : "";
  return depois(`Pronto: ${negrito(faixa.nome)} agora é ${faixa.temas.join(", ")}${busca} 🪶`, ctx.acervo, r.emSessao);
}

/** Se o texto é coisa da revisão, a resposta; senão, null (segue pro resto do chat). */
export async function tentarRevisao(
  texto: string,
  ctx: ContextoDeRevisao,
  ehPedido: (texto: string) => boolean,
): Promise<FalaDaRevisao | null> {
  const n = normalizar(texto).trim();

  const definir = DEFINIR_RE.exec(n);
  if (definir) {
    const temas = separarTemas(texto.slice(texto.search(/[:=]/) + 1));
    if (!aberta) {
      const faixa = faixaQueToca(ctx);
      if ("texto" in faixa) return faixa;
      aberta = { ...abrir(faixa, false).revisao!, esperandoTemas: false };
    }
    return responderRevisao({ temas }, ctx);
  }

  if (MOSTRAR_RE.test(n)) {
    const faixa = faixaQueToca(ctx);
    if ("texto" in faixa) return faixa;
    sessao = null;
    return abrir(faixa, false);
  }

  const revisar = REVISAR_RE.exec(n);
  if (revisar) {
    const busca = texto.trim().replace(/^\S+\s*/, "");
    const achadas = busca ? ctx.acervo.buscar(busca) : ctx.acervo.faixas;
    if (!achadas.length) return { texto: `Não achei nada no acervo com "${busca}" pra revisar.` };
    const semTema = (f: Faixa) => f.temas.length === 0 || f.temas.includes(NAO_CLASSIFICADO);
    const ordem = [...achadas.filter(semTema), ...achadas.filter((f) => !semTema(f))];
    sessao = { ids: ordem.map((f) => f.id), i: 0 };
    const sem = ordem.filter(semTema).length;
    const intro =
      `Bora revisar ${ordem.length} faixa${ordem.length > 1 ? "s" : ""}` +
      (sem ? ` (${sem} sem tema primeiro)` : "") +
      ". Responde **tá certo**, ou manda os temas certos. **para de revisar** encerra.\n\n";
    const primeira = abrir(ordem[0], true);
    return { texto: intro + primeira.texto, revisao: primeira.revisao };
  }

  if (!aberta) return null;
  if (PARAR_RE.test(n)) return responderRevisao("parar", ctx);
  if (CERTO_RE.test(n)) {
    if (aberta.esperandoTemas) return { texto: "Ela está sem temas: me diz quais são (ex.: taverna, alegre)." };
    return responderRevisao("certo", ctx);
  }
  if (ERRADO_RE.test(n)) {
    aberta.esperandoTemas = true;
    return { texto: "Então me diz os temas certos, separados por vírgula (ex.: masmorra, tenso, sombrio)." };
  }
  // Esperando os temas: o que não for pedido de música é a resposta.
  if (aberta.esperandoTemas && !ehPedido(texto)) return responderRevisao({ temas: separarTemas(texto) }, ctx);
  return null;
}

function faixaQueToca({ motor, acervo }: ContextoDeRevisao): Faixa | FalaDaRevisao {
  const tocando = motor.estado().tocando;
  if (!tocando) return { texto: "Não tem nada tocando. Pra revisar o acervo, manda **revisar** (ou **revisar hollow knight**)." };
  const faixa = tocando.faixaId ? acervo.porId(tocando.faixaId) : undefined;
  if (!faixa) return { texto: `${negrito(tocando.titulo)} não está no acervo (veio de um link), então não tem temas.` };
  return faixa;
}

/** Pra prévia embaixo do campo. */
export function ehComandoDeRevisao(texto: string): string | null {
  const n = normalizar(texto).trim();
  if (DEFINIR_RE.test(n)) return "trocar os temas";
  if (MOSTRAR_RE.test(n)) return "mostrar os temas da que toca";
  if (REVISAR_RE.test(n)) return "revisar os temas do acervo";
  return null;
}
