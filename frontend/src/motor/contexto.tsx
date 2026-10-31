/** Liga o motor ao React: quem precisa do estado usa os hooks daqui. */

import { createContext, useContext, useSyncExternalStore, type ReactNode } from "react";
import type { EstadoMotor, Motor, Progresso } from "./tipos";

const ContextoDoMotor = createContext<Motor | null>(null);

export function ProvedorDoMotor({ motor, children }: { motor: Motor; children: ReactNode }) {
  return <ContextoDoMotor.Provider value={motor}>{children}</ContextoDoMotor.Provider>;
}

export function useMotor(): Motor {
  const motor = useContext(ContextoDoMotor);
  if (!motor) throw new Error("useMotor fora do ProvedorDoMotor");
  return motor;
}

export function useEstadoDoMotor(): EstadoMotor {
  const motor = useMotor();
  return useSyncExternalStore(motor.inscrever, motor.estado);
}

/** Separado do estado: muda 2x por segundo e só a barra do player precisa. */
export function useProgresso(): Progresso {
  const motor = useMotor();
  return useSyncExternalStore(motor.inscreverProgresso, motor.progresso);
}
