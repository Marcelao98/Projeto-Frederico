# Backend do Freddy

Python:

- **`freddy/`**: o Freddy (`python -m freddy`, ou dentro do app instalado).
  Servidor local (FastAPI + WebSocket) que o painel usa pelo `MotorRemoto`:
  a fila mora aqui, o som sai daqui (yt-dlp + FFmpeg + caixa de som), e o
  acervo e as playlists também.
  Inclui as regras de música (`freddy/nucleo/`) e o bot do Discord
  (`freddy/integracoes/discord/`, guia em [`docs/discord.md`](../docs/discord.md)).
- **`scripts/`**: manutenção do acervo (`acervo_*.py`).

O acervo mora fora daqui, em `acervo/` na raiz: o painel lê os mesmos arquivos.

## Usar (sem programar)

Baixe o app nas Releases e abra: ele traz este backend empacotado e liga
sozinho, sem terminal e sem Python instalado. O log fica em `freddy.log`,
na pasta do Freddy (abaixo).

## Ligar pelo código (pra desenvolver)

### Fedora

```bash
sudo dnf install ffmpeg-free portaudio opus python3-pip   # uma vez (quem já tem o ffmpeg do RPM Fusion, pula o ffmpeg-free)
~/Projeto-Frederico/freddy.sh
```

O `freddy.sh` (na raiz do repositório) faz tudo na ordem certa: prepara o
Python na primeira vez (e quando o `requirements.txt` muda), liga o backend,
espera ele responder e só então abre o app. Ctrl+C desliga tudo.
`freddy.sh --sem-som` finge que toca.

O `ffmpeg-free` do Fedora basta: o Freddy pede áudio Opus ao YouTube, que
ele toca sem o RPM Fusion.

### Windows (só pra desenvolver; pra usar, é o app)

Instale o Python 3.12+ (python.org, marcando "Add to PATH") e o FFmpeg
(`winget install ffmpeg`). Depois, no PowerShell:

```powershell
cd backend
python -m venv .venv; .venv\Scripts\activate
pip install -r requirements.txt
python -m freddy
```

### Usando

Com o Freddy ligado, abra o painel (o app instalado ou `npm run dev`). Ele
acha o Freddy sozinho (espera uns 3 s, caso ele esteja acabando de ligar) e
mostra **"Este computador · pelo Freddy"** na barra lateral. Desligado, o
painel toca pelo navegador como antes; se o Freddy ligar depois, aparece
"O Freddy ligou. Usar ele?". Clicar na linha "Este computador" alterna
entre os dois.

```
python -m freddy               toca na caixa de som
python -m freddy --sem-som     finge que toca (testar o painel sem som nem internet)
python -m freddy --porta 47900 outra porta (o painel procura na 47824)
python -m freddy -v            mostra mais coisa no terminal
```

Playlists e faixas aprendidas ficam em `~/.local/share/Freddy/` (Linux) ou
`%APPDATA%\Freddy\` (Windows). `FREDDY_PASTA` ou `--pasta` trocam o lugar.

## Como o Freddy está organizado

```
freddy/
├── __main__.py        python -m freddy
├── config.py          porta (47824), pastas, PASTA_ACERVO, quem pode conectar
├── nucleo/            as regras, lógica pura (sem rede, som ou Discord)
│   ├── texto.py       normalizar, slug, links do YouTube
│   ├── pedido.py      "toca triste e bloodborne", "pula", "volume 30"
│   ├── vocabulario.py temas → as 27 categorias
│   └── busca.py       busca booleana (e / ou / sem) e o sorteio de 15
├── conversa/
│   └── cerebro.py     "@Freddy toca…" → o mesmo motor do painel → resposta
├── salas/
│   ├── motor.py       porta fiel do MotorLocal: comandos, estado, eventos
│   ├── fila.py        a fila
│   └── casos_contrato.json   casos rodados pelos testes dos DOIS lados
├── audio/
│   ├── pcm.py         o formato: 48 kHz, estéreo, 16 bits, quadros de 20 ms (o do Discord)
│   ├── mesa.py        onde o som é montado (um relógio só: o Discord ou a caixa)
│   ├── reprodutor_mesa.py   o Reprodutor de verdade; reprodutor_falso.py pros testes
│   ├── fontes/        youtube.py (yt-dlp), ytdlp.py (se atualiza no app), ffmpeg.py, assobio.py
│   └── saidas/        caixa.py (sounddevice), discord.py (a call), muda.py
├── integracoes/discord/
│   └── bot.py         conecta, lista canais, entra na call, ouve "@Freddy"
├── dados/
│   ├── acervo.py      o acervo + ajustes.json + aprendidas.json (do mestre)
│   ├── acervo_oficial.py   ler/formatar/acrescentar no acervo/musicas.json
│   ├── planilha.py    o acervo em CSV, ida e volta
│   ├── playlists.py   playlists.json
│   ├── segredos.py    o token do bot (discord.json, só o dono lê)
│   └── arquivos.py    gravar sem corromper
└── api/
    ├── app.py         monta as peças (app.state) e liga as rotas
    ├── porteiro.py    só o painel entra
    ├── ws.py          o canal de tempo real (/ws)
    ├── protocolo.py   as mensagens do /ws (validadas)
    ├── paineis.py     os painéis conectados (todos veem a mesma fila)
    └── rotas/         sistema, acervo, playlists, youtube, discord
