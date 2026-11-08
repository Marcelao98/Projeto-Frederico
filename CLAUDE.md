# Projeto Frederico (Freddy)

O som da mesa de RPG. O mestre pede música em português ("toca triste e
bloodborne"), o Freddy toca na caixa de som ou na call do Discord, e tudo é
controlado por um painel com a cara do Frederico, a calopsita de verdade do
Marcelo (cara-branca, asa prateada, olho preto, bico rosado).

**O Freddy é o áudio do Nattyverso:** a Natty (outro projeto do Marcelo) não
toca nada; não se mexe nela por causa de áudio.

**Licença GPL-3.0.** Código adaptado do Kenku FM (também GPL-3.0) diz no
topo do arquivo de onde veio.

**Antes de começar, leia o `ROADMAP.md`** (o que está pronto, a fase atual,
as decisões) e o **`docs/ARQUITETURA.md`** (o desenho, as pastas e as
etapas). Este arquivo tem as regras que não podem quebrar.

## Como o repositório está dividido

```
acervo/     o acervo oficial: musicas.json + vocabulario.json (fonte única)
backend/    Python: o Freddy (backend/freddy/) e os scripts do acervo (backend/scripts/)
frontend/   o painel (React + TypeScript, src/) e a casca do app (Tauri/Rust, src-tauri/)
docs/       ARQUITETURA.md, discord.md
scripts/versao.py   a versão do app nos 6 arquivos
freddy.sh   pra desenvolver: liga o backend e abre o app na ordem certa
.github/workflows/app.yml   testa, empacota o backend, compila e publica a Release
```

## Regras de arquitetura (não quebrar)

- **O backend é o Freddy; o painel e o Discord são telas.** Decisão (fila, o
  que tocar, entender pedido) mora em `backend/freddy/`.
- **Acervo é um só:** `acervo/` na raiz. O backend acha por
  `config.PASTA_ACERVO` (no app empacotado, junto do executável: o
  `app.yml` põe com `--add-data`); o painel importa os JSON pelo alias
  `@acervo` (`frontend/vite.config.ts` e `tsconfig.json`). Não copiar.
- **`backend/freddy/nucleo/`** (texto, pedido, vocabulário, busca) é lógica
  pura: nada de rede, som ou Discord. **Paridade com o painel:**
  `frontend/src/navegador/pedido.ts` e `busca.ts` são portas fiéis de
  `nucleo/pedido.py` e `nucleo/busca.py` (o modo navegador usa). Mudou uma
  regra num, muda no outro, e os testes dos dois lados.
- **O contrato do motor** (`frontend/src/motor/tipos.ts`) é a costura entre o
  painel e o backend: as telas só chamam `motor.executar({ tipo: ... })` e
  leem o estado. Dois motores no painel: `MotorRemoto`
  (`src/api/motorRemoto.ts`, WebSocket pro backend) e `MotorLocal`
  (`src/navegador/`, o modo reserva sem o Freddy); o `src/main.tsx` escolhe.
  No backend, `freddy/salas/motor.py` é a porta fiel do `MotorLocal`.
  **Comando novo** = entrada em `Comandos` + os dois motores + validação em
  `freddy/api/protocolo.py` + um caso em `freddy/salas/casos_contrato.json`
  (rodado pelos testes dos dois lados; alias `@contrato` no painel).
- **O modo navegador está congelado:** funciona sem o Freddy, mas função
  nova é só pelo Freddy.
- **Som** (`freddy/audio/`): fontes (`fontes/`: YouTube via yt-dlp, FFmpeg,
  assobio) → `Mesa` → saídas (`saidas/`: caixa, Discord, muda). A Mesa
  entrega quadros de 20 ms, 48 kHz, estéreo, 16 bits (o formato do Discord e
  a base do mixer). **Um relógio só:** com o bot tocando numa call, quem
  puxa a Mesa é o Discord (`saidas/discord.py`) e a caixa toca a cópia
  (`Mesa.ler_para_local`); nunca dois puxando. Avisos do áudio pro motor
  passam por `agendar` (o loop do servidor): o motor roda numa thread só.
- **yt-dlp** (`audio/fontes/ytdlp.py`): no app instalado, usa o mais novo já
  baixado (pasta do mestre, `yt-dlp/yt-dlp.zip`) e procura outro uma vez por
  dia, só do GitHub oficial do yt-dlp, com SHA-256 conferido; se o baixado
  não carregar, volta pro que veio no app. Em desenvolvimento, é o do `pip`.
- **Bot do Discord** (`freddy/integracoes/discord/bot.py`): roda no mesmo
  loop do servidor e só traduz Discord ↔ `freddy/conversa/` (o cérebro do
  chat, sem discord.py) e o motor. O player segue o Kenku
  (`PlaybackManager.ts`): play com uma `SaidaDiscord` nova quando o som
  começa, stop quando acaba. **`davey` fica em `<0.2`**: a 0.2 mudou a API e
  o discord.py 2.7 nunca fica pronto pra cifrar (DAVE), e a call fica muda
  sem erro nenhum. Token só na pasta do mestre (`discord.json`) ou em
  `FREDDY_DISCORD_TOKEN`. Ids do Discord vão pro painel como texto. Pra
  testar a call: janela do Discord → 🐦 assobio e "Diagnóstico"
  (`GET /diagnostico`). Aqui na nuvem não dá pra testar o Discord de verdade
  (o proxy bloqueia discord.com): teste com dublês e peça pro Marcelo.
- **API** (`freddy/api/`): `app.py` só monta as peças em `app.state`; rotas
  em `api/rotas/<assunto>.py` (sistema, acervo, playlists, youtube,
  discord); o canal de tempo real em `api/ws.py`.
- **Porta do Freddy: 47824**, só em `127.0.0.1`. O **Porteiro**
  (`api/porteiro.py`) confere TODO pedido, HTTP e WebSocket: Host só
  `127.0.0.1:<porta>`/`localhost:<porta>` (DNS rebinding) e, com Origin, só
  as origens de `config.py` (o painel). Sem isso, qualquer site aberto no
  navegador mexia no Freddy (POST "simples" não tem preflight de CORS). Rota
  nova já nasce protegida; nos testes, o `TestClient` usa
  `base_url="http://127.0.0.1:47824"` (e `WS` pro /ws). Link externo quem
  abre é o backend (`POST /abrir`, lista fechada de sites). Não abrir pra
  rede sem login (Fase 3).
- **Dados do mestre** (playlists, `ajustes.json` com as correções de
  nome/temas, `aprendidas.json` com as faixas novas, `discord.json`,
  `freddy.log`, o yt-dlp baixado) ficam na pasta do usuário
  (`~/.local/share/Freddy`, `%APPDATA%\Freddy`), nunca no repositório. O
  Freddy aplica os ajustes por cima do acervo ao servir `/acervo`; o
  `backend/scripts/acervo_promover.py` leva pro `acervo/musicas.json`.
  Categorias sempre saem dos temas (`nucleo/vocabulario.py`), nunca à mão.
- **Catálogo novo (o banco do Fredify):** fonte em CSV em `acervo/catalogo/`
  (README lá), compilado no `catalogo.db` (fora do git) por
  `freddy/catalogo/compilar.py`, que barra o que quebra as regras;
  `freddy/catalogo/consulta.py` entende o pedido. Ainda não ligado no app
  (etapa 4); até lá o app usa o `musicas.json`. Mexeu nos CSV: rodar
  `python -m unittest freddy.catalogo.test_catalogo` (pedidos de ouro).
- **Comandos só do painel no chat** (`temas`/`revisar` em
  `frontend/src/modos/chat/revisao.ts`; `playlists`/`toca a playlist X`/
  `salva a fila como X` em `playlistsChat.ts`) rodam antes do
  `navegador/pedido.ts`. Atenção: no `pedido`, "playlist" é palavra de
  "mostra a fila"; por isso os de playlist vêm antes. (Na etapa D o chat do
  painel passa a usar o `freddy/conversa/` e isso vai pro backend.)
- **Painel:** modos em `frontend/src/modos/<nome>/` (cada um com seu `.css`),
  entram pela lista em `modos/registro.tsx`. Conversa com o Freddy em
  `src/api/`; o que a tela guarda em `src/estado/`. CSS: `src/estilo/base.css`
  (comum), um `.css` por tela/componente, `telas-menores.css` por último
  (importado no `main.tsx` depois de tudo).
- **Temas (plumagens):** cores em `frontend/src/estilo/temas.css` (um bloco
  `[data-tema]` por tema, com `--acento` pra preencher e `--acento-texto`
  pra texto), lista em `frontend/src/estado/temas.ts`. O padrão é
  `frederico`. Arte em `frontend/public/aves/<tema>.png` e
  `<tema>-rosto.png`; tema sem arte usa a do Frederico.
- **App instalado serve o painel em `http://localhost:47823`**
  (`tauri-plugin-localhost`, ver `frontend/src-tauri/src/lib.rs`), porque o
  player do YouTube não toca em `tauri://`. Não trocar a porta: o
  localStorage (temas, playlists) é guardado por endereço.
- **O app liga o backend sozinho (sidecar):** o workflow empacota o backend
  com PyInstaller (`backend/freddy_backend.py` → `freddy-backend-<alvo>` em
  `frontend/src-tauri/binaries/`, fora do git), **liga o empacotado de
  verdade** (`/saude` e `/acervo`) e, no Windows, põe o `ffmpeg.exe` junto
  (`tauri.windows.conf.json`). O `lib.rs` só liga se a porta 47824 estiver
  livre (freddy.sh/`python -m freddy` continuam valendo), abre o painel com
  `?freddy=ligando` (aí o painel espera o backend acordar, até ~30 s) e
  passa `FREDDY_PAI`: o backend desliga sozinho se o app fechar ou cair.
  Empacotado, o log vai pro `freddy.log` na pasta do mestre. Dependência
  nova do backend que o PyInstaller não acha sozinho = flag no `app.yml`.

## Comandos

```bash
# painel no navegador, recarrega sozinho (o jeito normal de testar)
cd frontend && npm install && npm run dev        # http://localhost:5173

# o backend + o app, na ordem certa (Fedora: sudo dnf install ffmpeg-free portaudio opus)
./freddy.sh                 # --sem-som finge que toca
# ou só o backend: cd backend && pip install -r requirements.txt && python -m freddy

# testes (o GitHub roda todos antes de compilar, mais o ponta a ponta)
cd frontend && npm test && npm run build
cd backend && python -m unittest discover -s freddy -t .
python3 scripts/versao.py --conferir

# manutenção do acervo (de dentro de backend/): ver a skill chips
python scripts/acervo_promover.py --so-mostrar

# app desktop local (precisa de Rust e do backend empacotado em
# src-tauri/binaries/, ver o passo "Backend empacotado" do app.yml; raramente necessário)
cd frontend && npm run app
```

## Lançar versão nova do app

Ninguém compila no PC: o workflow `app.yml` compila e publica em Releases.
1. `python3 scripts/versao.py 0.5.6`: muda a versão nos 6 arquivos de uma
   vez (`--conferir` mostra; o GitHub falha se algum estiver diferente).
2. Commit e push no seu branch `claude/...`. O workflow roda em push em
   qualquer branch `claude/**` que mexa em `frontend/`, `backend/`,
   `scripts/` ou no workflow.
3. A Release `v<versão>` é criada pelo próprio GitHub (prerelease). Push na
   mesma versão só atualiza os arquivos dela.
4. Depois, leve o `main` junto: `git push origin HEAD:main`. O `main` é o
   branch principal do repositório (o que aparece pra quem abre o GitHub) e
   é só o espelho do que está pronto: push nele não compila de novo. O
   Marcelo é o único mestre e autorizou: não precisa de PR.

Nas sessões do Claude na nuvem, o proxy **não deixa subir tags** (403) e o
disparo manual do workflow só funciona com ele na branch principal: por isso
o gatilho por push no branch.

## O usuário

Marcelo, mestre de D&D (comunidade The Crossroads). Fala português informal;
responda em português do Brasil, direto e sem jargão. Usa **Fedora KDE**
(sem `apt`; pacote `.rpm` ou AppImage) e quer que os outros mestres, na
maioria no Windows, só baixem e usem, sem compilar nada.

## Segurança

`.env`, tokens de bot e `credentials.json` nunca vão pro git. Rodar
`git status` antes de cada commit.
