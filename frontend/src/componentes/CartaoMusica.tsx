import type { ReactNode } from "react";
import type { Musica } from "../comum/tipos";
import { miniatura } from "../comum/youtube";

/** Uma música em linha: capa, título, origem e as ações que quem usa passar. */
export function CartaoMusica({
  musica,
  detalhe,
  acoes,
  ativo,
  compacto,
}: {
  musica: Musica;
  detalhe?: ReactNode;
  acoes?: ReactNode;
  ativo?: boolean;
  compacto?: boolean;
}) {
  return (
    <div className={`cartao-musica ${ativo ? "ativo" : ""} ${compacto ? "compacto" : ""}`}>
      <img className="cartao-capa" src={miniatura(musica.link)} alt="" loading="lazy" />
      <div className="cartao-textos">
        <div className="cartao-titulo" title={musica.titulo}>
          {musica.titulo}
        </div>
        <div className="cartao-sub">{detalhe ?? musica.origem ?? "YouTube"}</div>
      </div>
      {acoes && <div className="cartao-acoes">{acoes}</div>}
    </div>
  );
}
