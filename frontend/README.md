# Painel do Freddy (frontend)

React + TypeScript + Vite, empacotado como **app desktop com Tauri**. Toca
de dois jeitos, sem mudar as telas:

- **Pelo Freddy** (o backend): o app liga ele sozinho. A fila, o som, o
  acervo e as playlists moram nele; dá pra abrir o app e o navegador ao mesmo
  tempo que os dois veem a mesma fila. Ver `backend/README.md`.
- **Pelo navegador**: sem o Freddy (por exemplo, `npm run dev` sem o
  backend), toca sozinho pelo player do YouTube embutido. É o modo de
  reserva: as funções novas são pelo Freddy.

A linha "Este computador" na barra lateral mostra qual está em uso (clicar
alterna). Pra forçar: `?motor=navegador` ou `?motor=freddy` na URL.

## Baixar e usar (sem compilar nada)

Na página **Releases** do GitHub, baixe o arquivo do seu sistema:

- **Windows:** `Freddy_..._x64-setup.exe` (ou o `.msi`). O FFmpeg vem junto.
- **Fedora:** `.rpm` (`sudo dnf install ./Freddy-....rpm`; puxa ffmpeg, opus
  e portaudio). **Ubuntu/Mint/Debian:** `.deb`. **Outras:** `.AppImage`.
- **Mac:** `.dmg` (precisa do FFmpeg: `brew install ffmpeg`; Mac Intel ainda
  fica sem o backend).

É só abrir: o app liga o Freddy sozinho. Quem compila é o GitHub
(`.github/workflows/app.yml`): a cada push num branch `claude/...` que mexa
no app, ele roda os testes, empacota o backend, compila os três sistemas e
publica a Release `v<versão>`. Pra lançar versão nova, ver "Lançar versão
nova do app" no `AGENTS.md` da raiz.

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

- **Chat**: pede música em português pro Freddy, sem @ e sem
  LLM. "toca triste e bloodborne", "toca chefe sem elden ring", "pula",
  "repete", "volume 30", "fila", "ajuda". O nome na frente é opcional
  ("Freddy, toca…"). Enquanto você digita, ele mostra quantas faixas do
  acervo batem, completa franquia e clima com **Tab** e lembra os pedidos
  anteriores com **↑ ↓**. Quando a fila anda sozinha, ele avisa no chat.
- **Playlist**: o acervo inteiro com busca, filtro por franquia e por
  clima (os mesmos de cima), e a fila do lado. Toca agora, toca a seguir
  ou põe no fim. Arrasta pra reordenar (ou Alt+↑↓), embaralha, tira, salva
  com nome e carrega depois. O 📁 de cada faixa põe ela numa playlist salva
  (ou numa nova) sem tocar nada; clicar numa playlist salva abre ela pra
  editar (tirar, reordenar, renomear) sem mexer na fila. "Tocar" uma
  playlist troca a fila por ela; o ＋ acrescenta no fim.

- **Acervo**: as faixas numa tabela, como planilha. Muda o nome e os temas
  ali mesmo (salva ao sair do campo ou no Enter; Esc desfaz), filtra por
  franquia ou "só sem tema", e toca a faixa pra ouvir antes de marcar.
  **Baixar planilha** salva o CSV na pasta Downloads; edita no
  LibreOffice/Excel e **Enviar planilha** mostra o que muda antes de aplicar.
  Precisa do Freddy ligado pra salvar.

Playlists também pelo chat: **playlists** lista as salvas, **toca a
playlist sessão 12** troca a fila por ela (o nome não precisa ser exato),
**põe a playlist cripta na fila** acrescenta, e **salva a fila como sessão
12** guarda o que toca mais a fila. Se não couber tudo (a fila tem 50
lugares), o Freddy avisa quantas entraram.

No chat, com o Freddy ligado, dá pra arrumar o acervo conversando: **temas**
mostra os temas da que toca e pergunta se está certo (botões ou "tá
certo"/"não"); **temas: taverna, alegre** troca; **revisar** (ou **revisar
hollow knight**) passa faixa por faixa, as sem tema primeiro. E o chat conta,
em letra miúda, o que mudou fora dele (Playlist, barra do player, outra aba):
"▶ Tocando Greenpath", "+5 na fila".