```

**Regras:** `nucleo/` e `salas/` não sabem de rede nem de som (testam com o
reprodutor falso). `api/` e `integracoes/` só traduzem (HTTP/WebSocket,
Discord) pro motor e pra `conversa/`. Comando novo no motor = os dois
motores (Python e TypeScript), a validação em `protocolo.py` e um caso em
`casos_contrato.json`. O desenho inteiro: [`docs/ARQUITETURA.md`](../docs/ARQUITETURA.md).

## A API (porta 47824, só neste computador)

| Rota | Para quê |
|---|---|
| `GET /saude` | o painel descobre se o Freddy está ligado (e a versão do yt-dlp) |
| `POST /abrir` | `{url}`: abre no navegador do sistema (só Discord e o GitHub do Freddy) |
| `GET /diagnostico` | o que está indo pra call (Discord) |
| `WS /ws` | o motor: comandos, estado, progresso e eventos (ver `api/protocolo.py`) |
| `GET /acervo` | `{musicas, vocabulario}`: o acervo + os ajustes e as faixas aprendidas |
| `POST /acervo/faixas` | `{titulo, link, temas}`: ensina faixa nova ("era essa?") |
| `PATCH /acervo/faixas/{id}` | `{nome?, temas?, comentario?}`: corrige uma faixa (categorias recalculadas) |
| `GET /acervo/planilha` | o acervo em CSV (`;`, com acentos certos pro Excel) |
| `POST /acervo/planilha/salvar` | salva o CSV na pasta Downloads (o jeito que funciona no app) |
| `POST /acervo/planilha?aplicar=` | manda o CSV editado: sem `aplicar`, só o resumo do que muda |
| `GET /playlists`, `PUT /playlists/{id}`, `DELETE /playlists/{id}` | playlists salvas |
| `GET /discord`, `PUT/DELETE /discord/token`, `POST /discord/religar` | o bot: situação, servidores e canais; guardar/esquecer o token |
| `POST /discord/entrar`, `POST /discord/sair`, `PUT /discord/ouvir-aqui` | entrar na call, sair, ouvir a call na caixa |
| `GET /youtube/info?link=` | título e duração de um link |
| `POST /youtube/buscar` | `{texto}`: busca livre no YouTube |

O servidor só escuta `127.0.0.1`, e o **Porteiro** (`api/porteiro.py`)
confere todo pedido, HTTP e WebSocket: o endereço tem que ser
`127.0.0.1:<porta>` ou `localhost:<porta>` (contra "DNS rebinding") e, se
veio de navegador, a origem tem que ser o painel (`config.py`). Um site
qualquer aberto no navegador não consegue mexer no Freddy. Programas locais
(sem origem, como o `curl`) passam.

## O acervo

`acervo/` na raiz do repositório (`musicas.json` + `vocabulario.json`) é a
fonte única: o backend acha por `config.PASTA_ACERVO` e o painel importa os
mesmos JSON (alias `@acervo` em `frontend/vite.config.ts`). No app
empacotado, o acervo vai junto do executável. Pra acrescentar uma franquia:
a skill `chips`.

O que o mestre muda fica na pasta dele (quem baixou o app não tem o
repositório):
- `ajustes.json`: correções nas faixas do acervo (nome, temas, comentário),
  feitas pelo chat (`temas`, `revisar`), pelo modo Acervo ou pela planilha.
  Só guarda o que difere do acervo oficial; voltar ao original apaga o ajuste.
- `aprendidas.json`: faixas novas ("era essa?" ou linha nova na planilha).

As categorias sempre saem dos temas (`acervo/vocabulario.json`). Pra levar tudo pro
acervo oficial (e os outros mestres ganharem junto na próxima versão):

```bash
python scripts/acervo_promover.py --so-mostrar   # ver o que tem
python scripts/acervo_promover.py                # levar, e revisar o git diff
```

## Testes

Todos os comandos rodam **de dentro de `backend/`**:

```bash
python -m unittest discover -s freddy -t .   # tudo (sem internet nem caixa de som)
```

Os testes de áudio geram um tom com o FFmpeg (pulam se ele não estiver
instalado). O GitHub roda tudo isso e mais um teste de ponta a ponta: o
`MotorRemoto` do painel falando com `python -m freddy --teste` pela rede.

## Discord

Criar o bot, usar e como funciona (inclusive o que veio do Kenku FM):
[`docs/discord.md`](../docs/discord.md).
