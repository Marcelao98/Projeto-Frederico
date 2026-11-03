import { useEffect, useRef, useState } from "react";
import { BarraDoPlayer } from "./componentes/BarraDoPlayer";
import { Calopsita } from "./componentes/Calopsita";
import { Icone } from "./componentes/Icone";
import { acervoAtual } from "./dados/acervo";
import { discord, freddy, freddyLigouDepois, preferenciaDeMotor } from "./dados/freddy";
import { JanelaDiscord } from "./componentes/JanelaDiscord";
import { modoAtual, videoAberto } from "./dados/preferencias";
import { TEMAS, proximoTema, temaAtual } from "./dados/temas";
import { useArmazem } from "./dados/useArmazem";
import { useConexao, useEstadoDoMotor, useMotor } from "./motor/contexto";
import { MODOS } from "./modos/registro";

function digitando(alvo: EventTarget | null) {
  return alvo instanceof HTMLElement && (alvo.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(alvo.tagName));
}

/** `palcoDoVideo` só existe com o motor do navegador (o Freddy toca sem vídeo). */
export function App({ palcoDoVideo }: { palcoDoVideo: HTMLElement | null }) {
  const motor = useMotor();
  const acervo = useArmazem(acervoAtual);
  const { tocando, situacao } = useEstadoDoMotor();
  const idDoModo = useArmazem(modoAtual);
  const comVideo = useArmazem(videoAberto);
  const tema = useArmazem(temaAtual);
  const doca = useRef<HTMLDivElement>(null);
  const modo = MODOS.find((m) => m.id === idDoModo) ?? MODOS[0];

  // O player do YouTube mora num elemento fixo, criado uma vez só: mudar ele
  // de lugar no DOM recarregaria o vídeo.
  useEffect(() => {
    if (palcoDoVideo) doca.current?.appendChild(palcoDoVideo);
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
          <OrigemDoSom comFreddy={!palcoDoVideo} />
          <div className="saida" title="Chega na Fase 4 (mixer)">
            <Icone nome="mic" tamanho={16} /> Mic virtual <span className="selo">breve</span>
          </div>
          <SaidaDiscord comFreddy={!palcoDoVideo} />
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
                  <Calopsita tamanho={30} tema={t.id} />
                </span>
              </button>
            ))}
          </div>
          <div className="plumagem-nome">{TEMAS.find((t) => t.id === tema)?.nome}</div>
        </div>

        {palcoDoVideo && (
          <div className={`doca-video ${comVideo ? "" : "fechada"} ${tocando ? "" : "sem-video"}`}>
            <button className="doca-alternar" onClick={() => videoAberto.escrever(!comVideo)}>
              <Icone nome="video" tamanho={14} /> {comVideo ? "Esconder vídeo" : "Mostrar vídeo"}
            </button>
            <div className="doca-palco" ref={doca} />
          </div>
        )}

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

      <AvisoFreddyLigou />
      <main className="principal">
        <modo.Componente acervo={acervo} />
      </main>

      <BarraDoPlayer />
    </div>
  );
}

const TEXTO_DA_CONEXAO = {
  conectado: "",
  conectando: "conectando…",
  reconectando: "reconectando…",
} as const;

/** "Este computador": pelo navegador ou pelo Freddy, e se o Freddy está conectado. */
function OrigemDoSom({ comFreddy }: { comFreddy: boolean }) {
  const conexao = useConexao();
  const alternar = () => {
    // Troca na próxima abertura: trocar de motor com a fila andando perderia a fila.
    preferenciaDeMotor.escrever(comFreddy ? "navegador" : "auto");
    location.reload();
  };
  const dica = comFreddy
    ? "Tocando pelo Freddy (python -m freddy). Clique pra tocar só pelo navegador."
    : "Tocando pelo navegador (YouTube). Ligue o Freddy e clique pra usar ele.";
  return (
    <button className="saida ativa" onClick={alternar} title={dica}>
      <Icone nome="volume" tamanho={16} />
      <span className="saida-nome">
        Este computador
        <small>{comFreddy ? `pelo Freddy ${TEXTO_DA_CONEXAO[conexao]}` : "pelo navegador"}</small>
      </span>
      <span className={`luz ${conexao === "conectado" ? "" : "apagada"}`} />
    </button>
  );
}

/** A linha "Discord" da barra lateral: mostra onde o bot está e abre a janela. */
function SaidaDiscord({ comFreddy }: { comFreddy: boolean }) {
  const estado = useArmazem(discord);
  const api = useArmazem(freddy);
  const [aberta, setAberta] = useState(false);
  const detalhe = !comFreddy
    ? "precisa do Freddy"
    : !estado || estado.situacao === "desligado"
      ? estado?.configurado ? "bot desligado" : "configurar"
      : estado.situacao === "conectando"
        ? "conectando…"
        : estado.situacao === "erro"
          ? "deu erro"
          : estado.canal
            ? `#${estado.canal.nome}`
            : "fora da call";
  return (
    <>
      <button className={`saida ${estado?.canal ? "ativa" : ""}`} onClick={() => setAberta(true)} title="Tocar no Discord">
        <Icone nome="discord" tamanho={16} />
        <span className="saida-nome">
          Discord
          <small>{detalhe}</small>
        </span>
        {estado?.canal && <span className="luz" />}
        {estado?.situacao === "erro" && <span className="luz apagada" />}
      </button>
      {estado?.canal && estado.podeTocar && api && (
        <label className="marcar so-na-call" title="Muta este PC: a música sai só pela call">
          <input
            type="checkbox"
            checked={!estado.ouvirAqui}
            onChange={(e) => void api.ouvirAqui(!e.target.checked).then((novo) => discord.escrever(novo)).catch(() => {})}
          />
          Só no Discord (mutar aqui)
        </label>
      )}
      {aberta && <JanelaDiscord fechar={() => setAberta(false)} />}
    </>
  );
}

/** Tocando pelo navegador e o Freddy ligou: oferece trocar (recarrega o painel). */
function AvisoFreddyLigou() {
  const ligou = useArmazem(freddyLigouDepois);
  const { tocando } = useEstadoDoMotor();
  if (!ligou) return null;
  return (
    <div className="aviso-freddy" role="status">
      <span>
        🐦 O Freddy ligou. Usar ele?{tocando ? " (a fila de agora fica pra trás)" : ""}
      </span>
      <button
        className="botao destaque"
        onClick={() => {
          preferenciaDeMotor.escrever("auto");
          location.reload();
        }}
      >
        Usar o Freddy
      </button>
      <button className="botao-texto" onClick={() => freddyLigouDepois.escrever(false)}>
        Agora não
      </button>
    </div>
  );
}
