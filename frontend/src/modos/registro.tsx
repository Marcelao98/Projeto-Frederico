/**
 * Os modos do painel. Pra criar um modo novo: faz o componente em
 * src/modos/<nome>/ e acrescenta uma entrada aqui. A barra lateral, o
 * atalho de teclado e a troca de modo saem disso sozinhos.
 */

import type { ComponentType } from "react";
import type { NomeIcone } from "../componentes/Icone";
import type { Acervo } from "../dados/acervo";
import { ModoAcervo } from "./acervo/ModoAcervo";
import { ModoChat } from "./chat/ModoChat";
import { ModoEmBreve } from "./mixer/ModoEmBreve";
import { ModoPlaylist } from "./playlist/ModoPlaylist";

export interface PropsDeModo {
  acervo: Acervo;
}

export interface DefinicaoDeModo {
  id: string;
  nome: string;
  icone: NomeIcone;
  descricao: string;
  Componente: ComponentType<PropsDeModo>;
  emBreve?: boolean;
}

export const MODOS: DefinicaoDeModo[] = [
  { id: "chat", nome: "Chat", icone: "chat", descricao: "Pede em português", Componente: ModoChat },
  { id: "playlist", nome: "Playlist", icone: "lista", descricao: "Monta a fila na mão", Componente: ModoPlaylist },
  { id: "acervo", nome: "Acervo", icone: "planilha", descricao: "Arruma nomes e temas", Componente: ModoAcervo },
  {
    id: "mixer",
    nome: "Mixer",
    icone: "mixer",
    descricao: "Camadas e ducking",
    emBreve: true,
    Componente: () => (
      <ModoEmBreve
        titulo="Mixer"
        resumo="Música, ambiente e efeitos ao mesmo tempo, cada um com o seu volume."
        novidades={[
          { icone: "lista", titulo: "Camada de música", texto: "A fila de hoje, agora com crossfade entre faixas." },
          { icone: "volume", titulo: "Camada de ambiente", texto: "Loops de chuva, taverna, masmorra por baixo da música." },
          { icone: "grade", titulo: "Camada de efeitos", texto: "Trovão, espada, rugido: disparados na hora." },
          { icone: "mic", titulo: "Ducking", texto: "A música abaixa sozinha quando um efeito toca ou quando você fala." },
        ]}
      />
    ),
  },
  {
    id: "soundboard",
    nome: "Soundboard",
    icone: "grade",
    descricao: "Pads e cenas",
    emBreve: true,
    Componente: () => (
      <ModoEmBreve
        titulo="Soundboard"
        resumo="Uma grade de pads e cenas prontas pra mesa: um clique e o clima muda."
        novidades={[
          { icone: "grade", titulo: "Pads com atalho", texto: "Teclas 1 a 9 e F1 a F12; depois Stream Deck e MIDI." },
          { icone: "salvar", titulo: "Cenas", texto: '"Taverna": música calma + ambiente + os pads da cena, num clique.' },
          { icone: "pasta", titulo: "Fontes", texto: "Arquivos do seu PC e Freesound (CC0, com créditos guardados)." },
          { icone: "discord", titulo: "Saídas", texto: "Mic virtual (seu mic + o som) ou o bot do Freddy no Discord." },
        ]}
      />
    ),
  },
];
