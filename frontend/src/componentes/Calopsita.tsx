/**
 * O Frederico. Cada plumagem pode ter a sua ilustração em public/aves/:
 *   <tema>.png        corpo inteiro, pros lugares grandes (boas-vindas)
 *   <tema>-rosto.png  só a cabeça, pros pequenos (logo, seletor, chat)
 * Falta o rosto: usa o corpo inteiro. Falta os dois: desenha a calopsita
 * robô em SVG com as cores do tema.
 */

import { useState } from "react";
import { temaAtual } from "../dados/temas";
import { useArmazem } from "../dados/useArmazem";

/** Abaixo disso o corpo inteiro (com a cauda comprida) vira um risquinho. */
const TAMANHO_DO_ROSTO = 60;

// Arquivos que já falharam: não tenta de novo a cada render.
const semArquivo = new Set<string>();

export function Calopsita({ tamanho = 40, tema }: { tamanho?: number; tema?: string }) {
  const atual = useArmazem(temaAtual);
  const plumagem = tema ?? atual;
  const [, redesenhar] = useState(0);

  const candidatos = tamanho < TAMANHO_DO_ROSTO ? [`${plumagem}-rosto`, plumagem] : [plumagem];
  const arquivo = candidatos.find((c) => !semArquivo.has(c));

  if (arquivo) {
    const rosto = arquivo.endsWith("-rosto");
    return (
      <img
        key={arquivo}
        className={rosto ? "ave-rosto" : undefined}
        src={`${import.meta.env.BASE_URL}aves/${arquivo}.png`}
        width={tamanho}
        height={tamanho}
        alt=""
        draggable={false}
        style={{ objectFit: "contain" }}
        onError={() => {
          semArquivo.add(arquivo);
          redesenhar((n) => n + 1);
        }}
      />
    );
  }
  return <CalopsitaDesenhada tamanho={tamanho} />;
}

/** A calopsita robô em SVG. As cores vêm do tema (--ave-*). */
function CalopsitaDesenhada({ tamanho }: { tamanho: number }) {
  return (
    <svg width={tamanho} height={tamanho} viewBox="0 0 64 64" aria-hidden="true">
      <path
        d="M30 14c-2-6 1-11 6-12-2 4-1 7 1 9 1-5 5-8 9-8-3 3-4 7-3 11Z"
        fill="var(--ave-crista)"
        stroke="var(--ave-borda)"
        strokeWidth="1"
      />
      {/* corpo e asas */}
      <circle cx="32" cy="36" r="20" fill="var(--ave-asa)" stroke="var(--ave-borda)" strokeWidth="2" />
      {/* cabeça e rosto */}
      <circle cx="32" cy="31" r="15" fill="var(--ave-corpo)" />
      <circle cx="24.5" cy="37" r="4.5" fill="var(--ave-bochecha)" />
      <circle cx="39.5" cy="37" r="4.5" fill="var(--ave-bochecha)" />
      <rect x="20" y="25.5" width="24" height="8.5" rx="4.25" fill="var(--ave-visor)" />
      <circle cx="26" cy="29.75" r="2.2" fill="var(--ave-olho)" />
      <circle cx="38" cy="29.75" r="2.2" fill="var(--ave-olho)" />
      <path d="M29 36h6l-3 5Z" fill="var(--ave-bico)" />
    </svg>
  );
}
