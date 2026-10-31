/** Lugar guardado pros modos que ainda vão existir. */

import { Icone, type NomeIcone } from "../../componentes/Icone";

export interface Novidade {
  icone: NomeIcone;
  titulo: string;
  texto: string;
}

export function ModoEmBreve({ titulo, resumo, novidades }: { titulo: string; resumo: string; novidades: Novidade[] }) {
  return (
    <section className="modo modo-em-breve">
      <header className="modo-topo">
        <div>
          <h1>
            {titulo} <span className="selo">em breve</span>
          </h1>
          <p>{resumo}</p>
        </div>
      </header>
      <div className="grade-novidades">
        {novidades.map((n) => (
          <article key={n.titulo} className="novidade">
            <Icone nome={n.icone} tamanho={22} />
            <h3>{n.titulo}</h3>
            <p>{n.texto}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
