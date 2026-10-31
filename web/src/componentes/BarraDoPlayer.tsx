/** A barra de baixo: o que toca, os controles e o volume. Igual em todos os modos. */

import { useEffect, useState } from "react";
import { videoAberto } from "../dados/preferencias";
import { useArmazem } from "../dados/useArmazem";
import { useEstadoDoMotor, useMotor, useProgresso } from "../motor/contexto";
import { miniatura } from "../nucleo/youtube";
import { Icone } from "./Icone";
import { formatarTempo } from "./tempo";

export function BarraDoPlayer() {
  const motor = useMotor();
  const { tocando, proximas, situacao, repetir, volume } = useEstadoDoMotor();
  const { posicao, duracao } = useProgresso();
  const [arrastando, setArrastando] = useState<number | null>(null);
  const comVideo = useArmazem(videoAberto);
  const [volumeAntesDoMudo, setVolumeAntesDoMudo] = useState<number | null>(null);

  useEffect(() => setArrastando(null), [tocando?.uid]);

  const tocandoOuCarregando = situacao === "tocando" || situacao === "carregando";
  const tempo = arrastando ?? posicao;
  const pct = duracao ? Math.min(100, (tempo / duracao) * 100) : 0;

  const alternarMudo = () => {
    if (volume > 0) {
      setVolumeAntesDoMudo(volume);
      void motor.executar({ tipo: "volume", valor: 0 });
    } else {
      void motor.executar({ tipo: "volume", valor: volumeAntesDoMudo ?? 50 });
    }
  };

  return (
    <footer className="barra" aria-label="Player">
      <div className="barra-faixa">
        {tocando ? (
          <>
            <img className="barra-capa" src={miniatura(tocando.link)} alt="" />
            <div className="barra-titulos">
              <div className="barra-titulo" title={tocando.titulo}>
                {tocando.titulo}
              </div>
              <div className="barra-sub">
                {situacao === "carregando" ? "carregando…" : (tocando.origem ?? "YouTube")}
                {proximas.length > 0 && ` · ${proximas.length} na fila`}
              </div>
            </div>
          </>
        ) : (
          <div className="barra-titulos">
            <div className="barra-titulo apagado">Nada tocando</div>
            <div className="barra-sub">Pede no chat ou monta uma playlist</div>
          </div>
        )}
      </div>

      <div className="barra-centro">
        <div className="barra-controles">
          <button
            className={`botao-icone ${repetir ? "ligado" : ""}`}
            onClick={() => void motor.executar({ tipo: "repetir" })}
            disabled={!tocando}
            aria-pressed={repetir}
            title={repetir ? "Repetindo esta faixa" : "Repetir esta faixa"}
          >
            <Icone nome="repetir" />
          </button>
          <button
            className="botao-icone"
            onClick={() => void motor.executar({ tipo: "parar" })}
            disabled={!tocando}
            title="Parar e limpar a fila"
          >
            <Icone nome="parar" />
          </button>
          <button
            className="botao-play"
            onClick={() => void motor.executar({ tipo: "alternar_pausa" })}
            disabled={!tocando}
            title={tocandoOuCarregando ? "Pausar (espaço)" : "Continuar (espaço)"}
          >
            <Icone nome={tocandoOuCarregando ? "pausar" : "tocar"} tamanho={20} />
          </button>
          <button
            className="botao-icone"
            onClick={() => void motor.executar({ tipo: "pular" })}
            disabled={!tocando}
            title="Pular"
          >
            <Icone nome="pular" />
          </button>
          <span className="botao-icone fantasma" aria-hidden="true" />
        </div>
        <div className="barra-progresso">
          <span className="tempo">{formatarTempo(tempo)}</span>
          <input
            type="range"
            className="trilho"
            min={0}
            max={duracao || 1}
            step={1}
            value={Math.min(tempo, duracao || 1)}
            disabled={!tocando || !duracao}
            style={{ "--pct": `${pct}%` } as React.CSSProperties}
            onChange={(e) => setArrastando(Number(e.target.value))}
            onPointerUp={() => {
              if (arrastando !== null) void motor.executar({ tipo: "buscar_posicao", segundos: arrastando });
              setArrastando(null);
            }}
            onKeyUp={() => {
              if (arrastando !== null) void motor.executar({ tipo: "buscar_posicao", segundos: arrastando });
              setArrastando(null);
            }}
            aria-label="Posição na música"
          />
          <span className="tempo">{formatarTempo(duracao)}</span>
        </div>
      </div>

      <div className="barra-volume">
        <button
          className={`botao-icone so-celular ${comVideo ? "ligado" : ""}`}
          onClick={() => videoAberto.escrever(!comVideo)}
          disabled={!tocando}
          aria-pressed={comVideo}
          title={comVideo ? "Esconder vídeo" : "Mostrar vídeo"}
        >
          <Icone nome="video" />
        </button>
        <button className="botao-icone" onClick={alternarMudo} title={volume ? "Mudo" : "Tirar do mudo"}>
          <Icone nome={volume ? "volume" : "mudo"} />
        </button>
        <input
          type="range"
          className="trilho"
          min={0}
          max={100}
          value={volume}
          style={{ "--pct": `${volume}%` } as React.CSSProperties}
          onChange={(e) => void motor.executar({ tipo: "volume", valor: Number(e.target.value) })}
          aria-label="Volume"
        />
        <span className="tempo largura-fixa">{volume}%</span>
      </div>
    </footer>
  );
}
