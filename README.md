# Projeto Frederico 🦜

> Nome de trabalho. O nome final (FredBOT, Freddy ou Fredérico) ainda não foi escolhido.

Uma aplicação de som inspirada no **Frederico**, a calopsita de verdade do
Marcelo, que ama música e barulho de todo tipo. No universo da
[Natty](https://github.com/Marcelao98/natty-bot) ele vira uma calopsita robô:
um dos robozinhos menores que a Natty comanda, o que cuida do som.

## De onde veio

O Freddy nasceu do módulo de música da Natty e veio com o histórico:
`git log` conta a história desde o começo.

**O Freddy é o áudio do Nattyverso:** a Natty não toca mais nada. Hoje ele é
um app que você baixa e abre:

- pede música em português ("toca triste e bloodborne"), num acervo de 607
  faixas marcadas por clima, ou busca livre no YouTube ("era essa?");
- Chat, Playlist (com playlists salvas pra cada sessão) e Acervo (arrumar
  as tags no painel, pelo chat ou numa planilha);
- toca na caixa de som ou numa call do Discord, pelo bot dele
  (guia em `docs/discord.md`), com `@Freddy toca...` no chat.

## Pra onde vai

O Frederico vai ser uma aplicação **local** (roda no PC de cada mestre) que
toca e mistura som, e o Discord é só uma das saídas:

- **Mixer em camadas:** música + ambiente (loops) + efeitos (pads), com volume
  por camada e ducking (a música abaixa quando um efeito toca ou quando você fala).
- **Microfone virtual:** soma o seu mic com o som e manda pra um microfone
  de mentira (no Linux o Freddy cria; no Windows, o VB-Cable). Discord, Zoom,
  Meet ou OBS usam como microfone, sem precisar de bot.
- **Cenas:** "Taverna" = música + ambiente + os pads, num clique.
- **Fontes:** arquivos locais, YouTube, playlists inteiras e Freesound
  (CC0 por padrão, com os créditos guardados).
- **Vários mestres no mesmo Freddy:** um bot só, rodando num PC de casa,
  cada mestre no seu servidor.

Por que local: bot de música público na nuvem cai (termos do YouTube e
bloqueio de IP de datacenter). No PC de cada um, é uso pessoal pra própria mesa.

O plano completo, fase por fase, está em [`ROADMAP.md`](ROADMAP.md); o guia pra quem for mexer no código (inclusive o Claude) está em [`CLAUDE.md`](CLAUDE.md).

## Como o repositório está dividido

```
acervo/     o acervo de músicas (musicas.json + vocabulario.json), lido pelos dois lados
frontend/   o painel (React + TypeScript) e o app desktop (Tauri, em Rust)
backend/    o Freddy (Python): fila, som, bot do Discord e as regras de música
docs/       ARQUITETURA.md (o desenho e as etapas) e discord.md (o bot)
scripts/    versao.py: a versão do app em todos os arquivos de uma vez
freddy.sh   pra desenvolver: liga o backend e abre o app na ordem certa
```

- **Frontend** ([`frontend/README.md`](frontend/README.md)): Chat, Playlist,
  Acervo e a janela do Discord, com cinco plumagens de calopsita.
- **Backend** ([`backend/README.md`](backend/README.md)): o servidor local
  (`backend/freddy/`) que o app liga sozinho.
- **Arquitetura** ([`docs/ARQUITETURA.md`](docs/ARQUITETURA.md)): o desenho,
  as pastas, as regras e as próximas etapas.

**Pra usar:** baixe o app na página **Releases** do GitHub e abra. Ele liga
o Freddy sozinho, sem terminal e sem Python instalado. No Fedora, o `.rpm`;
no Windows, o `-setup.exe`. **Pra desenvolver:** `./freddy.sh` (ver o
README do backend).

## Testes

```
python3 scripts/versao.py --conferir
cd backend && python -m unittest discover -s freddy -t .
cd frontend && npm test
```

Sem rede nem Discord de verdade (dublês).

## Licença

**GPL-3.0** (ver `LICENSE`). © 2026 Marcelo.

O Freddy é open source por natureza: pode usar, estudar, mudar e
redistribuir, desde que o que você distribuir também tenha o código aberto
sob a GPL-3.0. Partes adaptadas do [Kenku FM](https://github.com/owlbear-rodeo/kenku-fm)
(© Owlbear Rodeo, GPL-3.0) dizem isso no topo do arquivo.
