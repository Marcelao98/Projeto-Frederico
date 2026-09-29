# Módulo Bardo — música do YouTube, por link ou por busca

**Status:** ✅ Em produção desde 2026-09-27 · tocar, fila, pausar, continuar, parar e volume.
Busca booleana no dataset: implementada e testada (lógica pura), ainda não validada no Discord.

## O que faz, hoje

A Natty reconhece pedidos de música em linguagem natural — igual ao
módulo Dice reconhece "1d20 com vantagem" em vez de exigir um comando
formal — e toca no canal de voz de quem pediu, a partir de um link do
YouTube ou de uma busca por tema/origem no dataset local.

O pedido precisa ser dirigido à Natty: começar com o nome dela ("natty",
"ei natty") ou mencioná-la (o usuário @Natty ou o cargo automático @Natty,
que o Discord oferece com o mesmo nome).

| Ação | Exemplos | Slash command |
|------|----------|---------------|
| Tocar (ou pôr na fila) | `natty toca <link>`, `@Natty bota <link>`, `natty adiciona <link>` | `/tocar pedido:<link>` |
| Buscar no dataset | `natty toca triste e fire emblem`, `@Natty toca boss fight sem elden ring` | `/tocar pedido:<busca>` |
| Pular | `natty pula`, `natty próxima`, `natty skip` | `/pular` |
| Ver a fila | `natty fila`, `natty mostra a playlist` | `/fila` |
| Limpar a fila | `natty limpa a fila`, `natty esvazia a fila` | `/limpar-fila` |
| Pausar | `natty pausa` | `/pausar` |
| Continuar | `natty continua`, `natty volta a tocar`, `natty despausa` | `/continuar` |
| Parar (limpa a fila e sai do canal) | `natty para`, `natty chega`, `natty sai` | `/parar` |
| Volume | `natty volume 30`, `natty aumenta o volume`, `natty abaixa` | `/volume nivel:30` |
| Ver volume | `natty qual o volume?` | `/volume` |

- Tocar com música já tocando põe a nova no fim da fila. Quando uma música
  acaba, a próxima toca sozinha e a Natty avisa no canal do último pedido.
- A fila é por servidor, só em memória (some se a Natty reiniciar) e aceita
  até 50 músicas (`MAX_FILA`). A fila guarda o link, e a URL do áudio é
  resolvida de novo na hora de tocar, porque a do YouTube expira.
- Volume vai de 0 a 100%, começa em 50% e "aumenta"/"abaixa" mexe 20%.
  Vale por servidor e zera quando a Natty reinicia.
- Os slash commands não dependem de menção nem da Message Content Intent.

## Busca no dataset

"natty toca <texto>" sem link procura no `dataset/musicas.json` (~490
faixas de Elden Ring, Dark Souls, Bloodborne, Fire Emblem: Three Houses,
Umineko, Subahibi e Hollow Knight, cada uma com origem e temas em
português) e põe o resultado na fila. Se nada tocava, a primeira já começa.

- `e` = E, `ou` = OU, `sem`/`não` antes de um termo = exclui o termo.
- O `ou` separa grupos inteiros: `boss fight e elden ring ou hollow knight`
  é `(boss fight e elden ring) ou hollow knight` — traz todo o Hollow
  Knight, não só os boss fights. Pra isso, repete o termo:
  `boss fight e elden ring ou boss fight e hollow knight`.
- Cada termo é comparado por substring, sem acento e sem diferenciar
  maiúscula, contra nome da faixa, nome e tipo da origem e temas.
- Palavras de preenchimento ("uma", "música", "de"...) são ignoradas.
- Achando mais de 15 (`MAX_RESULTADOS_DA_BUSCA`), sorteia 15 e avisa
  quantas achou. A fila continua limitada a 50.

**Limitação conhecida — sem sinônimos.** "triste" não acha "trágico" nem
"melancólico": `natty toca triste e bloodborne` não acha nada, porque as
faixas do Bloodborne estão marcadas como trágico/melancólico. Tema em
português também não bate com palavra em inglês que só aparece no nome
da faixa (ex: "sem chuva" não filtra "(Rain)"). É curadoria do dataset
(vocabulário de temas), não bug do parser. Hoje 34 faixas estão como
"não classificado".

