# Painel do Freddy (frontend)

React + TypeScript + Vite, empacotado como **app desktop com Tauri**. Por
enquanto toca sozinho, pelo player do YouTube embutido; o backend
(Discord, mic virtual) entra depois sem mudar as telas.

## Baixar e usar (sem compilar nada)

Na página **Releases** do GitHub, baixe o arquivo do seu sistema:

- **Windows:** `Freddy_..._x64-setup.exe` (ou o `.msi`)
- **Linux:** `.AppImage` (qualquer distro) ou `.deb` (Ubuntu, Mint, Debian)
- **Mac:** `.dmg`

Quem compila é o GitHub (`.github/workflows/app.yml`): a cada tag de versão
(`v0.1.0`, `v0.2.0`...) ele roda os testes, compila os três sistemas e
publica a Release. Pra lançar uma versão nova: suba `version` em
`src-tauri/tauri.conf.json` e em `package.json`, faça o commit e
`git tag v0.2.0 && git push origin v0.2.0`.

## Rodar a partir do código (pra desenvolver)

Precisa de **Node 18+** e de **Rust** (https://rustup.rs). No Windows, também
do "Desktop development with C++" do Visual Studio Build Tools; no Linux, das
bibliotecas do WebKitGTK. Guia: https://v2.tauri.app/start/prerequisites/

```bash
cd frontend
npm install
npm run app          # abre o Freddy numa janela (a 1ª vez compila o Rust: uns minutos)
```

Sem Rust, dá pra ver no navegador: `npm run dev` e abrir http://localhost:5173.

Outros comandos:

```bash
npm test             # testes (vitest), sem rede
npm run build        # checa os tipos e gera dist/
npm run app:build    # gera o instalador (.msi/.exe no Windows) em src-tauri/target/release/bundle
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

## Plumagens (temas)

Cinco temas, um por calopsita. A ave do logo muda junto.

| Tema | Cara |
|---|---|
| **Frederico** (padrão) | branco e prata, acento rosado do bico: a calopsita de verdade (cara-branca) |
| Lutino | creme e amarela, bochecha laranja |
| Cinza silvestre | escuro, crista amarela e bochecha laranja |
| Canela | escuro castanho e quente |
| Cara-branca | escuro, cinza e branco, sem amarelo |

Troca pela barra lateral ("Plumagem") ou clicando na calopsita do logo (no
celular, é o único jeito). As cores ficam em `src/temas.css`; criar um tema
é um bloco `[data-tema="..."]` lá e uma linha em `src/dados/temas.ts`. Dá
pra fazer de outras aves do mesmo jeito.

## Como está organizado

```
src-tauri/      a casca desktop (Rust): janela, ícone, instalador
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
├── dados/      acervo (lê backend/modules/bardo/dataset), playlists, temas, preferências
├── modos/      um diretório por modo + registro.tsx (a lista de modos)
│   ├── chat/       ModoChat + conversa.ts (texto → comando → resposta)
│   ├── playlist/   ModoPlaylist, PainelAcervo, PainelFila
│   └── mixer/      ModoEmBreve
└── componentes/ barra do player, cartão de música, ícones, a calopsita
```

**O mesmo acervo do Bardo.** O painel importa `backend/modules/bardo/dataset/*.json`
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
- No app instalado, o painel é servido em `http://localhost:47823` (não no
  endereço interno do Tauri), porque o player do YouTube não toca sem uma
  origem web normal. Se outra coisa usar essa porta, o app não abre.
- Atalhos: Espaço pausa/continua, `/` vai pro chat, Alt+1…4 troca de modo.
