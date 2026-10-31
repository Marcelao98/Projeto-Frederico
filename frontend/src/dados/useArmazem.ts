import { useSyncExternalStore } from "react";
import type { Armazem } from "./armazem";

export function useArmazem<T>(armazem: Armazem<T>): T {
  return useSyncExternalStore(armazem.inscrever, armazem.ler);
}
