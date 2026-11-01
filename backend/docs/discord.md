# Discord: o bot do Freddy

O Freddy toca na call pelo bot dele: um bot só, compartilhado pelos mestres,
rodando dentro do `python -m freddy` (código em `backend/freddy/bot/`).

## Criar o bot (uma vez só)

1. Abra o [Discord Developer Portal](https://discord.com/developers/applications)
   e clique em **New Application**. Nome: *Freddy*. (Dá pra pôr a cara do
   Frederico como ícone: `frontend/src-tauri/icons/icon.png`.)
2. Na aba **Bot**, clique em **Reset Token** e copie o token. Ele é a senha
   do bot: não mande pra ninguém e nunca ponha no git.
3. Com o Freddy ligado, no painel: barra lateral → **Discord** → cole o
   token → **Conectar**. Fica guardado em `~/.local/share/Freddy/discord.json`
   (Windows: `%APPDATA%\Freddy\discord.json`), legível só por você. Quem
   preferir, usa a variável de ambiente `FREDDY_DISCORD_TOKEN`.
4. Na mesma janela: **Convidar pra um servidor** (ou **Copiar link** e abrir
   no navegador). O convite já pede as permissões certas: ver canais, enviar
   mensagens, ler o histórico, conectar e falar.

Não precisa ligar nenhum "Privileged Gateway Intent" no portal: mensagem que
menciona o bot chega com o texto mesmo sem o intent de conteúdo.

No Fedora, o Discord precisa da biblioteca Opus (quase sempre já está
instalada): `sudo dnf install opus`. No Windows ela vem junto com o discord.py.

## Usar

- **Pelo painel:** Discord → escolha o servidor e o canal de voz → o bot
  entra e toca a fila do painel. **Ouvir aqui também** faz o som da call sair
  na caixa do seu computador.
- **Pelo chat do Discord:** `@Freddy toca triste e bloodborne`, `@Freddy pula`,
  `@Freddy volume 30`, `@Freddy fila`, `@Freddy playlists`,
  `@Freddy toca a playlist sessão 12`, `@Freddy salva a fila como sessão 12`,
  `@Freddy sai`, `@Freddy ajuda`. Se o bot não estiver em call, ele entra na
  call de quem pediu. Ele avisa no canal quando a fila anda ("Tocando agora…").
- **Uma fila só:** o que se pede no Discord aparece no painel (o narrador do
  chat conta) e vice-versa.
- **Sozinho na call por 5 minutos** → ele sai e avisa.
- **Uma call por vez** (por enquanto). Várias mesas ao mesmo tempo é a Fase 3.

## Como funciona

```
Mesa (freddy/audio/mesa.py)  ──read() a cada 20 ms──▶  SaidaDiscord (bot/saida.py)  ──▶  discord.py (Opus) ──▶ call
   │
   └─ cópia (se "ouvir aqui") ──▶ caixa de som (audio/saidas.py)
```

- `bot/bot.py` (`BotDoFreddy`): conecta, lista servidores e canais de voz
  (na ordem do Discord), entra/sai da call, recebe as menções, avisa o
  painel (`ao_mudar` → mensagem `"discord"` no `/ws`).
- `bot/saida.py` (`SaidaDiscord`): o `discord.AudioSource`. O `read()` nunca
  devolve vazio (silêncio quando nada toca), então o player do discord.py
  nunca para: trocar de música não mexe no Discord, só na Mesa.
- `bot/conversa.py` (`Conversa`): texto do Discord → comando no mesmo `Motor`
  do painel → resposta. As regras de pedido são as do Bardo
  (`service.interpretar_pedido`); playlists, iguais ao chat do painel. Sem
  discord.py: testado direto em `bot/test_bot.py`.
- **Um relógio só:** com o bot numa call, quem puxa a Mesa é o Discord; a
  caixa de som toca uma cópia do que foi pra call. Sem isso a música andaria
  em dobro.
- **API:** `GET /discord`, `PUT/DELETE /discord/token`, `POST /discord/religar`,
  `POST /discord/entrar` `{canalId}`, `POST /discord/sair`,
  `PUT /discord/ouvir-aqui` `{ligado}`. Ids do Discord vão como texto (o
  JavaScript estraga número desse tamanho).

## O que veio do Kenku FM

O jeito de conectar foi adaptado do [Kenku FM](https://github.com/owlbear-rodeo/kenku-fm)
(`src/main/broadcast/DiscordBroadcast.ts`, © Owlbear Rodeo, GPL-3.0; o
Freddy também é GPL-3.0). Como o Kenku é JavaScript (discord.js) e o Freddy é
Python (discord.py), o que veio foi a lógica, reescrita:

- token colado no app, intents mínimos (servidores e estados de voz);
- ao conectar, a lista de servidores e canais de voz pro app escolher;
- um player só que nunca para (lá: `noSubscriber: Play` e 60 s de tolerância);
- um som contínuo de 48 kHz estéreo em quadros de 20 ms (lá: o mix do
  `AudioContext`; aqui: a Mesa);
- a saída "local" (loopback) tocando o mesmo som na caixa;
- erro de conexão vira aviso no app.

Onde o Freddy é diferente: um bot compartilhado (o Kenku é um bot por
pessoa); o chat do Discord manda na mesma fila do painel; o som vem direto do
YouTube via yt-dlp + FFmpeg (o Kenku captura o áudio de abas de navegador);
o bot sai sozinho da call vazia.

## Problemas comuns

- **"token inválido"**: gere outro em Bot → Reset Token e cole de novo.
- **"o bot não tem permissão de entrar e falar"**: no Discord, dê ao cargo
  do bot (ou no canal) as permissões Conectar e Falar.
- **"falta a biblioteca Opus"**: `sudo dnf install opus` (Fedora).
- **O botão de convite não abre nada no app**: use **Copiar link** e cole no
  navegador.
- **"Agora estou tocando em outro servidor"**: é uma call por vez; tire o
  bot de lá (painel ou `@Freddy sai`) antes.
