/**
 * Playlists salvas pelo chat:
 *
 *   "playlists"                         → lista as salvas
 *   "toca a playlist sessão 12"         → troca a fila pela playlist e toca
 *   "põe a playlist cripta na fila"     → acrescenta no fim, sem parar o que toca
 *   "salva a fila como sessão 12"       → a que toca + a fila (mesmo nome substitui)
 *
 * Mora fora do pedido.ts (gêmeo do Python): lá "playlist" é palavra de "mostra
 * a fila". Por isso o chat olha aqui antes.
 */

import { acharPlaylist, playlists, salvarPlaylist, type PlaylistSalva } from "../../dados/playlists";
import type { Motor } from "../../motor/tipos";
import { MAX_FILA } from "../../motor/tipos";
import { normalizar } from "../../nucleo/texto";
import type { Musica } from "../../nucleo/tipos";

export interface FalaDePlaylist {
  texto: string;
  musicas?: Musica[];
}

const LISTAR_RE = /^(?:quais (?:sao |são )?(?:as )?|mostra (?:as )?|minhas |lista (?:as )?)?playlists(?: salvas)?\s*\??$/iu;
const ENFILEIRAR_RE =
  /^(?:p[õo]e|bota|coloca|adiciona|add)\s+(?:a\s+)?playlist\s+(.+?)\s+(?:na|no fim da)\s+fila[.!]*$/iu;
const ADICIONAR_RE = /^(?:adiciona|add)\s+(?:a\s+)?playlist\s+(.+?)[.!]*$/iu;
const TOCAR_RE = /^(?:toca|toque|tocar|p[õo]e|bota|coloca|play|carrega|abre)\s+(?:a\s+)?playlist\s+(.+?)[.!]*$/iu;
const SALVAR_RE = /^salv(?:a|ar|e)\s+(?:a\s+)?(?:fila|playlist)\s+(?:como|com o nome(?: de)?)\s+(.+?)[.!]*$/iu;

const negrito = (t: string) => `**${t.replace(/\*/g, "")}**`;
const plural = (n: number, s: string, p = `${s}s`) => `${n} ${n === 1 ? s : p}`;
const semAspas = (t: string) => t.trim().replace(/^["“'«]+|["”'»]+$/g, "").trim();

/** Pra prévia embaixo do campo. */
export function ehComandoDePlaylist(texto: string): string | null {
  const t = texto.trim();
  if (LISTAR_RE.test(t)) return "mostrar as playlists salvas";
  if (SALVAR_RE.test(t)) return "salvar a fila como playlist";
  if (ENFILEIRAR_RE.test(t) || ADICIONAR_RE.test(t)) return "pôr a playlist no fim da fila";
  if (TOCAR_RE.test(t)) return "tocar a playlist (troca a fila)";
  return null;
}

/** Se o texto é sobre playlist salva, a resposta; senão, null (segue pro resto do chat). */
export async function tentarPlaylist(texto: string, motor: Motor): Promise<FalaDePlaylist | null> {
  const t = texto.trim();
  if (LISTAR_RE.test(t)) return listar();

  const salvar = SALVAR_RE.exec(t);
  if (salvar) return salvarFila(semAspas(salvar[1]), motor);

  const enfileirar = ENFILEIRAR_RE.exec(t) ?? ADICIONAR_RE.exec(t);
  if (enfileirar) return usar(semAspas(enfileirar[1]), motor, "fila");

  const tocar = TOCAR_RE.exec(t);
  if (tocar) return usar(semAspas(tocar[1]), motor, "tocar");

  return null;
}

function listar(): FalaDePlaylist {
  const lista = playlists.ler();
  if (!lista.length) {
    return { texto: "Nenhuma playlist salva ainda. Monta a fila e manda **salva a fila como sessão 12**." };
  }
  const linhas = lista.map((p) => `• ${negrito(p.nome)} (${plural(p.musicas.length, "música")})`);
  return { texto: `📁 Suas playlists:\n${linhas.join("\n")}\n\nPra tocar: **toca a playlist ${lista[0].nome}**.` };
}

function salvarFila(nome: string, motor: Motor): FalaDePlaylist {
  if (!nome) return { texto: "Faltou o nome. Ex.: **salva a fila como sessão 12**." };
  const { tocando, proximas } = motor.estado();
  const todas = tocando ? [tocando, ...proximas] : proximas;
  if (!todas.length) return { texto: "A fila está vazia: põe umas músicas antes de salvar." };
  const jaTinha = playlists.ler().some((p) => normalizar(p.nome) === normalizar(nome));
  const salva = salvarPlaylist(nome, todas);
  return { texto: `${jaTinha ? "Atualizei" : "Salvei"} a playlist ${negrito(salva.nome)} com ${plural(todas.length, "música")} 💾` };
}

/** Escolhe a playlist pelo nome; pergunta se não achar ou se tiver mais de uma. */
function escolher(nome: string): PlaylistSalva | FalaDePlaylist {
  const lista = playlists.ler();
  if (!lista.length) return { texto: "Você ainda não tem playlist salva. Monta a fila e manda **salva a fila como sessão 12**." };
  const achadas = acharPlaylist(nome, lista);
  if (achadas.length === 1) return achadas[0];
  if (achadas.length > 1) {
    return { texto: `Tenho mais de uma com "${nome}": ${achadas.map((p) => negrito(p.nome)).join(", ")}. Qual delas?` };
  }
  const algumas = lista.slice(0, 6).map((p) => negrito(p.nome)).join(", ");
  return { texto: `Não achei a playlist "${nome}". Tenho: ${algumas}${lista.length > 6 ? "…" : ""}.` };
}

async function usar(nome: string, motor: Motor, como: "tocar" | "fila"): Promise<FalaDePlaylist> {
  const escolhida = escolher(nome);
  if ("texto" in escolhida) return escolhida;
  const p = escolhida;
  if (!p.musicas.length) return { texto: `A playlist ${negrito(p.nome)} está vazia.` };

  if (como === "tocar") {
    // "Começar a sessão": a fila vira a playlist.
    await motor.executar({ tipo: "limpar_fila" });
    const r = await motor.executar({ tipo: "adicionar", musicas: p.musicas, onde: "agora" });
    return {
      texto: `Tocando a playlist ${negrito(p.nome)} 🎵 (${plural(r.entraram, "música")})${avisoDeLimite(r.entraram, p.musicas.length)}`,
      musicas: p.musicas.slice(0, r.entraram),
    };
  }

  const r = await motor.executar({ tipo: "adicionar", musicas: p.musicas });
  if (!r.entraram) return { texto: `A fila já está cheia (${MAX_FILA}). Tira algumas ou manda **limpa a fila**.` };
  const comecou = r.comecou ? ", e já comecei a tocar" : "";
  return {
    texto: `Pus a playlist ${negrito(p.nome)} na fila (${plural(r.entraram, "música")})${comecou} 📜${avisoDeLimite(r.entraram, p.musicas.length)}`,
    musicas: p.musicas.slice(0, r.entraram),
  };
}

/** "Entraram 50 de 62: a fila encheu." (vazio se coube tudo) */
export function avisoDeLimite(entraram: number, total: number): string {
  return entraram < total ? `\n⚠️ Entraram ${entraram} de ${total}: a fila encheu (cabem ${MAX_FILA} esperando).` : "";
}
