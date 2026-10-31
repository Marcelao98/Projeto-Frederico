# Projeto Frederico 🦜

> Nome de trabalho. O nome final (FredBOT, Freddy ou Fredérico) ainda não foi escolhido.

Uma aplicação de som inspirada no **Frederico**, a calopsita de verdade do
Marcelo, que ama música e barulho de todo tipo. No universo da
[Natty](https://github.com/Marcelao98/natty-bot) ele vira uma calopsita robô:
um dos robozinhos menores que a Natty comanda, o que cuida do som.

## De onde veio

O código foi roubado, com carinho e com histórico, do **Bardo**, o módulo de
música da Natty (`backend/modules/bardo/`). Ele já sabe:

- tocar link do YouTube ou buscar por tema no dataset (~585 faixas com tags,
  em `backend/modules/bardo/dataset/`)
- busca livre no YouTube com aprendizado ("era essa? me diz uns temas")
- fila por servidor, repetir, volume, pausa, pular e reconexão automática

Os commits do Bardo vieram junto (extraídos da natty-bot com
`git filter-repo`), então `git log` conta a história desde o começo.

**O Freddy é o áudio do Nattyverso:** a Natty não toca mais nada. Hoje ele
já roda sozinho no PC (`python -m freddy`, em `backend/freddy/`): o painel
manda nele, ele toca na caixa de som. O bot do Discord do Freddy é a Fase 2.

## Pra onde vai

O Frederico vai ser uma aplicação **local** (roda no PC de cada mestre) que
toca e mistura som, e o Discord é só uma das saídas:

- **Mixer em camadas:** música + ambiente (loops) + efeitos (pads), com volume
  por camada e ducking (a música abaixa quando um efeito toca ou quando você fala).
- **Microfone virtual:** soma o seu mic com o som e manda pra um cabo virtual
  (VB-Cable). Discord, Zoom, Meet ou OBS usam como microfone, sem precisar de bot.
- **Painel web local** (localhost) como controle remoto, com playlists e cenas salvas.
- **Fontes:** arquivos locais, YouTube, playlists inteiras e Freesound
  (CC0 por padrão, com os créditos guardados).
- **Bot de Discord do Freddy** (Fase 2): um bot só, compartilhado pelos
  mestres, rodando num PC de casa. O som nunca passa pela Natty.

Por que local: bot de música público na nuvem cai (termos do YouTube e
bloqueio de IP de datacenter). No PC de cada um, é uso pessoal pra própria mesa.

O plano completo, fase por fase, está em [`ROADMAP.md`](ROADMAP.md); o guia pra quem for mexer no código (inclusive o Claude) está em [`CLAUDE.md`](CLAUDE.md).

## Como o repositório está dividido

```
frontend/   o painel: React + TypeScript, empacotado como app desktop (Tauri)
backend/    o som: hoje o Bardo (Python, Discord), com o acervo de faixas
```

- **Frontend** ([`frontend/README.md`](frontend/README.md)): modo **Chat**
  (pedidos em português, sem comando decorado) e modo **Playlist** (monta a fila
  e salva), com cinco plumagens de calopsita como tema. Toca pelo Freddy
  (backend) se ele estiver ligado; senão, pelo player do YouTube.
- **Backend** ([`backend/README.md`](backend/README.md)): o Freddy
  (`backend/freddy/`: servidor local, fila, som), o Bardo e o acervo
  (`backend/modules/bardo/dataset/`). O frontend lê esse mesmo acervo.

**Pra usar:** baixe o app pronto na página **Releases** do GitHub (Windows,
Linux e Mac), sem compilar nada. Pra desenvolver: `cd frontend && npm install
&& npm run app` (precisa de Node e Rust; ver o README do frontend).

## Testes

```
cd backend && python -m unittest discover -s modules/bardo -t .
cd backend && python -m unittest discover -s freddy -t .
cd frontend && npm test
```

Sem rede nem Discord de verdade (dublês).

## Licença

MIT (ver `LICENSE`). Repositório privado por enquanto; a licença será
revisada antes de abrir.
