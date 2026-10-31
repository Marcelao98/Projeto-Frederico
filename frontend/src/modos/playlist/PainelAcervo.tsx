/** O acervo pra montar a playlist: busca, filtro por franquia e por clima. */

import { useMemo, useState, type ReactNode } from "react";
import { BotaoPlaylist } from "./BotaoPlaylist";
import { CartaoMusica } from "../../componentes/CartaoMusica";
import { Icone } from "../../componentes/Icone";
import { emojiCategoria, rotuloCategoria, type Acervo } from "../../dados/acervo";
import { useEstadoDoMotor, useMotor } from "../../motor/contexto";
import type { Onde } from "../../motor/tipos";
import { MAX_RESULTADOS_DA_BUSCA, sortear } from "../../nucleo/busca";
import { musicaDaFaixa, type Faixa, type Musica } from "../../nucleo/tipos";
import { extrairLinkYoutube } from "../../nucleo/youtube";

const PAGINA = 80;

export function PainelAcervo({
  acervo,
  avisar,
  editando,
  editar,
}: {
  acervo: Acervo;
  avisar: (texto: string) => void;
  editando: string | null;
  editar: (id: string) => void;
}) {
  const motor = useMotor();
  const { tocando } = useEstadoDoMotor();
  const [busca, setBusca] = useState("");
  const [origem, setOrigem] = useState<string | null>(null);
  const [categorias, setCategorias] = useState<Set<string>>(new Set());
  const [limite, setLimite] = useState(PAGINA);

  const link = extrairLinkYoutube(busca);
  const resultado = useMemo(() => {
    let faixas = busca.trim() && !link ? acervo.buscar(busca) : acervo.faixas;
    if (origem) faixas = faixas.filter((f) => f.origem.nome === origem);
    if (categorias.size) faixas = faixas.filter((f) => [...categorias].every((c) => f.categorias?.includes(c)));
    return faixas;
  }, [acervo, busca, link, origem, categorias]);

  const filtrando = Boolean(busca.trim() || origem || categorias.size);

  async function por(musicas: Musica[], onde: Onde) {
    const r = await motor.executar({ tipo: "adicionar", musicas, onde });
    if (!r.entraram) avisar("A fila está cheia (50). Tira alguma ou limpa a fila.");
    else if (r.entraram < musicas.length) avisar(`Entraram ${r.entraram} de ${musicas.length}: a fila encheu.`);
    else if (musicas.length > 1) avisar(`${r.entraram} músicas na fila 📜`);
    else if (onde === "proxima") avisar(`${musicas[0].titulo} toca a seguir`);
    else if (!r.comecou) avisar(`${musicas[0].titulo} na fila (posição ${r.posicao})`);
  }

  function alternarCategoria(c: string) {
    setLimite(PAGINA);
    setCategorias((atual) => {
      const nova = new Set(atual);
      if (nova.has(c)) nova.delete(c);
      else nova.add(c);
      return nova;
    });
  }

  function limparFiltros() {
    setBusca("");
    setOrigem(null);
    setCategorias(new Set());
    setLimite(PAGINA);
  }

  return (
    <section className="painel painel-acervo" aria-label="Acervo">
      <header className="painel-topo">
        <h2>Acervo</h2>
        <span className="contagem-grande">
          {resultado.length} de {acervo.faixas.length}
        </span>
      </header>

      <div className="campo-busca">
        <Icone nome="busca" tamanho={16} />
        <input
          value={busca}
          onChange={(e) => {
            setBusca(e.target.value);
            setLimite(PAGINA);
          }}
          placeholder='Busca ("chefe sem elden ring") ou cola um link'
          aria-label="Buscar no acervo"
          spellCheck={false}
        />
        {busca && (
          <button className="botao-icone pequeno" onClick={() => setBusca("")} title="Limpar busca">
            <Icone nome="x" tamanho={14} />
          </button>
        )}
      </div>

      <div className="filtro-linha" role="group" aria-label="Franquia">
        <button className={`chip ${origem === null ? "ligado" : ""}`} onClick={() => setOrigem(null)}>
          Todas
        </button>
        {acervo.origens.map((o) => (
          <button
            key={o.nome}
            className={`chip ${origem === o.nome ? "ligado" : ""}`}
            onClick={() => {
              setOrigem(origem === o.nome ? null : o.nome);
              setLimite(PAGINA);
            }}
          >
            {o.nome}
            <span className="contagem">{o.quantas}</span>
          </button>
        ))}
      </div>

      <div className="filtro-categorias" role="group" aria-label="Clima">
        {acervo.categorias
          .filter((c) => c.quantas > 0)
          .map((c) => (
            <button
              key={c.nome}
              className={`chip pequeno ${categorias.has(c.nome) ? "ligado" : ""}`}
              onClick={() => alternarCategoria(c.nome)}
              aria-pressed={categorias.has(c.nome)}
            >
              <span aria-hidden="true">{emojiCategoria(c.nome)}</span> {rotuloCategoria(c.nome)}
            </button>
          ))}
      </div>

      <div className="acervo-acoes">
        {filtrando ? (
          <button className="botao-texto" onClick={limparFiltros}>
            Limpar filtros
          </button>
        ) : (
          <span className="apagado">Tudo. Filtra por franquia, clima ou busca.</span>
        )}
        <div className="grupo-botoes">
          <button
            className="botao"
            disabled={!resultado.length}
            onClick={() => void por(sortear(resultado, MAX_RESULTADOS_DA_BUSCA).map(musicaDaFaixa), "fim")}
            title="Sorteia até 15 das que aparecem e põe na fila"
          >
            <Icone nome="embaralhar" tamanho={15} /> Sortear 15
          </button>
          <button
            className="botao"
            disabled={!resultado.length || resultado.length > 50}
            onClick={() => void por(resultado.map(musicaDaFaixa), "fim")}
            title={resultado.length > 50 ? "Filtra até 50 pra pôr todas" : "Põe todas na fila"}
          >
            <Icone nome="mais" tamanho={15} /> Todas
          </button>
        </div>
      </div>

      <ul className="lista-acervo">
        {link && (
          <li>
            <CartaoMusica
              musica={{ titulo: "Link colado", link }}
              detalhe={link}
              acoes={<AcoesDeMusica por={(onde) => void por([{ titulo: "Link do YouTube", link }], onde)} />}
            />
          </li>
        )}
        {resultado.slice(0, limite).map((f) => (
          <li key={f.id}>
            <CartaoMusica
              musica={musicaDaFaixa(f)}
              ativo={tocando?.faixaId === f.id}
              detalhe={<Detalhe faixa={f} />}
              acoes={
                <AcoesDeMusica por={(onde) => void por([musicaDaFaixa(f)], onde)}>
                  <BotaoPlaylist musica={musicaDaFaixa(f)} avisar={avisar} editando={editando} editar={editar} />
                </AcoesDeMusica>
              }
            />
          </li>
        ))}
        {!resultado.length && !link && (
          <li className="vazio">Nada com esses filtros. Tenta tirar um clima ou trocar a busca.</li>
        )}
      </ul>
      {resultado.length > limite && (
        <button className="botao mostrar-mais" onClick={() => setLimite(limite + PAGINA)}>
          Mostrar mais ({resultado.length - limite})
        </button>
      )}
    </section>
  );
}

function Detalhe({ faixa }: { faixa: Faixa }) {
  const cats = faixa.categorias ?? [];
  return (
    <>
      {faixa.origem.nome}
      {cats.length > 0 && (
        <span className="mini-tags">
          {cats.slice(0, 3).map((c) => (
            <span key={c} className="mini-tag">
              {rotuloCategoria(c)}
            </span>
          ))}
        </span>
      )}
    </>
  );
}

function AcoesDeMusica({ por, children }: { por: (onde: Onde) => void; children?: ReactNode }) {
  return (
    <>
      {children}
      <button className="botao-icone pequeno" onClick={() => por("agora")} title="Tocar agora">
        <Icone nome="tocar" tamanho={14} />
      </button>
      <button className="botao-icone pequeno" onClick={() => por("proxima")} title="Tocar a seguir">
        <Icone nome="aSeguir" tamanho={15} />
      </button>
      <button className="botao-icone pequeno destaque" onClick={() => por("fim")} title="Pôr no fim da fila">
        <Icone nome="mais" tamanho={16} />
      </button>
    </>
  );
}

