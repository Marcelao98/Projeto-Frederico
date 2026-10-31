/**
 * Modo Chat: fala com o Freddy como fala com a Natty no Discord.
 * "toca triste e bloodborne", "pula", "volume 30". Sem LLM.
 */

import { useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Calopsita } from "../../componentes/Calopsita";
import { CartaoMusica } from "../../componentes/CartaoMusica";
import { Icone } from "../../componentes/Icone";
import { TextoRico } from "../../componentes/TextoRico";
import { acervoAtual, emojiCategoria, recarregarAcervo, rotuloCategoria, sugestoesDeBusca, type Acervo } from "../../dados/acervo";
import { freddy, type ApiFreddy } from "../../dados/freddy";
import { tituloDoLink } from "../../dados/tituloDoLink";
import { useArmazem } from "../../dados/useArmazem";
import { useMotor } from "../../motor/contexto";
import type { Musica } from "../../nucleo/tipos";
import { previa, responder, responderEraEssa, separarTemas, termoEmDigitacao, type Contexto, type Previa } from "./conversa";
import { semNarrar } from "./narrador";
import { esquecerRevisao, responderRevisao, type Revisao } from "./revisao";
import { fecharPergunta, historico, limparHistorico, pedidosAnteriores, registrar, type MensagemChat } from "./historico";

const EXEMPLOS = [
  "toca calmo e hollow knight",
  "toca chefe sem elden ring",
  "toca taverna",
  "toca triste ou nostálgico e fire emblem",
];
const ATALHOS = ["pula", "pausa", "continua", "repete", "fila", "abaixa", "aumenta"];
const MUSICAS_NO_CARTAO = 4;

const NOME_DA_ACAO: Record<string, string> = {
  pular: "pular a música",
  fila: "mostrar a fila",
  limpar_fila: "limpar a fila",
  pausar: "pausar",
  continuar: "continuar",
  parar: "parar e limpar a fila",
  repetir: "repetir (liga/desliga)",
  volume: "mexer no volume",
  tocar: "pedir o que tocar",
};

/** Grava temas no Freddy e já traz o acervo novo (busca e Playlist enxergam na hora). */
function editarTemasCom(api: ApiFreddy | null): Contexto["editarTemas"] {
  if (!api) return undefined;
  return async (faixaId, temas) => {
    const faixa = await api.editarFaixa(faixaId, { temas });
    await recarregarAcervo(api);
    return faixa;
  };
}

/** O título de um link: o oEmbed do YouTube (rápido); se falhar, o Freddy pergunta pro yt-dlp. */
function tituloComFreddy(api: ApiFreddy | null) {
  return async (link: string) => (await tituloDoLink(link)) ?? (api ? await api.tituloDoLink(link) : null);
}

