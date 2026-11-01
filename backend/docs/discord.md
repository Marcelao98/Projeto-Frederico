# Discord: como o Kenku FM faz, e o plano do Freddy (Fase 2)

Estudo do [Kenku FM](https://github.com/owlbear-rodeo/kenku-fm) (v1.5.5), o
app de som para RPG que mais se parece com o Freddy, para decidir a Fase 2.

> **Licença:** o Kenku e o Freddy são GPL-3.0, então dá pra adaptar o código
> de lá. Arquivo que adaptar código do Kenku diz no topo de onde veio
> ("adaptado do Kenku FM, © Owlbear Rodeo, GPL-3.0"). Como o Kenku é
> JavaScript e o Freddy é Python, na prática o que vem é a lógica, reescrita.

## Como o Kenku fala com o Discord

Electron + `discord.js` + `@discordjs/voice`. O arquivo central é
`src/main/broadcast/DiscordBroadcast.ts`.

1. **Cada pessoa cria o próprio bot** no Discord Developer Portal e cola o
   token nas configurações do app (eles têm um guia: "getting a discord token").
2. **Intents mínimos:** só `Guilds` e `GuildVoiceStates`. O bot não lê
   mensagem nenhuma: é controlado só pelo app.
3. **Lista de servidores e canais:** quando o bot conecta, o app busca os
   servidores dele e os canais de voz de cada um (na ordem do Discord) e
   mostra numa lista de **saídas**: "Local" ou um canal de voz.
4. **Um player só, que nunca para:** um `AudioPlayer` com
   `noSubscriber: Play` (segue tocando mesmo sem ninguém ouvindo) e
   `maxMissedFrames: 3000` (aguenta 60 s de buraco sem desistir).
5. **Um som contínuo, não uma faixa por vez.** Tudo o que toca no app (abas
   de navegador embutidas, playlists, soundboard, até um microfone) é
   misturado num `AudioContext` a **48 kHz estéreo**. Um `AudioWorklet`
   converte em **PCM 16 bits** e manda por um WebSocket interno para o
   processo principal, que codifica em **Opus em quadros de 20 ms** (960
   amostras) e entrega ao player como um recurso só.
6. **Entrar e sair do canal:** `joinVoiceChannel` + `connection.subscribe(player)`;
   sair é destruir a conexão daquele servidor. Erro de conexão vira aviso na tela.
7. **Saída "Local":** o mesmo mix tocando na caixa de som (loopback).
8. **Controle remoto:** uma API HTTP local (fastify) para Stream Deck e afins.
9. **Criptografia de voz (DAVE):** usam `@snazzah/davey`. O Discord passou a
   exigir criptografia ponta a ponta nas calls; o Bardo já tem o `davey` no
   `requirements.txt`.

## O que o Freddy já tem igual

A Fase 1 foi feita pensando nisso: a **Mesa** (`freddy/audio/mesa.py`) é o
"mix contínuo" do Kenku. Ela entrega quadros de **20 ms, 48 kHz, estéreo,
16 bits** (3840 bytes), exatamente o que o `discord.AudioSource.read()` do
discord.py pede. A caixa de som (`SaidaLocal`) já puxa da Mesa; o Discord vai
ser só mais uma saída.

Diferença boa: o Kenku precisa de um navegador escondido para capturar o som
das abas. O Freddy decodifica direto (yt-dlp + FFmpeg), sem navegador.

## Onde o Freddy é diferente (decisões tomadas)

| | Kenku | Freddy |
|---|---|---|
| Bot | cada pessoa cria o seu e cola o token | **um bot compartilhado**: o token fica só no backend (`.env`); os mestres não mexem em token |
| Quem controla | só o app | o painel **e** o chat do Discord (`@Freddy toca ...`, como o Bardo) |
| Calls ao mesmo tempo | uma (um player global) | uma por servidor (Fase 3); na Fase 2, uma basta |
| Sistemas | Windows, Mac, Linux | Linux e Windows primeiro |

Consequências do bot compartilhado: login no painel pela conta do Discord e
permissão por cargo (Fase 3); e como um bot só fica em **um canal de voz por
servidor**, duas mesas no mesmo servidor precisam de um "pool" de bots.

## Esboço da Fase 2

```python
class SaidaDiscord(discord.AudioSource):
    """O Discord puxa um quadro de 20 ms a cada 20 ms: é só entregar o da Mesa."""

    def __init__(self, mesa: Mesa):
        self.mesa = mesa

    def read(self) -> bytes:
        return self.mesa.ler(BYTES_POR_QUADRO)  # nunca vazio: silêncio quando não toca

    def is_opus(self) -> bool:
        return False  # o discord.py codifica em Opus
```

- `voice_client = await canal.connect()` e `voice_client.play(SaidaDiscord(mesa))`,
  uma vez só ao entrar no canal. Trocar de música não mexe no Discord: só na
  Mesa. Como o `read()` nunca devolve vazio, o player não para sozinho (o
  equivalente ao `noSubscriber: Play` do Kenku).
- **API nova:** `GET /discord/servidores` → `[{id, nome, icone, canais: [{id, nome}]}]`
  (o que o bot enxerga), e um comando do motor `saida` com
  `{destino: "local" | "discord", canal?}`. O painel já tem o bloco "Saída do som".
- **Intents:** `guilds` e `voice_states` para o painel. Para `@Freddy toca`
  pelo chat, também `message_content` (intent privilegiado: ligar no portal).
- **Um relógio só:** se a caixa de som e o Discord puxarem da mesma Mesa ao
  mesmo tempo, a música anda em dobro. Com o Discord ativo, a caixa de som
  vira "monitor" (toca a cópia do que o Discord puxou) ou desliga. Decidir
  na Fase 2.
- **Erros do Discord** (sem permissão no canal, canal cheio, caiu) viram um
  evento novo para o painel mostrar, como o Kenku faz.
- O `cog.py` do Bardo vira o bot do Freddy: troca o `FFmpegPCMAudio` por
  faixa pela `SaidaDiscord` contínua, e os comandos de texto chamam o mesmo
  `Motor` que o painel usa (uma fila só para o chat e o painel).