## Por que não usa Lavalink

Decisão registrada em `modules/sieve/Findings/natty-reports/lavalink-perspective.md`
e confirmada em conversa: para o estágio atual (uma mesa, sem Spotify como
requisito), nem Lavalink nem Kenku em produção fazem sentido. O trade-off
central é que ambos trocam "sem processo extra" por "um processo extra"
(JVM ou Electron) — e o Natty hoje é um monólito modular Python puro (ver
`CLAUDE.md` da raiz).

Este MVP usa a abordagem mais simples possível: `discord.py`'s
`voice_client` nativo + `yt-dlp` (resolve o link em URL de áudio direto) +
FFmpeg (decodifica o stream pro formato que o Discord espera). Zero
processo extra, zero JVM.

A interface de `service.py` foi desenhada para poder ser trocada por um
cliente de um nó Lavalink de verdade no futuro, se o áudio algum dia pesar
demais no processo principal — sem precisar reescrever `cog.py`.

## Estrutura

```
modules/bardo/
├── __init__.py
├── youtube.py     # acesso cru ao YouTube via yt-dlp (equivalente a sheets.py no core)
├── service.py      # lógica pura: interpreta o pedido, fila, volume, busca booleana
├── cog.py           # interface Discord: on_message + slash commands, voz, playback
├── test_service.py  # testes de pedidos, fila e busca
├── dataset/
│   └── musicas.json  # faixas taggeadas (origem + temas), curadoria em andamento
└── README.md
```

## Requisitos de ambiente (fora do `pip install`)

1. **FFmpeg instalado no sistema** (não é pacote Python — precisa estar no
   `PATH` da máquina que roda o bot). No Ubuntu/Debian: `apt install ffmpeg`.
2. **PyNaCl** e **davey** (já em `requirements.txt`) — `discord.py` exige
   os dois pra voz; o `davey` é a criptografia de voz (DAVE) que o Discord
   passou a exigir. Sem ele a conexão de voz falha.
3. **Message Content Intent habilitada no Discord Developer Portal**
   (Bot → Privileged Gateway Intents → Message Content Intent). Sem isso,
   `message.content` chega sempre vazio pro bot, mesmo com
   `intents.message_content = True` no código — as duas coisas são
   independentes e as duas são necessárias.

## Fluxo

```
Usuário: "natty toca https://youtube.com/watch?v=xxx"
        ↓
cog.py (on_message)
  ├─ falou com a Natty? (nome, menção ou cargo) → chamou_a_natty() + discord.py
  ├─ interpretar_pedido(texto) → Pedido      → service.py (regex: tocar/pausar/continuar/parar/volume)
  ├─ usuário está em canal de voz?            → discord.py (message.author.voice)
  ├─ sem link? buscar_musicas(busca)            → service.py (dataset/musicas.json) → fila
  ├─ resolver_musica(link)                    → service.py → youtube.py → yt-dlp
  ├─ conecta/move pro canal de voz            → discord.py (voice_client)
  └─ toca via FFmpegPCMAudio + volume         → discord.py + FFmpeg
```

## Testes

```
python -m unittest discover -s modules/bardo -t .
```

Cobrem o reconhecimento de pedidos, a fila e a busca booleana
(`service.py`), inclusive um teste que valida o dataset real. A parte de voz foi
validada à mão no Discord.

## O que falta pro próximo passo

- Sinônimos/vocabulário padronizado de temas na busca
- Completar Dark Souls e Hollow Knight no dataset (hoje 3 e 4 faixas)
- Loop (repetir a música ou a fila), remover um item da fila, colar playlist do YouTube
- Sair sozinha do canal quando ficar vazio
- Fontes além de YouTube (Freesound, local files)
- Tratamento de erro mais fino (vídeo privado, idade-restrito, etc. — hoje
  cai tudo no mesmo `except Exception`)