export function ModoChat({ acervo }: { acervo: Acervo }) {
  const motor = useMotor();
  const api = useArmazem(freddy);
  const mensagens = useArmazem(historico);
  const [texto, setTexto] = useState("");
  const [pensando, setPensando] = useState(false);
  const [indiceHistorico, setIndiceHistorico] = useState(-1);
  const rolagem = useRef<HTMLDivElement>(null);
  const campo = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Sem mensagens é a tela de boas-vindas: fica no topo.
    if (!mensagens.length) return;
    rolagem.current?.scrollTo({ top: rolagem.current.scrollHeight, behavior: "smooth" });
  }, [mensagens.length, pensando]);

  useEffect(() => campo.current?.focus(), []);

  const emDigitacao = useMemo(() => termoEmDigitacao(texto), [texto]);
  const sugestoes = useMemo(
    () => (emDigitacao ? sugestoesDeBusca(acervo, emDigitacao.termo) : []),
    [acervo, emDigitacao],
  );
  const oQueVaiAcontecer = useMemo(() => (texto.trim() ? previa(texto, acervo) : null), [texto, acervo]);

  async function enviar(pedido: string) {
    const limpo = pedido.trim();
    if (!limpo || pensando) return;
    registrar("voce", { texto: limpo });
    setTexto("");
    setIndiceHistorico(-1);
    setPensando(true);
    try {
      registrar(
        "freddy",
        await semNarrar(() => responder(limpo, {
          motor,
          acervo,
          tituloDoLink: tituloComFreddy(api),
          buscarNoYoutube: api ? (t) => api.buscarNoYoutube(t) : undefined,
          editarTemas: editarTemasCom(api),
        })),
      );
    } catch (e) {
      registrar("freddy", { texto: `Deu ruim aqui 😕 (${e instanceof Error ? e.message : String(e)})` });
    } finally {
      setPensando(false);
      campo.current?.focus();
    }
  }

  function completar(sugestao: string) {
    if (!emDigitacao) return;
    setTexto(texto.slice(0, emDigitacao.inicio) + sugestao + " ");
    campo.current?.focus();
  }

  function aoTeclar(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Tab" && sugestoes.length) {
      e.preventDefault();
      completar(sugestoes[0]);
    } else if (e.key === "ArrowUp" || e.key === "ArrowDown") {
      const anteriores = pedidosAnteriores();
      if (!anteriores.length) return;
      e.preventDefault();
      const i =
        e.key === "ArrowUp"
          ? Math.min(indiceHistorico + 1, anteriores.length - 1)
          : Math.max(indiceHistorico - 1, -1);
      setIndiceHistorico(i);
      setTexto(i < 0 ? "" : anteriores[i]);
    } else if (e.key === "Escape") {
      setTexto("");
    }
  }

  return (
    <section className="modo modo-chat">
      <header className="modo-topo">
        <div>
          <h1>Chat</h1>
          <p>Pede do jeito que você pede pra Natty. Sem @, sem comando decorado.</p>
        </div>
        {mensagens.length > 0 && (
          <button
            className="botao-texto"
            onClick={() => {
              esquecerRevisao();
              limparHistorico();
            }}
          >
            Limpar conversa
          </button>
        )}
      </header>

      <div className="chat-rolagem" ref={rolagem} aria-live="polite">
        {mensagens.length === 0 ? (
          <BoasVindas acervo={acervo} enviar={enviar} />
        ) : (
          <ol className="chat-mensagens">
            {mensagens.map((m) => (
              <Mensagem key={m.id} mensagem={m} />
            ))}
            {pensando && (
              <li className="mensagem freddy">
                <div className="avatar">
                  <Calopsita tamanho={30} />
                </div>
                <div className="balao digitando" aria-label="Freddy está respondendo">
                  <span />
                  <span />
                  <span />
                </div>
              </li>
            )}
          </ol>
        )}
      </div>

      <form
        className="chat-entrada"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          void enviar(texto);
        }}
      >
        {sugestoes.length > 0 && (
          <div className="sugestoes" role="listbox" aria-label="Completar busca">
            {sugestoes.map((s, i) => (
              <button type="button" key={s} className="chip" onClick={() => completar(s)} role="option">
                {s}
                {i === 0 && <kbd>Tab</kbd>}
              </button>
            ))}
          </div>
        )}
        <div className="campo-chat">
          <input
            ref={campo}
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            onKeyDown={aoTeclar}
            placeholder='Ex.: "toca triste e bloodborne", "pula", "volume 30"'
            aria-label="Mensagem pro Freddy"
            autoComplete="off"
            spellCheck={false}
          />
          <button className="botao-enviar" type="submit" disabled={!texto.trim() || pensando} title="Enviar (Enter)">
            <Icone nome="enviar" />
          </button>
        </div>
        <div className="chat-rodape">
          <LinhaDePrevia previa={oQueVaiAcontecer} vazio={!texto.trim()} />
          <div className="atalhos">
            {ATALHOS.map((a) => (
              <button type="button" key={a} className="chip pequeno" onClick={() => void enviar(a)}>
                {a}
              </button>
            ))}
          </div>
        </div>
      </form>
    </section>
  );
}

