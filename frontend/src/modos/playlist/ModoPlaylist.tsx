/** Modo Playlist: monta a fila na mão, do acervo, e salva pra próxima sessão. */

import { useEffect, useRef, useState } from "react";
import type { Acervo } from "../../estado/acervo";
import { PainelAcervo } from "./PainelAcervo";
import { PainelFila } from "./PainelFila";
import "./playlist.css";

export function ModoPlaylist({ acervo }: { acervo: Acervo }) {
  const [aviso, setAviso] = useState<string | null>(null);
  const [editando, setEditando] = useState<string | null>(null);
  const prazo = useRef<ReturnType<typeof setTimeout>>();

  const avisar = (texto: string) => {
    setAviso(texto);
    clearTimeout(prazo.current);
    prazo.current = setTimeout(() => setAviso(null), 2600);
  };
  useEffect(() => () => clearTimeout(prazo.current), []);

  return (
    <section className="modo modo-playlist">
      <header className="modo-topo">
        <div>
          <h1>Playlist</h1>
          <p>Escolhe faixa por faixa, arrasta pra reordenar e salva pra próxima sessão.</p>
        </div>
      </header>
      <div className="playlist-grade">
        <PainelAcervo acervo={acervo} avisar={avisar} editando={editando} editar={setEditando} />
        <PainelFila avisar={avisar} editando={editando} editar={setEditando} />
      </div>
      <div className={`aviso-flutuante ${aviso ? "visivel" : ""}`} role="status">
        {aviso}
      </div>
    </section>
  );
}
