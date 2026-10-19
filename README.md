# Projeto Frederico 🦜

> Nome de trabalho. O nome final (FredBOT, Freddy ou Fredérico) ainda não foi escolhido.

Uma aplicação de som inspirada no **Frederico**, a calopsita de verdade do
Marcelo, que ama música e barulho de todo tipo. No universo da
[Natty](https://github.com/Marcelao98/natty-bot) ele vira uma calopsita robô:
um dos robozinhos menores que a Natty comanda, o que cuida do som.

## De onde veio

O código foi roubado, com carinho e com histórico, do **Bardo**, o módulo de
música da Natty (`modules/bardo/`). Ele já sabe:

- tocar link do YouTube ou buscar por tema no dataset (~585 faixas com tags,
  em `modules/bardo/dataset/`)
- busca livre no YouTube com aprendizado ("era essa? me diz uns temas")
- fila por servidor, repetir, volume, pausa, pular e reconexão automática

Os commits do Bardo vieram junto (extraídos da natty-bot com
`git filter-repo`), então `git log` conta a história desde o começo.

**Hoje** o código ainda é o Bardo como ele é na Natty: um Cog de discord.py,
sem bot próprio. Ele não roda sozinho ainda.

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
- **Bot de Discord** (depois): a Natty, na nuvem, manda o Frederico tocar pela
  convenção 🎙 (ver `CLAUDE.md` da natty-bot). A Natty nunca toca áudio, e o
  Frederico nunca sai do PC de quem roda.

Por que local: bot de música público na nuvem cai (termos do YouTube e
bloqueio de IP de datacenter). No PC de cada um, é uso pessoal pra própria mesa.

## Testes

```
python -m unittest discover -s modules/bardo -t .
```

Sem rede nem Discord de verdade (dublês).

## Licença

MIT (ver `LICENSE`). Repositório privado por enquanto; a licença será
revisada antes de abrir.
