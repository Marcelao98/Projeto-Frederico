/**
 * Modo Acervo: arrumar as faixas como numa planilha. Muda o nome e os temas
 * ali mesmo (salva ao sair do campo ou no Enter), ou baixa o CSV, edita no
 * LibreOffice/Excel e manda de volta (com resumo antes de aplicar).
 *
 * Gravar precisa do Freddy: as mudanças vão pro ajustes.json do mestre (ver
 * backend/freddy/dados/acervo.py). Sem ele, dá pra ver, não pra salvar.
 */

import { useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
import { Icone } from "../../componentes/Icone";
import { recarregarAcervo, rotuloCategoria, type Acervo } from "../../dados/acervo";
import { freddy, type ApiFreddy, type ResumoDaPlanilha } from "../../dados/freddy";
import { useArmazem } from "../../dados/useArmazem";
import { useMotor } from "../../motor/contexto";
import { normalizar } from "../../nucleo/texto";
import { musicaDaFaixa, type Faixa } from "../../nucleo/tipos";
import { separarTemas } from "../chat/revisao";

const PAGINA = 100;
const SEM_TEMA = "não classificado";

const semTema = (f: Faixa) => f.temas.length === 0 || f.temas.includes(SEM_TEMA);

export function ModoAcervo({ acervo }: { acervo: Acervo }) {
  const api = useArmazem(freddy);
  const [busca, setBusca] = useState("");
  const [origem, setOrigem] = useState("");
  const [soSemTema, setSoSemTema] = useState(false);
  const [limite, setLimite] = useState(PAGINA);
  const [aviso, setAviso] = useState<string | null>(null);
  const prazo = useRef<ReturnType<typeof setTimeout>>();

  const avisar = (texto: string) => {
    setAviso(texto);
    clearTimeout(prazo.current);
    prazo.current = setTimeout(() => setAviso(null), 4000);
  };
  useEffect(() => () => clearTimeout(prazo.current), []);

  const faixas = useMemo(() => {
    const termo = normalizar(busca);
    return acervo.faixas.filter(
      (f) =>
        (!origem || f.origem.nome === origem) &&
        (!soSemTema || semTema(f)) &&
        (!termo || normalizar(`${f.nome} ${f.origem.nome} ${f.temas.join(" ")}`).includes(termo)),
    );
  }, [acervo, busca, origem, soSemTema]);
  const quantasSemTema = useMemo(() => acervo.faixas.filter(semTema).length, [acervo]);

  return (
    <section className="modo modo-acervo">
      <header className="modo-topo">
        <div>
          <h1>Acervo</h1>
          <p>Arruma o nome e os temas das faixas. A busca usa as categorias, que saem dos temas sozinhas.</p>
        </div>
        <Planilha api={api} avisar={avisar} />
      </header>

      {!api && (
        <div className="faixa-aviso">
          Pra salvar, ligue o Freddy (<code>python -m freddy</code>). Sem ele dá pra ver o acervo, mas não mudar.
        </div>
      )}

      <div className="acervo-filtros">
        <div className="campo-busca">
          <Icone nome="busca" tamanho={16} />
          <input
            value={busca}
            onChange={(e) => {
              setBusca(e.target.value);
              setLimite(PAGINA);
            }}
            placeholder="Filtra por nome, franquia ou tema"
            aria-label="Filtrar o acervo"
            spellCheck={false}
          />
        </div>
        <select value={origem} onChange={(e) => setOrigem(e.target.value)} aria-label="Franquia">
          <option value="">Todas as franquias</option>
          {acervo.origens.map((o) => (
            <option key={o.nome} value={o.nome}>
              {o.nome} ({o.quantas})
            </option>
          ))}
        </select>
        <label className="marcar">
          <input type="checkbox" checked={soSemTema} onChange={(e) => setSoSemTema(e.target.checked)} />
          Só sem tema ({quantasSemTema})
        </label>
        <span className="contagem-grande">
          {faixas.length} de {acervo.faixas.length}
        </span>
      </div>

      <div className="tabela-rolagem">
        <table className="tabela-acervo">
          <thead>
            <tr>
              <th aria-label="Tocar" />
              <th>Nome</th>
              <th>Franquia</th>
              <th>Temas</th>
              <th>Na busca</th>
              <th aria-label="Situação" />
            </tr>
          </thead>
          <tbody>
            {faixas.slice(0, limite).map((f) => (
              <LinhaDaFaixa key={f.id} faixa={f} api={api} />
            ))}
          </tbody>
        </table>
        {faixas.length > limite && (
          <button className="botao mostrar-mais" onClick={() => setLimite(limite + PAGINA)}>
            Mostrar mais ({faixas.length - limite})
          </button>
        )}
        {!faixas.length && <p className="vazio">Nada com esse filtro.</p>}
      </div>

      <div className={`aviso-flutuante ${aviso ? "visivel" : ""}`} role="status">
        {aviso}
      </div>
    </section>
  );
}

type Situacao = "" | "salvando" | "salvo" | "erro";

function LinhaDaFaixa({ faixa, api }: { faixa: Faixa; api: ApiFreddy | null }) {
  const motor = useMotor();
  const [nome, setNome] = useState(faixa.nome);
  const [temas, setTemas] = useState(faixa.temas.join(", "));
  const [situacao, setSituacao] = useState<Situacao>("");
  const [erro, setErro] = useState("");

  // O acervo recarregou (outra edição, planilha): mostra o valor novo.
  useEffect(() => setNome(faixa.nome), [faixa.nome]);
  useEffect(() => setTemas(faixa.temas.join(", ")), [faixa.temas]);

  async function salvar() {
    if (!api) return;
    const novosTemas = separarTemas(temas);
    const mudouNome = nome.trim() && nome.trim() !== faixa.nome;
    const mudouTemas = novosTemas.join(",") !== faixa.temas.join(",") && !(novosTemas.length === 0 && semTema(faixa));
    if (!mudouNome && !mudouTemas) {
      setTemas(faixa.temas.join(", ")); // arruma espaços e vírgulas
      return;
    }
    setSituacao("salvando");
    try {
      await api.editarFaixa(faixa.id, {
        ...(mudouNome ? { nome: nome.trim() } : {}),
        ...(mudouTemas ? { temas: novosTemas } : {}),
      });
      await recarregarAcervo(api);
      setSituacao("salvo");
      setTimeout(() => setSituacao((s) => (s === "salvo" ? "" : s)), 2000);
    } catch (e) {
      setSituacao("erro");
      setErro(e instanceof Error ? e.message : String(e));
    }
  }

  const aoTeclar = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") e.currentTarget.blur();
    if (e.key === "Escape") {
      setNome(faixa.nome);
      setTemas(faixa.temas.join(", "));
      e.currentTarget.blur();
    }
  };

  return (
    <tr className={semTema(faixa) ? "sem-tema" : ""}>
      <td>
        <button
          className="botao-icone pequeno"
          title="Tocar agora (pra ouvir antes de marcar)"
          onClick={() => void motor.executar({ tipo: "adicionar", musicas: [musicaDaFaixa(faixa)], onde: "agora" })}
        >
          <Icone nome="tocar" tamanho={14} />
        </button>
      </td>
      <td>
        <input
          className="celula"
          value={nome}
          onChange={(e) => setNome(e.target.value)}
          onBlur={() => void salvar()}
          onKeyDown={aoTeclar}
          disabled={!api}
          aria-label={`Nome de ${faixa.nome}`}
        />
      </td>
      <td className="celula-franquia">{faixa.origem.nome}</td>
      <td>
        <input
          className="celula"
          value={temas}
          onChange={(e) => setTemas(e.target.value)}
          onBlur={() => void salvar()}
          onKeyDown={aoTeclar}
          disabled={!api}
          placeholder="taverna, alegre…"
          aria-label={`Temas de ${faixa.nome}`}
        />
      </td>
      <td className="celula-categorias">
        {(faixa.categorias ?? []).map((c) => (
          <span key={c} className="selo">
            {rotuloCategoria(c)}
          </span>
        ))}
      </td>
      <td className={`celula-situacao ${situacao}`} title={situacao === "erro" ? erro : undefined}>
        {situacao === "salvando" ? "…" : situacao === "salvo" ? "✓" : situacao === "erro" ? "!" : ""}
      </td>
    </tr>
  );
}

