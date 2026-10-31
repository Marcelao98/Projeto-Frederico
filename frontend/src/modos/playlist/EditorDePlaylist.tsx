/**
 * Editar uma playlist salva sem mexer na fila: tirar, reordenar (arrastar ou
 * Alt+setas), renomear, e tocar ou pôr na fila quando estiver pronta.
 * Cada mudança grava na hora (no Freddy, se ligado).
 */

import { useEffect, useState, type DragEvent, type KeyboardEvent } from "react";
import { CartaoMusica } from "../../componentes/CartaoMusica";
import { Icone } from "../../componentes/Icone";
import { moverNaPlaylist, playlists, removerDaPlaylist, renomearPlaylist } from "../../dados/playlists";
import { useArmazem } from "../../dados/useArmazem";
import { useMotor } from "../../motor/contexto";
import { tocarPlaylist, porPlaylistNaFila } from "./usarPlaylist";

export function EditorDePlaylist({ id, fechar, avisar }: { id: string; fechar: () => void; avisar: (t: string) => void }) {
  const motor = useMotor();
  const playlist = useArmazem(playlists).find((p) => p.id === id);
  const [nome, setNome] = useState(playlist?.nome ?? "");
  const [arrastado, setArrastado] = useState<number | null>(null);
  const [alvo, setAlvo] = useState<number | null>(null);

  useEffect(() => {
    if (playlist) setNome(playlist.nome);
  }, [playlist?.nome]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!playlist) {
    return (
      <div className="editor-playlist">
        <p className="vazio">Essa playlist não existe mais.</p>
        <button className="botao" onClick={fechar}>
          Voltar pra fila
        </button>
      </div>
    );
  }

  function renomear() {
    if (!playlist || nome.trim() === playlist.nome) return;
    const erro = renomearPlaylist(id, nome);
    if (erro) {
      avisar(`Não renomeei: ${erro}`);
      setNome(playlist.nome);
    } else avisar(`Agora se chama "${nome.trim()}"`);
  }

  function soltar(e: DragEvent, indice: number) {
    e.preventDefault();
    if (arrastado !== null) moverNaPlaylist(id, arrastado, arrastado < indice ? indice - 1 : indice);
    setArrastado(null);
    setAlvo(null);
  }

  function teclar(e: KeyboardEvent, i: number) {
    if (!e.altKey || !playlist) return;
    if (e.key === "ArrowUp" && i > 0) {
      e.preventDefault();
      moverNaPlaylist(id, i, i - 1);
    } else if (e.key === "ArrowDown" && i < playlist.musicas.length - 1) {
      e.preventDefault();
      moverNaPlaylist(id, i, i + 1);
    }
  }

  return (
    <div className="editor-playlist">
      <div className="editor-topo">
        <button className="botao-icone" onClick={fechar} title="Voltar pra fila">
          ←
        </button>
        <div className="editor-nome">
          <span className="rotulo">Editando playlist</span>
          <input
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            onBlur={renomear}
            onKeyDown={(e) => {
              if (e.key === "Enter") e.currentTarget.blur();
              if (e.key === "Escape") {
                setNome(playlist.nome);
                e.currentTarget.blur();
              }
            }}
            aria-label="Nome da playlist"
          />
        </div>
      </div>

      <div className="fila-acoes">
        <button className="botao destaque" disabled={!playlist.musicas.length} onClick={() => void tocarPlaylist(motor, playlist, avisar)}>
          <Icone nome="tocar" tamanho={14} /> Tocar
        </button>
        <button className="botao" disabled={!playlist.musicas.length} onClick={() => void porPlaylistNaFila(motor, playlist, avisar)}>
          <Icone nome="mais" tamanho={15} /> Pôr na fila
        </button>
        <span className="contagem-grande">
          {playlist.musicas.length} música{playlist.musicas.length === 1 ? "" : "s"}
        </span>
      </div>

      <ol className="lista-fila" onDragLeave={() => setAlvo(null)}>
        {playlist.musicas.map((m, i) => (
          <li
            key={`${m.link}-${i}`}
            draggable
            tabIndex={0}
            className={`${arrastado === i ? "arrastando" : ""} ${alvo === i ? "alvo" : ""}`}
            onDragStart={(e) => {
              setArrastado(i);
              e.dataTransfer.effectAllowed = "move";
            }}
            onDragOver={(e) => {
              e.preventDefault();
              setAlvo(i);
            }}
            onDrop={(e) => soltar(e, i)}
            onDragEnd={() => {
              setArrastado(null);
              setAlvo(null);
            }}
            onKeyDown={(e) => teclar(e, i)}
            aria-label={`${i + 1}. ${m.titulo}. Alt+setas pra mover.`}
          >
            <span className="alca" aria-hidden="true">
              <Icone nome="arrastar" tamanho={14} />
            </span>
            <span className="numero">{i + 1}</span>
            <CartaoMusica
              musica={m}
              compacto
              acoes={
                <button className="botao-icone pequeno" onClick={() => removerDaPlaylist(id, i)} title="Tirar da playlist">
                  <Icone nome="x" tamanho={14} />
                </button>
              }
            />
          </li>
        ))}
        {playlist.musicas.length > 0 && (
          <li
            className={`fim-da-fila ${alvo === playlist.musicas.length ? "alvo" : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              setAlvo(playlist.musicas.length);
            }}
            onDrop={(e) => soltar(e, playlist.musicas.length)}
          >
            fim da playlist
          </li>
        )}
        {!playlist.musicas.length && (
          <li className="vazio">Vazia. Põe músicas pelo botão 📁 no acervo, ao lado.</li>
        )}
      </ol>
    </div>
  );
}
