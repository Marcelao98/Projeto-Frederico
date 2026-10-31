/** Links do YouTube: reconhecer, extrair e tirar o id do vídeo. */

const PADRAO_URL =
  "(https?://)?(www\\.|music\\.)?(youtube\\.com/watch\\?v=[\\w-]+|youtu\\.be/[\\w-]+)(\\S*)?";

export const URL_YOUTUBE_RE = new RegExp(PADRAO_URL, "i");
export const URL_YOUTUBE_GLOBAL_RE = new RegExp(PADRAO_URL, "gi");

/** A primeira URL do YouTube no texto, ou null. */
export function extrairLinkYoutube(texto: string): string | null {
  return URL_YOUTUBE_RE.exec(texto)?.[0] ?? null;
}

/** O id do vídeo (watch?v=, youtu.be/), ou o próprio texto se não achar. */
export function videoId(link: string): string {
  return /(?:[?&]v=|youtu\.be\/)([\w-]+)/.exec(link)?.[1] ?? link;
}

/** Link de watch "limpo", que não expira e serve de chave do vídeo. */
export function linkDeWatch(link: string): string {
  return `https://www.youtube.com/watch?v=${videoId(link)}`;
}

export function miniatura(link: string): string {
  return `https://i.ytimg.com/vi/${videoId(link)}/mqdefault.jpg`;
}
