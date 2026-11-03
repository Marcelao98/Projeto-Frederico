/**
 * A janela do Discord: colar o token do bot (uma vez), convidar pros
 * servidores, escolher o canal de voz e entrar. O fluxo é o do Kenku FM
 * (token → servidores e canais → entrar); o resto mora no backend
 * (backend/freddy/bot/).
 */

import { useEffect, useState } from "react";
import { discord, freddy, type Diagnostico, type EstadoDiscord } from "../dados/freddy";
import { useArmazem } from "../dados/useArmazem";
import { Icone } from "./Icone";

export function JanelaDiscord({ fechar }: { fechar: () => void }) {
  const api = useArmazem(freddy);
  const estado = useArmazem(discord);
  const [ocupado, setOcupado] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    const aoTeclar = (e: KeyboardEvent) => e.key === "Escape" && fechar();
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [fechar]);

  async function fazer(qual: string, acao: () => Promise<EstadoDiscord>) {
    setOcupado(qual);
    setErro(null);
    try {
      discord.escrever(await acao());
    } catch (e) {
      setErro(e instanceof Error ? e.message : String(e));
    } finally {
      setOcupado(null);
    }
  }

  return (
    <div className="janela-fundo" onClick={fechar}>
      <div className="janela" role="dialog" aria-label="Discord" onClick={(e) => e.stopPropagation()}>
        <header className="janela-topo">
          <h2>
            <Icone nome="discord" tamanho={20} /> Discord
          </h2>
          <button className="botao-icone" onClick={fechar} title="Fechar (Esc)">
            <Icone nome="x" tamanho={16} />
          </button>
        </header>

        {!api ? (
          <p>
            O Discord precisa do Freddy ligado: no app ele liga sozinho (no navegador, rode o <code>freddy.sh</code>).
            Sem ele, o som só sai neste computador.
          </p>
        ) : !estado ? (
          <p className="apagado">Perguntando pro Freddy…</p>
        ) : (
          <Conteudo estado={estado} ocupado={ocupado} fazer={fazer} />
        )}
        {(erro || estado?.erro) && <p className="janela-erro">⚠️ {erro ?? estado?.erro}</p>}
      </div>
    </div>
  );
}

