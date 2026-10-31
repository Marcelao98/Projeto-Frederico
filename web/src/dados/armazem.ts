/**
 * Um pedacinho de estado observável, pro React ler com useSyncExternalStore.
 * Com `chave`, persiste no localStorage (e sobrevive se ele falhar).
 */

export interface Armazem<T> {
  ler(): T;
  escrever(valor: T | ((anterior: T) => T)): void;
  inscrever(ouvinte: () => void): () => void;
}

export function criarArmazem<T>(inicial: T, chave?: string): Armazem<T> {
  let valor = inicial;
  if (chave) {
    try {
      const salvo = localStorage.getItem(chave);
      if (salvo !== null) valor = JSON.parse(salvo) as T;
    } catch {
      // Sem localStorage (aba privada, teste): segue só em memória.
    }
  }
  const ouvintes = new Set<() => void>();
  return {
    ler: () => valor,
    escrever(novo) {
      valor = typeof novo === "function" ? (novo as (a: T) => T)(valor) : novo;
      if (chave) {
        try {
          localStorage.setItem(chave, JSON.stringify(valor));
        } catch {
          // idem
        }
      }
      for (const o of ouvintes) o();
    },
    inscrever(ouvinte) {
      ouvintes.add(ouvinte);
      return () => void ouvintes.delete(ouvinte);
    },
  };
}
