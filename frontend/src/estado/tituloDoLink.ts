/** Título de um vídeo do YouTube pelo oEmbed (público, sem chave). null se falhar. */
export async function tituloDoLink(link: string): Promise<string | null> {
  const controle = new AbortController();
  const prazo = setTimeout(() => controle.abort(), 2500);
  try {
    const url = `https://www.youtube.com/oembed?format=json&url=${encodeURIComponent(link)}`;
    const resposta = await fetch(url, { signal: controle.signal });
    if (!resposta.ok) return null;
    const dados = (await resposta.json()) as { title?: string };
    return dados.title ?? null;
  } catch {
    return null;
  } finally {
    clearTimeout(prazo);
  }
}
