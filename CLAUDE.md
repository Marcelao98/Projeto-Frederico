# Frederico

Aplicação local de som: toca música (catálogo, YouTube, arquivos) por cima do
microfone e manda pra um mic virtual (VB-Cable). Nasceu do Bardo, o módulo de
música da Natty (https://github.com/Marcelao98/natty-bot). Nome final ainda
não escolhido: "Frederico" é codinome, não crie nada público com nome definitivo.

## Regras

- **O núcleo não importa discord.py.** `service.py`, `player.py`, `fonte.py`,
  `mixer.py`, `audio.py` e `web.py` são independentes de Discord. Qualquer
  interface (painel, bot, linha de comando) só chama o `Player`.
- `frederico/discord_pendente/` é o cog antigo do Bardo, parado. Não carrega
  em lugar nenhum; fica de referência pro bot que vem depois.
- Roda **local**, no PC de quem usa (YouTube bloqueia IP de datacenter e bot
  de música público cai). Nunca pensar em hospedar na nuvem.
- O callback de áudio (`Motor.processar`, `Player.ler`) nunca espera rede nem
  disco: o que demora roda em outra thread.
- O painel escuta só em 127.0.0.1 e confere o Host.

## Testes

```
python -m unittest discover -s frederico -t .
```

Sem rede nem placa de som (dublês). A nuvem não tem placa de som nem acesso
ao YouTube: ouvir de verdade é com o Marcelo, no Windows.

## Segurança

`.env`, `credentials.json` e `config_local.json` não vão pro git. Rodar
`git status` antes de commitar.

## Diário

`DIARIO.md`: uma entrada por sessão de trabalho (o que foi feito, decidido e
o que falta).