/** Baixar o CSV (vai pra pasta Downloads) e mandar de volta, com resumo antes de aplicar. */
function Planilha({ api, avisar }: { api: ApiFreddy | null; avisar: (t: string) => void }) {
  const arquivo = useRef<HTMLInputElement>(null);
  const [enviada, setEnviada] = useState<{ texto: string; resumo: ResumoDaPlanilha } | null>(null);
  const [ocupado, setOcupado] = useState(false);

  async function baixar() {
    if (!api) return;
    try {
      const { caminho } = await api.salvarPlanilha();
      avisar(`Planilha salva em ${caminho}`);
    } catch (e) {
      avisar(`Não consegui salvar a planilha (${e instanceof Error ? e.message : e})`);
    }
  }

  async function escolher(e: ChangeEvent<HTMLInputElement>) {
    const escolhido = e.target.files?.[0];
    e.target.value = "";
    if (!api || !escolhido) return;
    setOcupado(true);
    try {
      const texto = await escolhido.text();
      setEnviada({ texto, resumo: await api.enviarPlanilha(texto, false) });
    } catch (erro) {
      avisar(`Não consegui ler a planilha: ${erro instanceof Error ? erro.message : erro}`);
    } finally {
      setOcupado(false);
    }
  }

  async function aplicar() {
    if (!api || !enviada) return;
    setOcupado(true);
    try {
      const r = await api.enviarPlanilha(enviada.texto, true);
      await recarregarAcervo(api);
      avisar(
        `Pronto: ${r.mudaram} ${r.mudaram === 1 ? "faixa mudou" : "faixas mudaram"}, ${r.novas} nova${r.novas === 1 ? "" : "s"} 🪶`,
      );
      setEnviada(null);
    } catch (erro) {
      avisar(`Não consegui aplicar: ${erro instanceof Error ? erro.message : erro}`);
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="acoes-planilha">
      <button className="botao" onClick={() => void baixar()} disabled={!api} title="Salva o acervo em CSV na sua pasta Downloads">
        <Icone nome="planilha" tamanho={16} /> Baixar planilha
      </button>
      <button className="botao" onClick={() => arquivo.current?.click()} disabled={!api || ocupado} title="Manda o CSV editado de volta">
        <Icone nome="enviar" tamanho={16} /> Enviar planilha
      </button>
      <input ref={arquivo} type="file" accept=".csv,text/csv" hidden onChange={(e) => void escolher(e)} />

      {enviada && (
        <div className="resumo-planilha" role="dialog" aria-label="O que a planilha muda">
          <h2>O que essa planilha muda</h2>
          <p>
            <strong>{enviada.resumo.mudaram}</strong> {enviada.resumo.mudaram === 1 ? "faixa muda" : "faixas mudam"} ·{" "}
            <strong>{enviada.resumo.novas}</strong> nova{enviada.resumo.novas === 1 ? "" : "s"} ·{" "}
            <strong>{enviada.resumo.totalIgnoradas}</strong> linha{enviada.resumo.totalIgnoradas === 1 ? "" : "s"} ignorada
            {enviada.resumo.totalIgnoradas === 1 ? "" : "s"}
          </p>
          {enviada.resumo.exemplos.length > 0 && (
            <ul className="lista-resumo">
              {enviada.resumo.exemplos.map((x) => (
                <li key={x.id}>
                  <strong>{x.nome}</strong>: {x.antes.join(", ")} → {x.depois.join(", ")}
                </li>
              ))}
              {enviada.resumo.mudaram > enviada.resumo.exemplos.length && (
                <li>… e mais {enviada.resumo.mudaram - enviada.resumo.exemplos.length}</li>
              )}
            </ul>
          )}
          {enviada.resumo.ignoradas.length > 0 && (
            <ul className="lista-resumo ignoradas">
              {enviada.resumo.ignoradas.map((i) => (
                <li key={i.linha}>
                  Linha {i.linha}: {i.motivo}
                </li>
              ))}
            </ul>
          )}
          <div className="resumo-botoes">
            <button className="botao" onClick={() => setEnviada(null)} disabled={ocupado}>
              Cancelar
            </button>
            <button
              className="botao destaque"
              onClick={() => void aplicar()}
              disabled={ocupado || (!enviada.resumo.mudaram && !enviada.resumo.novas)}
            >
              Aplicar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
