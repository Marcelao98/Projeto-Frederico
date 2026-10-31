# Backend do Freddy

Python. Duas peças:

- **`freddy/`**: o Freddy rodando sozinho, sem a Natty (`python -m freddy`).
  Servidor local (FastAPI + WebSocket) que o painel usa pelo `MotorRemoto`:
  a fila mora aqui, o som sai daqui (yt-dlp + FFmpeg + caixa de som), e o
  acervo e as playlists também.
- **`modules/bardo/`**: o Bardo, o módulo de música da Natty (Cog de
  discord.py). É dele que o Freddy reaproveita as regras (pedidos, busca no
  acervo, YouTube). Na Fase 2 o Cog vira o bot do Freddy.

## Ligar o Freddy

### Fedora

```bash
sudo dnf install ffmpeg-free portaudio python3-pip
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m freddy
```

O `ffmpeg-free` do Fedora basta: o Freddy pede áudio Opus ao YouTube, que
ele toca sem o RPM Fusion.

### Windows

Instale o Python 3.12+ (python.org, marcando "Add to PATH") e o FFmpeg
(`winget install ffmpeg`). Depois, no PowerShell:

```powershell
cd backend
python -m venv .venv; .venv\Scripts\activate
pip install -r requirements.txt
python -m freddy
```

(Na Fase 6 o app passa a trazer o backend junto: ninguém vai precisar disso.)

### Usando

Com o Freddy ligado, abra o painel (o app instalado ou `npm run dev`). Ele
acha o Freddy sozinho e mostra **"Este computador · pelo Freddy"** na barra
lateral. Desligado, o painel toca pelo navegador como antes. Clicar nessa
linha alterna entre os dois.

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
├── config.py          porta (47824), pastas, quem pode conectar
├── motor/
│   ├── fila.py        porta fiel de frontend/src/motor/fila.ts
│   ├── motor.py       porta fiel do MotorLocal: comandos, estado, eventos
│   └── casos_contrato.json   casos rodados pelos testes dos DOIS lados
├── audio/
│   ├── pcm.py         o formato: 48 kHz, estéreo, 16 bits, quadros de 20 ms (o do Discord)
│   ├── youtube.py     link → áudio (yt-dlp), erros em português
│   ├── fonte_ffmpeg.py  FFmpeg decodificando um link em quadros
│   ├── mesa.py        onde o som é montado (hoje uma camada; mixer na Fase 4)
│   ├── saidas.py      caixa de som (sounddevice), muda; Discord na Fase 2
│   ├── reprodutor_mesa.py   o Reprodutor de verdade
│   └── reprodutor_falso.py  pros testes e o --sem-som
├── api/
│   ├── app.py         FastAPI: REST + /ws
│   ├── protocolo.py   as mensagens do WebSocket (validadas)
│   └── paineis.py     os painéis conectados (todos veem a mesma fila)
└── dados/
    ├── acervo.py      dataset do repositório + aprendidas.json
    └── playlists.py   playlists.json
```

**Regras:** o `motor/` não sabe de rede nem de áudio (testa com o reprodutor
falso). O `api/` só traduz WebSocket/HTTP ↔ motor, como o `cog.py` faz com o
Discord. Comando novo no motor = os dois motores (Python e TypeScript), a
validação em `protocolo.py` e um caso em `casos_contrato.json`.

## A API (porta 47824, só neste computador)

| Rota | Para quê |
|---|---|
| `GET /saude` | o painel descobre se o Freddy está ligado |
| `WS /ws` | o motor: comandos, estado, progresso e eventos (ver `api/protocolo.py`) |
| `GET /acervo` | `{musicas, vocabulario}`: o dataset + as faixas aprendidas |
| `POST /acervo/faixas` | `{titulo, link, temas}`: ensina faixa nova ("era essa?") |
| `GET /playlists`, `PUT /playlists/{id}`, `DELETE /playlists/{id}` | playlists salvas |
| `GET /youtube/info?link=` | título e duração de um link |
| `POST /youtube/buscar` | `{texto}`: busca livre no YouTube |

O servidor só escuta `127.0.0.1` e só aceita o painel (confere a origem):
um site qualquer aberto no navegador não consegue mexer na fila.

## O acervo

`modules/bardo/dataset/` (`musicas.json` + `vocabulario.json`) é a fonte
única: o frontend importa os mesmos JSON (alias `@dataset` em
`frontend/vite.config.ts`). Mover ou renomear essa pasta quebra o frontend.

O que a mesa ensina pelo "era essa?" vai pro `aprendidas.json` do mestre
(quem baixou o app não tem o repositório). Pra levar pro acervo oficial:

```bash
python scripts/freddy_promover_aprendidas.py --so-mostrar   # ver o que tem
python scripts/freddy_promover_aprendidas.py                # levar, e revisar o git diff
```

## Testes

Todos os comandos rodam **de dentro de `backend/`**:

```bash
python -m unittest discover -s modules/bardo -t .   # o Bardo
python -m unittest discover -s freddy -t .          # o Freddy (sem internet nem caixa de som)
```

Os testes de áudio geram um tom com o FFmpeg (pulam se ele não estiver
instalado). O GitHub roda tudo isso e mais um teste de ponta a ponta: o
`MotorRemoto` do painel falando com `python -m freddy --teste` pela rede.

## Discord

O estudo de como o Kenku FM fala com o Discord, e o plano da Fase 2, estão
em [`docs/discord.md`](docs/discord.md).