function Conteudo({
  estado,
  ocupado,
  fazer,
}: {
  estado: EstadoDiscord;
  ocupado: string | null;
  fazer: (qual: string, acao: () => Promise<EstadoDiscord>) => Promise<void>;
}) {
  const api = useArmazem(freddy)!;
  const [token, setToken] = useState("");
  const [copiado, setCopiado] = useState(false);

  if (estado.situacao === "conectando" || ocupado === "token") {
    return <p className="apagado">Conectando o bot no Discord…</p>;
  }

  if (estado.situacao !== "conectado" || !estado.bot) {
    return (
      <form
        className="janela-token"
        onSubmit={(e) => {
          e.preventDefault();
          void fazer("token", () => api.guardarTokenDoDiscord(token.trim()));
        }}
      >
        {estado.configurado ? (
          <div className="janela-linha">
            <p>{estado.situacao === "erro" ? "O bot não conectou." : "O bot está desligado."}</p>
            <button className="botao destaque" type="button" onClick={() => void fazer("token", () => api.religarDiscord())}>
              Conectar de novo
            </button>
          </div>
        ) : (
          <ol className="guia">
            <li>
              Abre o <strong>Discord Developer Portal</strong> (discord.com/developers/applications) e clica em{" "}
              <strong>New Application</strong>. Nome: <em>Freddy</em>.
            </li>
            <li>
              Na aba <strong>Bot</strong>, clica em <strong>Reset Token</strong> e copia o token.
            </li>
            <li>Cola aqui embaixo. Ele fica guardado só neste computador, na pasta do Freddy.</li>
          </ol>
        )}
        {estado.doAmbiente ? (
          <p className="apagado">O token vem da variável FREDDY_DISCORD_TOKEN (troque lá, se precisar).</p>
        ) : (
          <div className="janela-linha">
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder={estado.configurado ? "Ou cola um token novo" : "Token do bot"}
              aria-label="Token do bot"
              autoComplete="off"
            />
            <button className="botao destaque" type="submit" disabled={token.trim().length < 20}>
              Conectar
            </button>
          </div>
        )}
      </form>
    );
  }

  const copiarConvite = async () => {
    if (!estado.convite) return;
    try {
      await navigator.clipboard.writeText(estado.convite);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      window.prompt("Copia o link do convite:", estado.convite);
    }
  };

  return (
    <div className="janela-corpo">
      <div className="bot-linha">
        <img src={estado.bot.avatar} alt="" className="bot-avatar" />
        <div>
          <strong>{estado.bot.nome}</strong>
          <div className="apagado">conectado</div>
        </div>
        {estado.convite && (
          <div className="grupo-botoes">
            <a className="botao" href={estado.convite} target="_blank" rel="noreferrer">
              Convidar pra um servidor
            </a>
            <button className="botao" onClick={() => void copiarConvite()} title="Copiar o link do convite">
              {copiado ? "Copiado ✓" : "Copiar link"}
            </button>
          </div>
        )}
      </div>

      {!estado.podeTocar && (
        <p className="janela-erro">O Freddy está em modo --sem-som: dá pra conectar, mas não tem som pra mandar pra call.</p>
      )}

      {estado.canal && (
        <div className="na-call">
          <span className="luz" />
          <span>
            Tocando em <strong>#{estado.canal.nome}</strong> ({estado.canal.servidor})
          </span>
          <button className="botao" disabled={ocupado !== null} onClick={() => void fazer("sair", () => api.sairDaCall())}>
            Sair da call
          </button>
        </div>
      )}

      <label className="marcar">
        <input
          type="checkbox"
          checked={estado.ouvirAqui}
          onChange={(e) => void fazer("ouvir", () => api.ouvirAqui(e.target.checked))}
        />
        Ouvir aqui também (o som da call sai na caixa deste computador)
      </label>

      {estado.canal && estado.podeTocar && <Teste ocupado={ocupado} fazer={fazer} />}

      {estado.servidores.length === 0 ? (
        <p className="apagado">O bot ainda não está em nenhum servidor. Usa o convite aí em cima.</p>
      ) : (
        <div className="servidores">
          {estado.servidores.map((s) => (
            <section key={s.id} className="servidor">
              <h3>
                {s.icone ? <img src={s.icone} alt="" /> : <span className="servidor-letra">{s.nome[0]}</span>}
                {s.nome}
              </h3>
              {s.canais.length === 0 && <p className="apagado">Sem canal de voz.</p>}
              {s.canais.map((c) => {
                const aqui = estado.canal?.id === c.id;
                return (
                  <button
                    key={c.id}
                    className={`canal ${aqui ? "ativo" : ""}`}
                    disabled={aqui || ocupado !== null || !estado.podeTocar}
                    onClick={() => void fazer(`canal-${c.id}`, () => api.entrarNaCall(c.id))}
                    title={aqui ? "Tocando aqui" : `Entrar em ${c.nome}`}
                  >
                    <Icone nome="volume" tamanho={14} />
                    <span className="canal-nome">{c.nome}</span>
                    {c.pessoas > 0 && <span className="contagem">{c.pessoas} 👤</span>}
                    {ocupado === `canal-${c.id}` ? <span className="apagado">entrando…</span> : aqui ? <span className="selo">aqui</span> : null}
                  </button>
                );
              })}
            </section>
          ))}
        </div>
      )}

      {!estado.doAmbiente && (
        <button
          className="botao-texto desconectar"
          disabled={ocupado !== null}
          onClick={() => {
            if (window.confirm("Desconectar o bot e esquecer o token? Pra voltar, tem que colar o token de novo.")) {
              void fazer("esquecer", () => api.esquecerTokenDoDiscord());
            }
          }}
        >
          Desconectar e esquecer o token
        </button>
      )}
    </div>
  );
}

