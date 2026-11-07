/** Tocar ou enfileirar uma playlist salva pelos botões (o chat faz o mesmo em playlistsChat.ts). */

import type { PlaylistSalva } from "../../estado/playlists";
import type { Motor } from "../../motor/tipos";
import { avisoDeLimite } from "../chat/playlistsChat";

const plural = (n: number) => `${n} música${n === 1 ? "" : "s"}`;

/** Troca a fila pela playlist e começa a tocar (o "começar a sessão"). */
export async function tocarPlaylist(motor: Motor, p: PlaylistSalva, avisar: (t: string) => void) {
  await motor.executar({ tipo: "limpar_fila" });
  const r = await motor.executar({ tipo: "adicionar", musicas: p.musicas, onde: "agora" });
  avisar(`Tocando "${p.nome}" (${plural(r.entraram)}) 🎵${avisoDeLimite(r.entraram, p.musicas.length).replace("\n⚠️", " ·")}`);
}

export async function porPlaylistNaFila(motor: Motor, p: PlaylistSalva, avisar: (t: string) => void) {
  const r = await motor.executar({ tipo: "adicionar", musicas: p.musicas });
  if (!r.entraram) return avisar("A fila está cheia.");
  avisar(`"${p.nome}" na fila (${plural(r.entraram)})${avisoDeLimite(r.entraram, p.musicas.length).replace("\n⚠️", " ·")}`);
}
