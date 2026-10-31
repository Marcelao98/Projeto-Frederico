# Painel do Freddy (frontend)

React + TypeScript + Vite, empacotado como **app desktop com Tauri**. Toca
de dois jeitos, sem mudar as telas:

- **Pelo Freddy** (o backend, `python -m freddy`): se ele estiver ligado, o
  painel acha sozinho. A fila, o som, o acervo e as playlists moram nele;
  dá pra abrir o app e o navegador ao mesmo tempo que os dois veem a mesma
  fila. Ver `backend/README.md`.
- **Pelo navegador**: com o Freddy desligado, toca sozinho pelo player do
  YouTube embutido, como sempre.

A linha "Este computador" na barra lateral mostra qual está em uso (clicar
alterna). Pra forçar: `?motor=navegador` ou `?motor=freddy` na URL.

## Baixar e usar (sem compilar nada)

Na página **Releases** do GitHub, baixe o arquivo do seu sistema:

- **Windows:** `Freddy_..._x64-setup.exe` (ou o `.msi`)
- **Linux:** `.AppImage` (qualquer distro) ou `.deb` (Ubuntu, Mint, Debian)
- **Mac:** `.dmg`

Quem compila é o GitHub (`.github/workflows/app.yml`): a cada tag de versão
(`v0.1.0`, `v0.2.0`...) ele roda os testes, compila os três sistemas e
publica a Release. Pra lançar uma versão nova, ver "Lançar versão nova do
app" no `CLAUDE.md` da raiz.

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

- **Acervo**: as faixas numa tabela, como planilha. Muda o nome e os temas
  ali mesmo (salva ao sair do campo ou no Enter; Esc desfaz), filtra por
  franquia ou "só sem tema", e toca a faixa pra ouvir antes de marcar.
  **Baixar planilha** salva o CSV na pasta Downloads; edita no
  LibreOffice/Excel e **Enviar planilha** mostra o que muda antes de aplicar.
  Precisa do Freddy ligado pra salvar.

No chat, com o Freddy ligado, dá pra arrumar o acervo conversando: **temas**
mostra os temas da que toca e pergunta se está certo (botões ou "tá
certo"/"não"); **temas: taverna, alegre** troca; **revisar** (ou **revisar
hollow knight**) passa faixa por faixa, as sem tema primeiro. E o chat conta,
em letra miúda, o que mudou fora dele (Playlist, barra do player, outra aba):
"▶ Tocando Greenpath", "+5 na fila".

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
├── motor/      quem toca: o contrato Motor e os dois motores
│   ├── tipos.ts         Motor, EstadoMotor, Comandos, EventoMotor
│   ├── fila.ts          a fila (imutável)
│   ├── motorLocal.ts    Motor que roda no navegador
│   ├── motorRemoto.ts   Motor que fala com o Freddy (WebSocket)
│   ├── contratoCasos.ts roda os casos de backend/freddy/motor/casos_contrato.json
│   ├── reprodutor*.ts   Reprodutor (interface) + o do YouTube
│   └── contexto.tsx     hooks do React (useMotor, useEstadoDoMotor, useConexao...)
├── dados/      acervo, playlists, temas, preferências; freddy.ts (API do backend e a escolha do motor)
├── modos/      um diretório por modo + registro.tsx (a lista de modos)
│   ├── chat/       ModoChat + conversa.ts (texto → comando → resposta),
│   │               revisao.ts (temas pelo chat), narrador.ts (o que mudou fora do chat)
│   ├── acervo/     ModoAcervo (tabela editável + planilha)
│   ├── playlist/   ModoPlaylist, PainelAcervo, PainelFila
│   └── mixer/      ModoEmBreve
└── componentes/ barra do player, cartão de música, ícones, a calopsita
```

**O mesmo acervo do Bardo.** O painel importa `backend/modules/bardo/dataset/*.json`
direto (alias `@dataset` no `vite.config.ts`), sem cópia. A busca e o
interpretador de pedidos são portas fiéis do `service.py`: os testes do
`test_service.py` foram traduzidos, e conferi que TS e Python dão o mesmo
resultado em buscas e pedidos de verdade. **Mudou uma regra num, muda no
outro.** Com o Freddy ligado, o acervo vem dele (`GET /acervo`), com as
faixas que a mesa ensinou.

**O contrato `Motor`** (`motor/tipos.ts`) é a costura com o backend. As telas
só chamam `motor.executar({ tipo: "pular" })` e leem `useEstadoDoMotor()`.
O `main.tsx` escolhe o `MotorLocal` ou o `MotorRemoto`. Os casos de
`backend/freddy/motor/casos_contrato.json` rodam no `MotorLocal`, no Motor
do Python e, no GitHub, no `MotorRemoto` falando com o backend de verdade
(`contrato.remoto.test.ts`): os três se comportam igual.

## Como crescer

- **Modo novo** (mixer, soundboard, cenas): cria `src/modos/<nome>/`, põe uma
  entrada em `modos/registro.tsx`. Navegação e atalho Alt+N saem sozinhos.
- **Comando novo** (ex.: volume por camada): acrescenta em `Comandos` no
  `motor/tipos.ts`, implementa no `MotorLocal` e no motor do backend
  (`backend/freddy/motor/motor.py` + validação em `api/protocolo.py`), e
  põe um caso em `casos_contrato.json`. O TypeScript cobra os argumentos e o
  retorno em quem chama.
- **Fonte nova** (arquivo local, Freesound): outro `Reprodutor`.
- **Saída nova** (mic virtual, Discord): é o backend, via `MotorRemoto`.

## Limites de hoje

- Busca livre no YouTube (quando o acervo não tem) e o "era essa?" que
  ensina faixa nova só existem com o Freddy ligado. Sem ele, o chat pede o link.
- Pelo navegador, vídeo com embed bloqueado pelo dono não toca: o painel
  avisa e pula. Pelo Freddy isso some (ele pega o áudio direto).
- Pelo navegador, a fila não sobrevive a recarregar a página (pelo Freddy,
  sobrevive enquanto ele estiver ligado). Playlists salvas sobrevivem nos dois.
- Pelo Freddy não tem vídeo, só a capa.
- No app instalado, o painel é servido em `http://localhost:47823` (não no
  endereço interno do Tauri), porque o player do YouTube não toca sem uma
  origem web normal. Se outra coisa usar essa porta, o app não abre.
- Atalhos: Espaço pausa/continua, `/` vai pro chat, Alt+1…4 troca de modo.
