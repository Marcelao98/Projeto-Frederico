/** A fila: o que toca, o que vem (arrasta pra reordenar) e as playlists salvas. */

import { useState, type DragEvent, type KeyboardEvent } from "react";
import { CartaoMusica } from "../../componentes/CartaoMusica";
import { Icone } from "../../componentes/Icone";
import { formatarTempo } from "../../componentes/tempo";
import { excluirPlaylist, playlists, salvarPlaylist, type PlaylistSalva } from "../../dados/playlists";
import { useArmazem } from "../../dados/useArmazem";
import { useEstadoDoMotor, useMotor } from "../../motor/contexto";
import { MAX_FILA, type ItemDaFila } from "../../motor/tipos";

export function PainelFila({ avisar }: { avisar: (texto: string) => void }) {
  const motor = useMotor();
  const { tocando, proximas, situacao, repetir } = useEstadoDoMotor();
  const [arrastado, setArrastado] = useState<string | null>(null);
  const [alvo, setAlvo] = useState<number | null>(null);
  const [nome, setNome] = useState("");
  const [salvando, setSalvando] = useState(false);

  const todas = tocando ? [tocando, ...proximas] : proximas;

  function soltar(e: DragEvent, indice: number) {
    e.preventDefault();
    if (arrastado) {
      const de = proximas.findIndex((m) => m.uid === arrastado);
      // Soltar abaixo do próprio lugar: a lista "anda" um pra cima quando ele sai.
      const para = de >= 0 && de < indice ? indice - 1 : indice;
      void motor.executar({ tipo: "mover", uid: arrastado, para });
    }
    setArrastado(null);
    setAlvo(null);
  }

  function teclar(e: KeyboardEvent, item: ItemDaFila, indice: number) {
    if (!e.altKey) return;
    if (e.key === "ArrowUp" && indice > 0) {
      e.preventDefault();
      void motor.executar({ tipo: "mover", uid: item.uid, para: indice - 1 });
    } else if (e.key === "ArrowDown" && indice < proximas.length - 1) {
      e.preventDefault();
      void motor.executar({ tipo: "mover", uid: item.uid, para: indice + 1 });
    }
  }

  function salvar() {
    const n = nome.trim();
    if (!n || !todas.length) return;
    salvarPlaylist(n, todas);
    avisar(`Playlist "${n}" salva com ${todas.length} música${todas.length > 1 ? "s" : ""} 💾`);
    setNome("");
    setSalvando(false);
  }

  return (
    <section className="painel painel-fila" aria-label="Fila">
      <header className="painel-topo">
        <h2>Fila</h2>
        <span className="contagem-grande">
          {proximas.length}/{MAX_FILA}
        </span>
      </header>

      <div className="tocando-agora">
        <div className="rotulo">
          {situacao === "pausado" ? "Pausado" : situacao === "carregando" ? "Carregando" : "Tocando agora"}
          {repetir && <span className="selo">🔁 repetindo</span>}
        </div>
        {tocando ? (
          <CartaoMusica musica={tocando} ativo />
        ) : (
          <div className="vazio">Nada tocando. Põe música pelo acervo ou pelo chat.</div>
        )}
      </div>

      <div className="fila-acoes">
        <button
          className="botao"
          disabled={proximas.length < 2}
          onClick={() => void motor.executar({ tipo: "embaralhar" })}
        >
          <Icone nome="embaralhar" tamanho={15} /> Embaralhar
        </button>
        <button
          className="botao"
          disabled={!proximas.length}
          onClick={() => void motor.executar({ tipo: "limpar_fila" })}
        >
          <Icone nome="lixo" tamanho={15} /> Limpar
        </button>
        <button className="botao" disabled={!todas.length} onClick={() => setSalvando(!salvando)}>
          <Icone nome="salvar" tamanho={15} /> Salvar
        </button>
      </div>

      {salvando && (
        <form
          className="salvar-playlist"
          onSubmit={(e) => {
            e.preventDefault();
            salvar();
          }}
        >
          <input
            autoFocus
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            placeholder="Nome (ex.: Sessão 12, a cripta)"
            aria-label="Nome da playlist"
          />
          <button className="botao destaque" type="submit" disabled={!nome.trim()}>
            Salvar {todas.length}
          </button>
        </form>
      )}

      <ol className="lista-fila" onDragLeave={() => setAlvo(null)}>
        {proximas.map((m, i) => (
          <li
            key={m.uid}
            draggable
            tabIndex={0}
            className={`${arrastado === m.uid ? "arrastando" : ""} ${alvo === i ? "alvo" : ""}`}
            onDragStart={(e) => {
              setArrastado(m.uid);
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
            onKeyDown={(e) => teclar(e, m, i)}
            aria-label={`${i + 1}. ${m.titulo}. Alt+setas pra mover.`}
          >
            <span className="alca" aria-hidden="true">
              <Icone nome="arrastar" tamanho={14} />
            </span>
            <span className="numero">{i + 1}</span>
            <CartaoMusica
              musica={m}
              compacto
              detalhe={m.duracaoSegundos ? `${m.origem ?? "YouTube"} · ${formatarTempo(m.duracaoSegundos)}` : undefined}
              acoes={
                <>
                  <button
                    className="botao-icone pequeno"
                    onClick={() => void motor.executar({ tipo: "tocar_item", uid: m.uid })}
                    title="Tocar esta agora"
                  >
                    <Icone nome="tocar" tamanho={14} />
                  </button>
                  <button
                    className="botao-icone pequeno"
                    onClick={() => void motor.executar({ tipo: "remover", uid: m.uid })}
                    title="Tirar da fila"
                  >
                    <Icone nome="x" tamanho={14} />
                  </button>
                </>
              }
            />
          </li>
        ))}
        {proximas.length > 0 && (
          <li
            className={`fim-da-fila ${alvo === proximas.length ? "alvo" : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              setAlvo(proximas.length);
            }}
            onDrop={(e) => soltar(e, proximas.length)}
          >
            fim da fila
          </li>
        )}
        {!proximas.length && <li className="vazio">A fila está vazia.</li>}
      </ol>

      <PlaylistsSalvas avisar={avisar} />
    </section>
  );
}

function PlaylistsSalvas({ avisar }: { avisar: (texto: string) => void }) {
  const motor = useMotor();
  const salvas = useArmazem(playlists);
  const [confirmando, setConfirmando] = useState<string | null>(null);

  if (!salvas.length) {
    return (
      <div className="salvas">
        <h3>Playlists salvas</h3>
        <p className="apagado">Monta a fila e clica em Salvar. Fica guardada neste navegador.</p>
      </div>
    );
  }

  async function tocar(p: PlaylistSalva) {
    const r = await motor.executar({ tipo: "adicionar", musicas: p.musicas, onde: "agora" });
    avisar(`Tocando "${p.nome}" (${r.entraram} música${r.entraram > 1 ? "s" : ""}) 🎵`);
  }

  async function enfileirar(p: PlaylistSalva) {
    const r = await motor.executar({ tipo: "adicionar", musicas: p.musicas });
    avisar(r.entraram ? `"${p.nome}" na fila (${r.entraram})` : "A fila está cheia.");
  }

  return (
    <div className="salvas">
      <h3>Playlists salvas</h3>
      <ul>
        {salvas.map((p) => (
          <li key={p.id} className="salva">
            <Icone nome="pasta" tamanho={16} />
            <div className="salva-textos">
              <div className="salva-nome">{p.nome}</div>
              <div className="cartao-sub">
                {p.musicas.length} música{p.musicas.length > 1 ? "s" : ""} ·{" "}
                {new Date(p.atualizadaEm).toLocaleDateString("pt-BR")}
              </div>
            </div>
            <button className="botao-icone pequeno" onClick={() => void tocar(p)} title="Tocar agora">
              <Icone nome="tocar" tamanho={14} />
            </button>
            <button className="botao-icone pequeno" onClick={() => void enfileirar(p)} title="Pôr no fim da fila">
              <Icone nome="mais" tamanho={15} />
            </button>
            <button
              className={`botao-icone pequeno ${confirmando === p.id ? "perigo" : ""}`}
              onClick={() => {
                if (confirmando === p.id) {
                  excluirPlaylist(p.id);
                  setConfirmando(null);
                } else setConfirmando(p.id);
              }}
              onBlur={() => setConfirmando(null)}
              title={confirmando === p.id ? "Clica de novo pra excluir" : "Excluir"}
            >
              <Icone nome="lixo" tamanho={14} />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