function LinhaDePrevia({ previa, vazio }: { previa: Previa | null; vazio: boolean }) {
  if (vazio) return <span className="previa apagado">↑ ↓ repete pedidos · Tab completa</span>;
  if (!previa) return <span className="previa apagado">…não parece um pedido de música ainda</span>;
  switch (previa.tipo) {
    case "busca":
      return previa.total ? (
        <span className="previa ok">
          <Icone nome="busca" tamanho={14} /> {previa.total} faixa{previa.total > 1 ? "s" : ""} no acervo
          {previa.total > 15 && " (sorteio 15)"}
        </span>
      ) : (
        <span className="previa aviso">nada no acervo com isso</span>
      );
    case "link":
      return <span className="previa ok">link do YouTube: toco ou ponho na fila</span>;
    case "ajuda":
      return <span className="previa ok">mostrar tudo que eu entendo</span>;
    case "comando":
      return <span className="previa ok">↵ {NOME_DA_ACAO[previa.acao] ?? previa.acao}</span>;
    case "acervo":
      return <span className="previa ok">↵ {previa.descricao}</span>;
  }
}

function BoasVindas({ acervo, enviar }: { acervo: Acervo; enviar: (t: string) => void }) {
  const categorias = acervo.categorias.filter((c) => c.quantas > 0).slice(0, 14);
  return (
    <div className="boas-vindas">
      <Calopsita tamanho={150} />
      <h2>Oi, eu sou o Freddy</h2>
      <p>
        Cuido do som da mesa. Tenho <strong>{acervo.faixas.length} faixas</strong> de{" "}
        {acervo.origens.length} franquias, marcadas por clima. Me diz o que a cena pede.
      </p>
      <div className="exemplos">
        {EXEMPLOS.map((e) => (
          <button key={e} className="exemplo" onClick={() => enviar(e)}>
            <span>“{e}”</span>
            <Icone nome="enviar" tamanho={14} />
          </button>
        ))}
      </div>
      <div className="categorias-rapidas">
        {categorias.map((c) => (
          <button key={c.nome} className="chip" onClick={() => enviar(`toca ${rotuloCategoria(c.nome)}`)}>
            <span aria-hidden="true">{emojiCategoria(c.nome)}</span> {rotuloCategoria(c.nome)}
            <span className="contagem">{c.quantas}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function Mensagem({ mensagem }: { mensagem: MensagemChat }) {
  const motor = useMotor();
  const hora = new Date(mensagem.quando).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  const musicas = mensagem.musicas ?? [];
  const tocarAgora = (m: Musica) => void motor.executar({ tipo: "adicionar", musicas: [m], onde: "agora" });

  if (mensagem.discreta) {
    return (
      <li className="mensagem aviso-discreto">
        <TextoRico texto={mensagem.texto} />
        <time>{hora}</time>
      </li>
    );
  }

  return (
    <li className={`mensagem ${mensagem.autor}`}>
      {mensagem.autor === "freddy" && (
        <div className="avatar">
          <Calopsita tamanho={30} />
        </div>
      )}
      <div className="balao">
        <div className="balao-texto">
          <TextoRico texto={mensagem.texto} />
        </div>
        {mensagem.pergunta && <EraEssa mensagem={mensagem} musica={mensagem.pergunta} />}
        {mensagem.revisao && <TaCerto revisao={mensagem.revisao} />}
        {musicas.length > 0 && (
          <div className="balao-musicas">
            {musicas.slice(0, MUSICAS_NO_CARTAO).map((m, i) => (
              <CartaoMusica
                key={`${m.link}-${i}`}
                musica={m}
                compacto
                acoes={
                  <button className="botao-icone pequeno" onClick={() => tocarAgora(m)} title="Tocar agora">
                    <Icone nome="tocar" tamanho={14} />
                  </button>
                }
              />
            ))}
            {musicas.length > MUSICAS_NO_CARTAO && (
              <div className="mais-musicas">+ {musicas.length - MUSICAS_NO_CARTAO} na fila</div>
            )}
          </div>
        )}
        <time className="balao-hora">{hora}</time>
      </div>
    </li>
  );
}

/** Os botões do "era essa?": guarda a faixa no acervo com os climas, ou pula. */
function EraEssa({ mensagem, musica }: { mensagem: MensagemChat; musica: Musica }) {
  const motor = useMotor();
  const api = useArmazem(freddy);
  const [climas, setClimas] = useState("");
  const [ocupado, setOcupado] = useState(false);
  if (!api) return null;

  async function responder(temas: string[] | null) {
    if (!api || ocupado) return;
    setOcupado(true);
    try {
      registrar("voce", { texto: temas === null ? "não era essa" : `era essa${temas.length ? `: ${temas.join(", ")}` : ""}` });
      registrar("freddy", await semNarrar(() => responderEraEssa(musica, temas, { motor, professor: api })));
      fecharPergunta(mensagem.id);
      if (temas !== null) await recarregarAcervo(api);
    } catch (e) {
      registrar("freddy", { texto: `Deu ruim aqui 😕 (${e instanceof Error ? e.message : String(e)})` });
    } finally {
      setOcupado(false);
    }
  }

  return (
    <form
      className="era-essa"
      onSubmit={(e) => {
        e.preventDefault();
        void responder(separarTemas(climas));
      }}
    >
      <input
        value={climas}
        onChange={(e) => setClimas(e.target.value)}
        placeholder="climas: taverna, alegre…"
        aria-label="Climas da música"
        disabled={ocupado}
      />
      <button type="submit" className="chip" disabled={ocupado}>
        É essa, guarda
      </button>
      <button type="button" className="chip" disabled={ocupado} onClick={() => void responder(null)}>
        Não é
      </button>
    </form>
  );
}

/** Os botões do "tá certo?": confirma, corrige os temas ali mesmo, ou para a revisão. */
function TaCerto({ revisao }: { revisao: Revisao }) {
  const motor = useMotor();
  const api = useArmazem(freddy);
  const acervo = useArmazem(acervoAtual);
  const semTema = revisao.temas.length === 0 || revisao.temas.includes("não classificado");
  const [corrigindo, setCorrigindo] = useState(semTema);
  const [temas, setTemas] = useState(semTema ? "" : revisao.temas.join(", "));
  const [ocupado, setOcupado] = useState(false);

  async function responder(resposta: Parameters<typeof responderRevisao>[0], fala: string) {
    if (ocupado) return;
    setOcupado(true);
    try {
      registrar("voce", { texto: fala });
      registrar("freddy", await responderRevisao(resposta, { motor, acervo, editarTemas: editarTemasCom(api) }));
    } catch (e) {
      registrar("freddy", { texto: `Não consegui salvar (${e instanceof Error ? e.message : String(e)}) 😕` });
    } finally {
      setOcupado(false);
    }
  }

  const salvar = () => {
    const lista = separarTemas(temas);
    void responder({ temas: lista }, `temas: ${lista.join(", ")}`);
  };

  return (
    <div className="era-essa">
      {corrigindo ? (
        <form
          className="era-essa"
          onSubmit={(e) => {
            e.preventDefault();
            salvar();
          }}
        >
          <input
            autoFocus
            value={temas}
            onChange={(e) => setTemas(e.target.value)}
            placeholder="temas: taverna, alegre…"
            aria-label="Temas da música"
            disabled={ocupado}
          />
          <button type="submit" className="chip" disabled={ocupado || !temas.trim()}>
            Salvar
          </button>
        </form>
      ) : (
        <>
          <button className="chip" disabled={ocupado} onClick={() => void responder("certo", "tá certo")}>
            👍 Tá certo
          </button>
          <button className="chip" disabled={ocupado} onClick={() => setCorrigindo(true)}>
            ✏️ Corrigir
          </button>
        </>
      )}
      {revisao.emSessao && (
        <button className="chip" disabled={ocupado} onClick={() => void responder("parar", "para de revisar")}>
          Parar revisão
        </button>
      )}
    </div>
  );
}
