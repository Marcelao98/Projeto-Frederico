import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { ProvedorDoMotor } from "./motor/contexto";
import { MotorLocal } from "./motor/motorLocal";
import { ReprodutorYoutube } from "./motor/reprodutorYoutube";
import { falaDoEvento } from "./modos/chat/conversa";
import { registrar } from "./modos/chat/historico";
import { aplicarTema, temaAtual } from "./dados/temas";
import "./temas.css";
import "./estilo.css";

aplicarTema(temaAtual.ler());
temaAtual.inscrever(() => aplicarTema(temaAtual.ler()));

// Hoje o som sai do navegador (MotorLocal + YouTube). Quando o backend
// existir, é só trocar esta linha por um MotorRemoto: o resto não muda.
const palcoDoVideo = document.createElement("div");
palcoDoVideo.className = "palco-video";
const motor = new MotorLocal(new ReprodutorYoutube(palcoDoVideo));

// Como o Bardo avisa no canal quando a fila anda sozinha.
motor.aoEvento((evento) => registrar("freddy", falaDoEvento(evento)));

createRoot(document.getElementById("raiz")!).render(
  <StrictMode>
    <ProvedorDoMotor motor={motor}>
      <App palcoDoVideo={palcoDoVideo} />
    </ProvedorDoMotor>
  </StrictMode>,
);
