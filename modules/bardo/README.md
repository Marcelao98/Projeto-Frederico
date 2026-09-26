# Módulo Bardo — MVP (tocar um link do YouTube)

**Status:** ✅ Implementado (MVP mínimo) · não testado em produção (só localmente, sem rede pra YouTube)

## O que faz, hoje

A Natty reconhece um pedido de música em linguagem natural — igual ao
módulo Dice reconhece "1d20 com vantagem" em vez de exigir um comando
formal — e toca o link do YouTube no canal de voz de quem pediu.

```
@Natty toca https://youtube.com/watch?v=...
@Natty toque https://youtu.be/...
@Natty bota https://www.youtube.com/watch?v=...
@Natty play https://youtube.com/watch?v=...
```

Não tem busca por tags, não tem dataset, não tem fila, não tem `/comando`.
É só: reconhece o pedido, pega o link, toca. Tudo o resto (dataset de
tags, playlist dinâmica, fontes além de YouTube) é trabalho futuro descrito
em outros documentos do projeto.

## Por que não usa Lavalink

Decisão registrada em `modules/natty-sieve/natty-reports/lavalink-perspective.md`
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
├── service.py      # lógica pura: reconhece gatilho, extrai link, orquestra resolução
├── cog.py           # interface Discord: on_message, conecta em voz, toca
└── README.md
```

## Requisitos de ambiente (fora do `pip install`)

1. **FFmpeg instalado no sistema** (não é pacote Python — precisa estar no
   `PATH` da máquina que roda o bot). No Ubuntu/Debian: `apt install ffmpeg`.
2. **PyNaCl** (já em `requirements.txt`) — `discord.py` exige isso pra voz.
3. **Message Content Intent habilitada no Discord Developer Portal**
   (Bot → Privileged Gateway Intents → Message Content Intent). Sem isso,
   `message.content` chega sempre vazio pro bot, mesmo com
   `intents.message_content = True` no código — as duas coisas são
   independentes e as duas são necessárias.

## Fluxo

```
Usuário: "@Natty toca https://youtube.com/watch?v=xxx"
        ↓
cog.py (on_message)
  ├─ eh_pedido_de_musica(texto)?           → service.py (regex: toca/toque/play/bota)
  ├─ extrair_link_youtube(texto)           → service.py (regex de URL)
  ├─ usuário está em canal de voz?         → discord.py (message.author.voice)
  ├─ resolver_musica(link)                 → service.py → youtube.py → yt-dlp
  ├─ conecta/move pro canal de voz         → discord.py (voice_client)
  └─ toca via FFmpegPCMAudio               → discord.py + FFmpeg
```

## Testado

- ✅ Sintaxe (`py_compile`) de todos os arquivos
- ✅ Reconhecimento de gatilho + extração de link (testado localmente com
  4 casos: PT com gatilho, EN com gatilho, sem gatilho, link com querystring
  de playlist)
- ⚠️ **Não testado**: resolução real via yt-dlp e playback no Discord. O
  ambiente onde este código foi escrito não tem acesso de rede a
  youtube.com (só GitHub e registries de pacote). Precisa ser validado
  rodando o bot de verdade.

## O que falta pro próximo passo (fora do escopo deste MVP)

- Dataset de tags + busca booleana (`música triste e deserto`)
- Fila / próxima música
- Fontes além de YouTube (Freesound, local files)
- Testes automatizados (`test_service.py`, nos moldes do módulo Dice)
- Tratamento de erro mais fino (vídeo privado, idade-restrito, etc. — hoje
  cai tudo no mesmo `except Exception`)
