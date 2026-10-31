# Projeto Frederico (Freddy)

O som da mesa de RPG. O mestre pede música em português ("toca triste e
bloodborne"), o Freddy toca, e tudo é controlado por um painel com a cara do
Frederico, a calopsita de verdade do Marcelo (cara-branca, asa prateada,
olho preto, bico rosado). Nasceu do **Bardo**, o módulo de música da Natty
(repositório `Marcelao98/natty-bot`).

**Leia o `ROADMAP.md` antes de começar**: ele diz o que está pronto, a fase
atual e as decisões já tomadas.

## Como o repositório está dividido

```
frontend/   painel React + TypeScript (Vite), empacotado em app desktop com Tauri 2
backend/    Python: o Freddy (backend/freddy: FastAPI + WebSocket + áudio),
            o Bardo (discord.py + yt-dlp + FFmpeg) e o acervo
.github/workflows/app.yml   testa, compila Windows/Linux/Mac e publica a Release
ROADMAP.md  fases e decisões
```

Detalhes de cada lado em `frontend/README.md` e `backend/README.md`.

## Regras de arquitetura (não quebrar)

- **Acervo é um só:** `backend/modules/bardo/dataset/` (`musicas.json` +
  `vocabulario.json`). O frontend importa esses JSON direto (alias
  `@dataset` no `frontend/vite.config.ts`). Não copiar, não mover sem
  atualizar o alias.
- **Paridade TS ↔ Python:** `frontend/src/nucleo/pedido.ts` e `busca.ts` são
  portas fiéis de `interpretar_pedido` e `buscar_por_tags` do
  `backend/modules/bardo/service.py`. Mudou uma regra num, muda no outro, e
  os testes dos dois lados. O `freddy` importa as regras do Bardo (não copia).
- **O contrato `Motor`** (`frontend/src/motor/tipos.ts`) é a costura com o
  backend: as telas só chamam `motor.executar({ tipo: ... })` e leem o
  estado. Dois motores no painel: `MotorLocal` (toca pelo player do YouTube
  no navegador) e `MotorRemoto` (WebSocket pro `python -m freddy`); o
  `frontend/src/main.tsx` escolhe (Freddy ligado = remoto). No backend, o
  `backend/freddy/motor/motor.py` é a porta fiel do `MotorLocal`.
  **Comando novo** = entrada em `Comandos` + os DOIS motores + validação em
  `backend/freddy/api/protocolo.py` + um caso em
  `backend/freddy/motor/casos_contrato.json` (rodado pelos testes dos dois
  lados, alias `@contrato` no frontend).
- **Backend do Freddy** (`backend/freddy/`): `motor/` é lógica pura (sem rede
  nem áudio, testa com `ReprodutorFalso`); `api/` só traduz HTTP/WebSocket ↔
  motor; `audio/` é yt-dlp → FFmpeg → `Mesa` → saída. A Mesa entrega quadros
  de 20 ms, 48 kHz, estéreo, 16 bits: o formato do Discord (Fase 2) e a base
  do mixer (Fase 4). Avisos do áudio pro motor passam por `agendar` (o loop
  do servidor): o motor roda numa thread só.
- **Porta do Freddy: 47824**, só em `127.0.0.1`, e o `/ws` só aceita as
  origens de `backend/freddy/config.py` (o painel). Não abrir pra rede sem
  login (Fase 3).
- **Dados do mestre** (playlists, faixas aprendidas pelo "era essa?") ficam na
  pasta do usuário (`~/.local/share/Freddy`, `%APPDATA%\Freddy`), nunca no
  repositório. Aprendidas vão pro acervo oficial pelo
  `backend/scripts/freddy_promover_aprendidas.py`.
- **Modos do painel** moram em `frontend/src/modos/<nome>/` e entram pela
  lista em `frontend/src/modos/registro.tsx`.
- **No backend, a regra da Natty vale:** `service.py` é lógica pura, sem
  discord.py; `cog.py` só traduz Discord ↔ service.
- **Temas (plumagens):** cores em `frontend/src/temas.css` (um bloco
  `[data-tema]` por tema, com `--acento` pra preencher e `--acento-texto`
  pra texto), lista em `frontend/src/dados/temas.ts`. O padrão é
  `frederico`. Arte em `frontend/public/aves/<tema>.png` e
  `<tema>-rosto.png`; tema sem arte usa a do Frederico.
- **App instalado serve o painel em `http://localhost:47823`**
  (`tauri-plugin-localhost`, ver `frontend/src-tauri/src/lib.rs`), porque o
  player do YouTube não toca em `tauri://`. Não trocar a porta: o
  localStorage (temas, playlists) é guardado por endereço.

## Comandos

```bash
# painel no navegador, recarrega sozinho (o jeito normal de testar)
cd frontend && npm install && npm run dev        # http://localhost:5173

# o backend (Fedora: sudo dnf install ffmpeg-free portaudio)
cd backend && pip install -r requirements.txt && python -m freddy   # --sem-som finge que toca

# testes (o GitHub roda todos antes de compilar, mais o ponta a ponta)
cd frontend && npm test && npm run build
cd backend && python -m unittest discover -s modules/bardo -t .
cd backend && python -m unittest discover -s freddy -t .

# app desktop local (precisa de Rust; raramente necessário)
cd frontend && npm run app
```

## Lançar versão nova do app

Ninguém compila no PC: o workflow `app.yml` compila e publica em Releases.
1. Suba `version` em `frontend/package.json`, `frontend/src-tauri/tauri.conf.json`
   e `frontend/src-tauri/Cargo.toml` (e rode `cargo update -p freddy --offline`
   pra atualizar o `Cargo.lock`).
2. Commit e push. O workflow roda em push no branch de desenvolvimento que
   mexa em `frontend/`, `backend/` ou no workflow (ver `branches:` no
   `app.yml`; depois do merge na main, trocar pra `main`).
3. A Release `v<versão>` é criada pelo próprio GitHub (prerelease).

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