/**
 * Testar a call e o modo debug: o assobio do Frederico (só pelo Discord) e,
 * aberto, os números do que está saindo (2x por segundo, só enquanto aberto).
 */
function Teste({
  ocupado,
  fazer,
}: {
  ocupado: string | null;
  fazer: (qual: string, acao: () => Promise<EstadoDiscord>) => Promise<void>;
}) {
  const api = useArmazem(freddy)!;
  const [aberto, setAberto] = useState(false);
  const [diag, setDiag] = useState<Diagnostico | null>(null);

  useEffect(() => {
    if (!aberto) return;
    let vivo = true;
    const pedir = () =>
      api
        .diagnostico()
        .then((d) => vivo && setDiag(d))
        .catch(() => vivo && setDiag(null));
    void pedir();
    const t = window.setInterval(pedir, 500);
    return () => {
      vivo = false;
      window.clearInterval(t);
    };
  }, [aberto, api]);

  const t = diag?.transmissao;
  const m = diag?.mesa;
  const puxando = t ? t.quadrosPorSegundo >= 40 : false;

  return (
    <div className="teste-call">
      <div className="teste-linha">
        <button className="botao" disabled={ocupado !== null} onClick={() => void fazer("assobio", () => api.assobiar())}>
          🐦 {ocupado === "assobio" ? "Assobiando…" : "Testar: o Frederico assobia na call"}
        </button>
        <span className="apagado">O PC fica mudo: se você ouviu o assobio, veio pelo Discord.</span>
      </div>

      <details className="diagnostico" onToggle={(e) => setAberto((e.target as HTMLDetailsElement).open)}>
        <summary>Diagnóstico (modo debug)</summary>
        {!diag ? (
          <p className="apagado">Perguntando pro Freddy…</p>
        ) : (
          <dl>
            <dt>Indo pra call</dt>
            <dd>
              <Nivel valor={t?.nivel ?? 0} />
              {t
                ? `${t.quadrosPorSegundo}/50 quadros por segundo, ${t.comSomPorSegundo} com som`
                : "fora da call"}
              {t && !puxando && <strong className="aviso"> · o Discord não está puxando o som</strong>}
            </dd>
            <dt>Saindo neste PC</dt>
            <dd>
              <Nivel valor={m?.mudoLocal ? 0 : (m?.nivelLocal ?? 0)} />
              {m?.mudoLocal ? "mudo (só na call)" : "ligado"}
            </dd>
            <dt>Música</dt>
            <dd>
              {m?.musica ?? "—"}
              {m?.musica === "engasgou" && <strong className="aviso"> · esperando o YouTube mandar mais</strong>}
              {m && m.musica !== "sem música" && m.musica !== "assobiando" && ` · ${m.bufferSegundos.toFixed(1)} s guardados`}
              {diag.motor.titulo && <div className="apagado">{diag.motor.titulo}</div>}
            </dd>
            <dt>Player do Discord</dt>
            <dd>{t ? (t.tocando ? "rodando" : "parado") : "—"}{t && ` · ${t.quadros} quadros desde que entrou`}</dd>
          </dl>
        )}
      </details>
    </div>
  );
}

/** Barrinha de volume: 0 a 32767 em escala de ouvido (dB), pra mexer com a música. */
function Nivel({ valor }: { valor: number }) {
  const db = valor > 0 ? 20 * Math.log10(valor / 32767) : -60;
  const pct = Math.max(0, Math.min(100, ((db + 60) / 60) * 100));
  return (
    <span className="nivel" aria-hidden="true">
      <span style={{ width: `${pct}%` }} />
    </span>
  );
}
