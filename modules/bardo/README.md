# Módulo Bardo — link direto, dataset com tags, fila e busca booleana

**Status:** ✅ Playback por link testado em produção. Busca por tags + fila
implementadas e com testes automatizados; ainda não testadas em produção de
verdade (rede bloqueada no ambiente onde foram escritas).

## O que faz, hoje

A Natty reconhece um pedido de música em linguagem natural — igual ao
módulo Dice reconhece "1d20 com vantagem" em vez de exigir um comando
formal — de dois jeitos:

**1. Link direto do YouTube** — toca na hora, interrompe o que tava tocando:

```
@Natty toca https://youtube.com/watch?v=...
@Natty toque https://youtu.be/...
@Natty bota https://www.youtube.com/watch?v=...
@Natty play https://youtube.com/watch?v=...
```

**2. Busca por tema/origem em linguagem natural** — procura no dataset
local (`dataset/musicas.json`, ~490 faixas taggeadas hoje) e enfileira o
que encontrar:

```
@Natty toca triste e bloodborne
@Natty toca boss fight e elden ring ou hollow knight
@Natty toca calmo e fire emblem sem batalha
```

Gramática da busca: `e` = E, `ou` = OU (separa grupos alternativos),
`sem`/`não` antes de um termo = exclui esse termo. Cada termo é comparado
(sem acento, case-insensitive, por substring) contra nome da faixa, nome
da origem, tipo da origem (jogo/visual novel) e temas da faixa. Se a busca
achar mais de 15 resultados, sorteia 15 pra não lotar a fila inteira com
uma franquia só (avisa quantas achou vs. quantas entrou).

## Fila

Uma fila por servidor (`guild_id`), em memória (zera se o bot reiniciar —
aceitável pra uma mesa de D&D, não é requisito de persistência). Quando
uma faixa termina, a próxima da fila toca sozinha (via callback `after=`
do `voice_client.play()`, que discord.py chama numa thread separada — por
isso o uso de `asyncio.run_coroutine_threadsafe` em vez de `await` direto
em `cog.py`). Um pedido por link direto interrompe e limpa a fila (é
pedido explícito do usuário); um pedido por busca só enfileira.

Não tem ainda: comando pra pular faixa, ver o que tá na fila, ou limpar
manualmente — as funções (`service.proxima_da_fila`, `service.ver_fila`,
`service.limpar_fila`) já existem, só falta o gatilho de linguagem natural
no `cog.py` chamando elas.

## Por que não usa Lavalink

Decisão registrada em `modules/natty-sieve/natty-reports/lavalink-perspective.md`
e confirmada em conversa: para o estágio atual (uma mesa, sem Spotify como
requisito), nem Lavalink nem Kenku em produção fazem sentido. O trade-off
central é que ambos trocam "sem processo extra" por "um processo extra"
(JVM ou Electron) — e o Natty hoje é um monólito modular Python puro (ver
`CLAUDE.md` da raiz).

Este módulo usa a abordagem mais simples possível: `discord.py`'s
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
├── youtube.py         # acesso cru ao YouTube via yt-dlp (equivalente a sheets.py no core)
├── service.py          # lógica pura: gatilho, link, busca booleana, fila
├── cog.py                # interface Discord: on_message, conecta em voz, toca, avança fila
├── test_service.py       # testes automatizados (unittest, nos moldes do módulo Dice)
├── dataset/
│   └── musicas.json       # ~490 faixas taggeadas (origem + temas), curadoria em andamento
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
     ou: "@Natty toca triste e bloodborne"
        ↓
cog.py (on_message)
  ├─ eh_pedido_de_musica(texto)?             → service.py (regex: toca/toque/play/bota)
  ├─ tem link do YouTube?
  │    ├─ sim → resolver_musica(link)         → service.py → youtube.py → yt-dlp
  │    │        limpa fila, toca na hora
  │    └─ não → extrair_texto_de_busca(texto) → service.py
  │             buscar_por_tags(texto)         → service.py (dataset/musicas.json)
  │             adicionar_varias_na_fila(...)  → service.py
  ├─ conecta/move pro canal de voz            → discord.py (voice_client)
  ├─ toca via FFmpegPCMAudio                  → discord.py + FFmpeg
  └─ ao terminar, toca a próxima da fila       → cog.py (after=) + service.py (proxima_da_fila)
```

## Conhecido: limitações do dataset de tags

A busca é por substring exato, não por sinônimo — "triste" não bate com
"trágico"/"melancólico" mesmo sendo parecido, e um tema em português não
bate com uma palavra em inglês que só aparece no nome da faixa (ex:
"sem chuva" não filtra faixas cujo nome tem "(Rain)"). Não é bug do motor
de busca — é o dataset ainda precisando de curadoria/padronização de
vocabulário, o que é trabalho contínuo, não travado por código.

## Testado

- ✅ Playback por link direto, em produção real (canal de voz, música tocando de fato).
- ✅ Sintaxe (`py_compile`) de todos os arquivos.
- ✅ Reconhecimento de gatilho + extração de link.
- ✅ Busca booleana (AND/OR/NOT, filler words, acentuação) — 18 testes
  automatizados em `test_service.py`, todos passando
  (`python -m unittest discover -s modules/bardo -t .`).
- ✅ Fila (FIFO, múltiplos servidores isolados, fila vazia) — cobertos nos
  mesmos testes.
- ⚠️ **Não testado em produção ainda**: busca por tags + fila + avanço
  automático via `after=`. A lógica pura (service.py) está testada; o que
  falta validar é o comportamento real dentro do Discord (múltiplas
  faixas em sequência, thread-safety do callback).

## O que falta pro próximo passo (fora do escopo atual)

- Comando de linguagem natural pra pular faixa / ver fila / limpar fila
  (as funções de service.py já existem, falta o gatilho em cog.py)
- Sinônimos/normalização de tema pra busca não depender de match exato
- Completar Dark Souls e Hollow Knight no dataset (hoje só têm 3 e 4
  faixas manuais, o resto das franquias tem trilha completa)
- Fontes além de YouTube (Freesound, arquivos locais)
- Sonoplastia / múltiplas camadas de áudio simultâneas (música + ambiente
  + efeito pontual) — precisa de um mixer de PCM próprio, discutido mas
  não iniciado (Discord só aceita um stream de áudio por conexão de voz)
- Tratamento de erro mais fino (vídeo privado, idade-restrito, etc. — hoje
  cai tudo no mesmo `except Exception`)