**Discord** (barra lateral, com o Freddy ligado): cola o token do bot uma
vez, convida pros servidores, escolhe o canal de voz e o bot toca a mesma
fila do painel. Guia em `docs/discord.md`.

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
celular, é o único jeito). As cores ficam em `src/estilo/temas.css`; criar um tema
é um bloco `[data-tema="..."]` lá e uma linha em `src/estado/temas.ts`. Dá
pra fazer de outras aves do mesmo jeito.

## Como está organizado

```
src-tauri/      a casca desktop (Rust): janela, liga o backend, instalador
src/
├── main.tsx    escolhe o motor (o Freddy ou o navegador) e monta a tela
├── api/        falar com o Freddy
│   ├── freddy.ts        as rotas (acervo, playlists, Discord...) e "o Freddy está ligado?"
│   └── motorRemoto.ts   o motor pelo WebSocket
├── motor/      o contrato do motor (o mesmo pros dois motores)
│   ├── tipos.ts         Motor, EstadoMotor, Comandos, EventoMotor
│   ├── contexto.tsx     hooks do React (useMotor, useEstadoDoMotor, useConexao...)
│   └── contratoCasos.ts roda os casos de backend/freddy/salas/casos_contrato.json
├── estado/     o que a tela guarda: acervo, playlists, temas, preferências
├── modos/      uma pasta por modo (cada uma com seu .css) + registro.tsx (a lista)
│   ├── chat/       ModoChat + conversa.ts (texto → comando → resposta),
│   │               revisao.ts (temas pelo chat), playlistsChat.ts (playlists pelo chat),
│   │               narrador.ts (o que mudou fora do chat)
│   ├── acervo/     ModoAcervo (tabela editável + planilha)
│   ├── playlist/   ModoPlaylist, PainelAcervo, PainelFila, editor de playlist
│   └── mixer/      ModoEmBreve
├── componentes/ barra do player, cartão de música, ícones, a calopsita, JanelaDiscord
├── comum/      tipos (Faixa, Musica), texto, links do YouTube
├── navegador/  o modo reserva, sem o Freddy (congelado: função nova é só pelo Freddy)
│   ├── motorLocal.ts, fila.ts, reprodutor*.ts   tocar pelo player do YouTube
│   └── pedido.ts, busca.ts                      portas fiéis de backend/freddy/nucleo/
└── estilo/     base.css (comum), temas.css (plumagens), telas-menores.css (por último)
```

**O mesmo acervo do backend.** O painel importa `acervo/*.json` (na raiz do
repositório) direto, pelo alias `@acervo` no `vite.config.ts`, sem cópia.
Com o Freddy ligado, o acervo vem dele (`GET /acervo`), com os ajustes e as
faixas que a mesa ensinou. A busca e o interpretador de pedidos do modo
navegador são portas fiéis de `backend/freddy/nucleo/`: **mudou uma regra
num, muda no outro.**

**O contrato `Motor`** (`motor/tipos.ts`) é a costura com o backend. As telas
só chamam `motor.executar({ tipo: "pular" })` e leem `useEstadoDoMotor()`.
O `main.tsx` escolhe o `MotorRemoto` (o Freddy) ou o `MotorLocal` (o
navegador). Os casos de `backend/freddy/salas/casos_contrato.json` rodam no
`MotorLocal`, no motor do Python e, no GitHub, no `MotorRemoto` falando com o
backend de verdade (`contrato.remoto.test.ts`): os três se comportam igual.

## Como crescer

- **Modo novo** (mixer, soundboard, cenas): cria `src/modos/<nome>/` (com o
  `.css` dele, importado pelo componente), põe uma entrada em `modos/registro.tsx`. Navegação e atalho Alt+N saem sozinhos.
- **Comando novo** (ex.: volume por camada): acrescenta em `Comandos` no
  `motor/tipos.ts`, implementa no `MotorLocal` e no motor do backend
  (`backend/freddy/salas/motor.py` + validação em `api/protocolo.py`), e
  põe um caso em `casos_contrato.json`. O TypeScript cobra os argumentos e o
  retorno em quem chama.
- **Fonte nova** (arquivo local, Freesound) e **saída nova** (mic virtual):
  é no backend (`backend/freddy/audio/fontes/` e `saidas/`).

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
- Link externo (convite do bot, Developer Portal) quem abre é o backend
  (`POST /abrir`, só Discord e o GitHub do Freddy): o app não abre link sozinho.
- Atalhos: Espaço pausa/continua, `/` vai pro chat, Alt+1…4 troca de modo.
