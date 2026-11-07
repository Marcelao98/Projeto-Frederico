/**
 * O 📁 de cada faixa do acervo: põe a faixa numa playlist salva (ou numa
 * nova) sem tocar nada. Pra preparar a sessão com calma.
 */

import { useRef, useState } from "react";
import { Icone } from "../../componentes/Icone";
import { adicionarNaPlaylist, playlists, salvarPlaylist } from "../../estado/playlists";
import { useArmazem } from "../../estado/useArmazem";
import type { Musica } from "../../comum/tipos";

export function BotaoPlaylist({
  musica,
  avisar,
  editando,
  editar,
}: {
  musica: Musica;
  avisar: (t: string) => void;
  editando: string | null;
  editar: (id: string) => void;
}) {
  const salvas = useArmazem(playlists);
  const [aberto, setAberto] = useState<{ x: number; y: number } | null>(null);
  const [nova, setNova] = useState("");
  const botao = useRef<HTMLButtonElement>(null);

  function abrir() {
    if (aberto) return setAberto(null);
    const r = botao.current?.getBoundingClientRect();
    if (!r) return;
    // Fixo na tela: a lista do acervo rola e cortaria um menu preso nela.
    const altura = Math.min(320, 56 + salvas.length * 34);
    const y = r.bottom + altura > window.innerHeight ? Math.max(8, r.top - altura - 4) : r.bottom + 4;
    setAberto({ x: Math.max(8, r.right - 260), y });
  }

  function por(id: string, nome: string) {
    const r = adicionarNaPlaylist(id, musica);
    avisar(r === "ja_estava" ? `"${musica.titulo}" já está em "${nome}"` : `"${musica.titulo}" entrou em "${nome}" 📁`);
    setAberto(null);
  }

  function criar() {
    const nome = nova.trim();
    if (!nome) return;
    const existente = salvas.find((p) => p.nome.trim().toLowerCase() === nome.toLowerCase());
    if (existente) return por(existente.id, existente.nome);
    const p = salvarPlaylist(nome, [musica]);
    avisar(`Playlist "${p.nome}" criada com "${musica.titulo}" 📁`);
    setNova("");
    setAberto(null);
    editar(p.id);
  }

  // Com uma playlist aberta no editor, a ordem é ela primeiro.
  const ordem = editando ? [...salvas.filter((p) => p.id === editando), ...salvas.filter((p) => p.id !== editando)] : salvas;

  return (
    <>
      <button
        ref={botao}
        className={`botao-icone pequeno ${aberto ? "ligado" : ""}`}
        onClick={abrir}
        title="Pôr numa playlist salva"
        aria-haspopup="menu"
        aria-expanded={aberto !== null}
      >
        <Icone nome="pasta" tamanho={15} />
      </button>
      {aberto && (
        <>
          <div className="menu-fundo" onClick={() => setAberto(null)} />
          <div
            className="menu-playlist"
            role="menu"
            style={{ left: aberto.x, top: aberto.y }}
            onKeyDown={(e) => e.key === "Escape" && setAberto(null)}
          >
            <div className="menu-titulo">Pôr em…</div>
            {ordem.map((p) => (
              <button key={p.id} role="menuitem" className="menu-item" onClick={() => por(p.id, p.nome)}>
                <Icone nome="pasta" tamanho={14} />
                <span>{p.nome}</span>
                {p.id === editando && <span className="selo">aberta</span>}
                <span className="contagem">{p.musicas.length}</span>
              </button>
            ))}
            <form
              className="menu-nova"
              onSubmit={(e) => {
                e.preventDefault();
                criar();
              }}
            >
              <input
                autoFocus={!salvas.length}
                value={nova}
                onChange={(e) => setNova(e.target.value)}
                placeholder="➕ Nova playlist…"
                aria-label="Nome da nova playlist"
              />
            </form>
          </div>
        </>
      )}
    </>
  );
}
