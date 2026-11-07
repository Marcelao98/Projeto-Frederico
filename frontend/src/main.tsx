import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
// O visual: as cores das plumagens e o básico primeiro; cada tela importa o
// CSS dela; o das telas menores por último, por cima de tudo.
import "./estilo/temas.css";
import "./estilo/base.css";
import { App } from "./App";
import { acervoAtual, montarAcervo } from "./estado/acervo";
import {
  discord,
  escolherFreddy,
  freddy,
  freddyLigouDepois,
  preferenciaEfetiva,
  vigiarFreddy,
  type EstadoDiscord,
} from "./api/freddy";
import { definirAvisoDeFalha, usarPlaylistsDoFreddy } from "./estado/playlists";
import { aplicarTema, temaAtual } from "./estado/temas";
import { falaDoEvento } from "./modos/chat/conversa";
import { registrar } from "./modos/chat/historico";
import { ligarNarrador } from "./modos/chat/narrador";
import { ProvedorDoMotor } from "./motor/contexto";
import { MotorLocal } from "./navegador/motorLocal";
import { MotorRemoto } from "./api/motorRemoto";
import { ReprodutorYoutube } from "./navegador/reprodutorYoutube";
import type { Motor } from "./motor/tipos";
import "./estilo/telas-menores.css";

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
    const remoto = new MotorRemoto(api.urlDoMotor);
    motor = remoto;
    freddy.escrever(api);
    // O bot do Discord: o Freddy manda o estado ao conectar e a cada mudança.
    remoto.aoMensagem("discord", (d) => discord.escrever(d as EstadoDiscord));
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
    // Se o Freddy ligar depois, a tela oferece trocar (sem trocar sozinha: a fila sumiria).
    // (Quem escolheu "só navegador" de propósito não é incomodado.)
    if (preferenciaEfetiva() === "auto") vigiarFreddy(() => freddyLigouDepois.escrever(true));
  }

  // O Freddy avisa no chat quando a fila anda sozinha.
  motor.aoEvento((evento) => registrar("freddy", falaDoEvento(evento)));
  // E o que mudou fora do chat (Playlist, barra do player, outra aba), em letra miúda.
  ligarNarrador(motor, (texto) => registrar("freddy", { texto }, true));

  createRoot(document.getElementById("raiz")!).render(
    <StrictMode>
      <ProvedorDoMotor motor={motor}>
        <App palcoDoVideo={palcoDoVideo} />
      </ProvedorDoMotor>
    </StrictMode>,
  );
}

void iniciar();
