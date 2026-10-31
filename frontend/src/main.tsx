import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { acervoAtual, montarAcervo } from "./dados/acervo";
import { escolherFreddy, freddy } from "./dados/freddy";
import { definirAvisoDeFalha, usarPlaylistsDoFreddy } from "./dados/playlists";
import { aplicarTema, temaAtual } from "./dados/temas";
import { falaDoEvento } from "./modos/chat/conversa";
import { registrar } from "./modos/chat/historico";
import { ProvedorDoMotor } from "./motor/contexto";
import { MotorLocal } from "./motor/motorLocal";
import { MotorRemoto } from "./motor/motorRemoto";
import { ReprodutorYoutube } from "./motor/reprodutorYoutube";
import type { Motor } from "./motor/tipos";
import "./temas.css";
import "./estilo.css";

aplicarTema(temaAtual.ler());
temaAtual.inscrever(() => aplicarTema(temaAtual.ler()));

/**
 * Qual motor: se o Freddy (python -m freddy) está ligado, a fila e o som
 * moram nele (MotorRemoto). Senão, tudo no navegador (MotorLocal + player do
 * YouTube), como sempre foi. Preferência em dados/freddy.ts (?motor= na URL).
 */
async function iniciar() {
  const api = await escolherFreddy();
  let motor: Motor;
  let palcoDoVideo: HTMLElement | null = null;

  if (api) {
    motor = new MotorRemoto(api.urlDoMotor);
    freddy.escrever(api);
    definirAvisoDeFalha((e) =>
      registrar("freddy", { texto: `Não consegui salvar a playlist no Freddy (${e instanceof Error ? e.message : e}) 😕` }),
    );
    // Acervo e playlists vêm do Freddy; até chegarem, o painel usa o embutido.
    api
      .acervo()
      .then((a) => acervoAtual.escrever(montarAcervo(a.musicas, a.vocabulario)))
      .catch((e) => console.warn("Acervo do Freddy não veio; uso o embutido.", e));
    usarPlaylistsDoFreddy(api).catch((e) => console.warn("Playlists do Freddy não vieram.", e));
  } else {
    palcoDoVideo = document.createElement("div");
    palcoDoVideo.className = "palco-video";
    motor = new MotorLocal(new ReprodutorYoutube(palcoDoVideo));
  }

  // Como o Bardo avisa no canal quando a fila anda sozinha.
  motor.aoEvento((evento) => registrar("freddy", falaDoEvento(evento)));

  createRoot(document.getElementById("raiz")!).render(
    <StrictMode>
      <ProvedorDoMotor motor={motor}>
        <App palcoDoVideo={palcoDoVideo} />
      </ProvedorDoMotor>
    </StrictMode>,
  );
}

void iniciar();
