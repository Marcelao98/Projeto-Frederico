import { useEffect, useRef, useState } from "react";
import { BarraDoPlayer } from "./componentes/BarraDoPlayer";
import { Calopsita } from "./componentes/Calopsita";
import { Icone } from "./componentes/Icone";
import { acervoLocal } from "./dados/acervo";
import { modoAtual, videoAberto } from "./dados/preferencias";
import { TEMAS, proximoTema, temaAtual } from "./dados/temas";
import { useArmazem } from "./dados/useArmazem";
import { useEstadoDoMotor, useMotor } from "./motor/contexto";
import { MODOS } from "./modos/registro";

function digitando(alvo: EventTarget | null) {
  return alvo instanceof HTMLElement && (alvo.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(alvo.tagName));
}

export function App({ palcoDoVideo }: { palcoDoVideo: HTMLElement }) {
  const motor = useMotor();
  const { tocando, situacao } = useEstadoDoMotor();
  const idDoModo = useArmazem(modoAtual);
  const comVideo = useArmazem(videoAberto);
  const tema = useArmazem(temaAtual);
  const doca = useRef<HTMLDivElement>(null);
  const modo = MODOS.find((m) => m.id === idDoModo) ?? MODOS[0];

  // O player do YouTube mora num elemento fixo, criado uma vez só: mudar ele
  // de lugar no DOM recarregaria o vídeo.
  useEffect(() => {
    doca.current?.appendChild(palcoDoVideo);
  }, [palcoDoVideo]);

  useEffect(() => {
    document.title = tocando ? `${situacao === "pausado" ? "⏸" : "▶"} ${tocando.titulo} · Freddy` : "Freddy";
  }, [tocando, situacao]);

  useEffect(() => {
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.altKey && /^[1-9]$/.test(e.key)) {
        const m = MODOS[Number(e.key) - 1];
        if (m) {
          e.preventDefault();
          modoAtual.escrever(m.id);
        }
        return;
      }
      if (digitando(e.target)) return;
      if (e.code === "Space") {
        e.preventDefault();
        void motor.executar({ tipo: "alternar_pausa" });
      } else if (e.key === "/") {
        e.preventDefault();
        modoAtual.escrever("chat");
      }
    };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [motor]);

  const [mostrarAjuda, setMostrarAjuda] = useState(false);

  return (
    <div className="app">
      <aside className="lateral">
        <div className="marca">
          <button
            className="marca-ave"
            onClick={() => temaAtual.escrever(proximoTema(tema))}
            title="Trocar a plumagem"
            aria-label="Trocar a plumagem"
          >
            <Calopsita tamanho={36} />
          </button>
          <div>
            <div className="marca-nome">Freddy</div>
            <div className="marca-sub">o som da mesa</div>
          </div>
        </div>

        <nav className="navegacao" aria-label="Modos">
          {MODOS.map((m, i) => (
            <button
              key={m.id}
              className={`item-nav ${m.id === modo.id ? "ativo" : ""}`}
              onClick={() => modoAtual.escrever(m.id)}
              aria-current={m.id === modo.id ? "page" : undefined}
              aria-label={m.emBreve ? `${m.nome} (em breve)` : m.nome}
              title={`${m.descricao} (Alt+${i + 1})`}
            >
              <Icone nome={m.icone} />
              <span className="item-nav-nome">{m.nome}</span>
              {m.emBreve && <span className="selo">breve</span>}
            </button>
          ))}
        </nav>

        <div className="saidas">
          <div className="rotulo">Saída do som</div>
          <div className="saida ativa" title="Toca aqui mesmo, neste computador">
            <Icone nome="volume" tamanho={16} /> Este computador <span className="luz" />
          </div>
          <div className="saida" title="Chega com o backend do Freddy">
            <Icone nome="mic" tamanho={16} /> Mic virtual <span className="selo">backend</span>
          </div>
          <div className="saida" title="Chega com o backend do Freddy">
            <Icone nome="discord" tamanho={16} /> Discord <span className="selo">backend</span>
          </div>
        </div>

        <div className="plumagens">
          <div className="rotulo">Plumagem</div>
          <div className="plumagens-grade" role="radiogroup" aria-label="Plumagem">
            {TEMAS.map((t) => (
              <button
                key={t.id}
                role="radio"
                aria-checked={t.id === tema}
                className={`plumagem ${t.id === tema ? "ativa" : ""}`}
                onClick={() => temaAtual.escrever(t.id)}
                title={`${t.nome}: ${t.descricao}`}
              >
                {/* O data-tema aqui pinta só esta ave com as cores do tema dela. */}
                <span data-tema={t.id} className="plumagem-ave">
                  <Calopsita tamanho={30} />
                </span>
              </button>
            ))}
          </div>
          <div className="plumagem-nome">{TEMAS.find((t) => t.id === tema)?.nome}</div>
        </div>

        <div className={`doca-video ${comVideo ? "" : "fechada"} ${tocando ? "" : "sem-video"}`}>
          <button className="doca-alternar" onClick={() => videoAberto.escrever(!comVideo)}>
            <Icone nome="video" tamanho={14} /> {comVideo ? "Esconder vídeo" : "Mostrar vídeo"}
          </button>
          <div className="doca-palco" ref={doca} />
        </div>

        <button className="botao-texto atalhos-teclado" onClick={() => setMostrarAjuda(!mostrarAjuda)}>
          Atalhos de teclado
        </button>
        {mostrarAjuda && (
          <dl className="lista-atalhos">
            <dt>Espaço</dt>
            <dd>pausa / continua</dd>
            <dt>/</dt>
            <dd>vai pro chat</dd>
            <dt>Alt+1…{MODOS.length}</dt>
            <dd>troca de modo</dd>
            <dt>↑ ↓</dt>
            <dd>pedidos anteriores (chat)</dd>
            <dt>Alt+↑ ↓</dt>
            <dd>move na fila</dd>
          </dl>
        )}
      </aside>

      <main className="principal">
        <modo.Componente acervo={acervoLocal} />
      </main>

      <BarraDoPlayer />
    </div>
  );
}
