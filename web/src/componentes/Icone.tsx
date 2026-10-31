/** Ícones em SVG (traço de 2px, 24x24). Sem biblioteca. */

const CAMINHOS = {
  chat: "M21 12a8 8 0 0 1-11.6 7.1L4 20.5l1.4-4.6A8 8 0 1 1 21 12Z",
  lista: "M8 6h13M8 12h13M8 18h8M3.5 6h.01M3.5 12h.01M3.5 18h.01",
  mixer: "M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6",
  grade: "M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z",
  tocar: "M7 4.5v15l12.5-7.5Z",
  pausar: "M7 4.5h3.5v15H7zM13.5 4.5H17v15h-3.5z",
  pular: "M5 4.5v15l10-7.5ZM18.5 4.5v15",
  parar: "M6 6h12v12H6z",
  repetir: "M17 2l4 4-4 4M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 0 1-3 3H3",
  volume: "M11 5 6 9H2v6h4l5 4V5ZM15.5 8.5a5 5 0 0 1 0 7M19 5a10 10 0 0 1 0 14",
  mudo: "M11 5 6 9H2v6h4l5 4V5ZM22 9l-6 6M16 9l6 6",
  mais: "M12 5v14M5 12h14",
  lixo: "M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14",
  x: "M18 6 6 18M6 6l12 12",
  arrastar: "M9 5h.01M9 12h.01M9 19h.01M15 5h.01M15 12h.01M15 19h.01",
  embaralhar: "M16 3h5v5M4 20 21 3M21 16v5h-5M15 15l6 6M4 4l5 5",
  salvar: "M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2ZM17 21v-8H7v8M7 3v5h8",
  enviar: "M22 2 11 13M22 2l-7 20-4-9-9-4 20-7Z",
  aSeguir: "M3 12h12M11 6l6 6-6 6M21 5v14",
  busca: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14ZM21 21l-4.3-4.3",
  pasta: "M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z",
  video: "M3 6h13v12H3zM16 10l5-3v10l-5-3",
  discord: "M8 15c3 1.5 5 1.5 8 0M9 11h.01M15 11h.01M7 5c3-1 7-1 10 0l2 4c1 3 1 6 0 9-2 1.2-3.5 1.8-5 2l-1-2M7 5 5 9c-1 3-1 6 0 9 2 1.2 3.5 1.8 5 2l1-2",
  mic: "M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3ZM19 10v2a7 7 0 0 1-14 0v-2M12 19v3",
} as const;

export type NomeIcone = keyof typeof CAMINHOS;

const PREENCHIDOS = new Set<NomeIcone>(["tocar", "pausar", "parar"]);

export function Icone({ nome, tamanho = 18, titulo }: { nome: NomeIcone; tamanho?: number; titulo?: string }) {
  const cheio = PREENCHIDOS.has(nome);
  return (
    <svg
      width={tamanho}
      height={tamanho}
      viewBox="0 0 24 24"
      fill={cheio ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth={cheio ? 0 : 2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden={titulo ? undefined : true}
      role={titulo ? "img" : undefined}
    >
      {titulo && <title>{titulo}</title>}
      <path d={CAMINHOS[nome]} />
    </svg>
  );
}
