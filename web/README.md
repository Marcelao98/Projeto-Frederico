# Painel do Freddy (frontend)

React + TypeScript + Vite. Por enquanto roda **sozinho no navegador**: o
som sai pelo player do YouTube embutido na página. O backend Python (mic
virtual e bot do Discord) vem depois e entra sem mudar as telas.

```bash
cd web
npm install
npm run dev        # http://localhost:5173
npm test           # testes (vitest), sem rede
npm run build      # checa os tipos e gera dist/
```

## Os dois modos

- **Chat**: fala com o Freddy como fala com a Natty no Discord, sem @ e sem
  LLM. "toca triste e bloodborne", "toca chefe sem elden ring", "pula",
  "repete", "volume 30", "fila", "ajuda". O nome na frente é opcional
  ("Freddy, toca…"). Enquanto você digita, ele mostra quantas faixas do
  acervo batem, completa franquia e clima com **Tab** e lembra os pedidos
  anteriores com **↑ ↓**. Quando a fila anda sozinha, ele avisa no chat.
- **Playlist**: o acervo inteiro com busca, filtro por franquia e por
  clima (os mesmos de cima), e a fila do lado. Toca agora, toca a seguir
  ou põe no fim. Arrasta pra reordenar (ou Alt+↑↓), embaralha, tira, salva
  com nome e carrega depois.

Mixer e Soundboard já aparecem na barra lateral como "em breve".

## Como está organizado

```
src/
├── nucleo/     lógica pura, sem React: porta do service.py do Bardo
│   ├── pedido.ts   interpretarPedido(): "toca X", "pula", "volume 30"...
│   ├── busca.ts    busca booleana + vocabulário (e / ou / sem, sinônimos)
│   └── youtube.ts  links e ids de vídeo
├── motor/      quem toca: o contrato Motor e a implementação local
│   ├── tipos.ts         Motor, EstadoMotor, Comandos, EventoMotor
│   ├── fila.ts          a fila (imutável)
│   ├── motorLocal.ts    Motor que roda no navegador
│   ├── reprodutor*.ts   Reprodutor (interface) + o do YouTube
│   └── contexto.tsx     hooks do React (useMotor, useEstadoDoMotor...)
├── dados/      acervo (lê modules/bardo/dataset), playlists salvas, preferências
├── modos/      um diretório por modo + registro.tsx (a lista de modos)
│   ├── chat/       ModoChat + conversa.ts (texto → comando → resposta)
│   ├── playlist/   ModoPlaylist, PainelAcervo, PainelFila
│   └── mixer/      ModoEmBreve
└── componentes/ barra do player, cartão de música, ícones, a calopsita
```

**O mesmo acervo do Bardo.** O painel importa `modules/bardo/dataset/*.json`
direto (alias `@dataset` no `vite.config.ts`), sem cópia. A busca e o
interpretador de pedidos são portas fiéis do `service.py`: os testes do
`test_service.py` foram traduzidos, e conferi que TS e Python dão o mesmo
resultado em buscas e pedidos de verdade. **Mudou uma regra num, muda no
outro.** Quando o backend existir, ele vira a fonte única e o chat pode
mandar o texto cru pra ele.

**O contrato `Motor`** (`motor/tipos.ts`) é a costura com o backend. As telas
só chamam `motor.executar({ tipo: "pular" })` e leem `useEstadoDoMotor()`.
Hoje quem responde é o `MotorLocal`; depois um `MotorRemoto` (WebSocket pro
backend Python) implementa a mesma interface, e a troca é uma linha no
`main.tsx`.

## Como crescer

- **Modo novo** (mixer, soundboard, cenas): cria `src/modos/<nome>/`, põe uma
  entrada em `modos/registro.tsx`. Navegação e atalho Alt+N saem sozinhos.
- **Comando novo** (ex.: volume por camada): acrescenta em `Comandos` no
  `motor/tipos.ts` e implementa no motor. O TypeScript cobra os argumentos
  e o retorno em quem chama.
- **Fonte nova** (arquivo local, Freesound): outro `Reprodutor`.
- **Saída nova** (mic virtual, Discord): é o backend, via `MotorRemoto`.

## Limites de hoje

- Busca livre no YouTube (quando o acervo não tem) e o "era essa?" que
  ensina faixa nova precisam do backend (yt-dlp). O chat avisa e pede o link.
- Vídeo com embed bloqueado pelo dono não toca no navegador: o Freddy avisa
  e pula. No backend isso some, porque ele baixa o áudio direto.
- A fila não sobrevive a recarregar a página. As playlists salvas e a
  preferência de modo sobrevivem (ficam no `localStorage`).
- Atalhos: Espaço pausa/continua, `/` vai pro chat, Alt+1…4 troca de modo.
