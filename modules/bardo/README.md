# Módulo Bardo — música do YouTube, por link ou por busca

**Status:** ✅ Em produção desde 2026-09-27 · tocar, fila, pausar, continuar, parar e volume.
Busca no dataset (596 faixas) e busca livre no YouTube com aprendizado em mesa: ✅ em uso real —
17 faixas já entraram no dataset como "Descoberta em mesa". Pedido falado na call (via módulo Echo):
✅ validado em 01/10/2026 ("Garçom", "Ela Partiu").

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
| Buscar no YouTube (quando o dataset não tem) | `natty toca ragnar the red skyrim` | `/tocar pedido:<busca>` |
| Pular | `natty pula`, `natty próxima`, `natty skip` | `/pular` |
| Ver a fila | `natty fila`, `natty mostra a playlist` | `/fila` |
| Limpar a fila | `natty limpa a fila`, `natty esvazia a fila` | `/limpar-fila` |
| Pausar | `natty pausa` | `/pausar` |
| Continuar | `natty continua`, `natty volta a tocar`, `natty despausa` | `/continuar` |
| Parar (para a música e limpa a fila; **continua no canal**) | `natty para`, `natty chega`, `natty sai` | `/parar` |
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

## Busca livre no YouTube e aprendizado por confirmação

Se "natty toca <texto>" não acha nada no dataset, a Natty busca o texto
direto no YouTube, toca o primeiro resultado (ou põe na fila, como um link)
e pergunta no mesmo canal: *"Era essa mesmo? Me diz uns temas dela"*.

- A resposta é a próxima mensagem **naquele canal que chama a Natty**
  (nome ou menção, como um pedido), de qualquer pessoa — a mesa é
  coletiva. Conversa normal da mesa não conta, então "kkkk" não vira tema.
  - `"natty, não"` (o "não" em qualquer lugar da frase) → descarta, nada é gravado.
  - `"natty, é triste e épico"` → grava a faixa com os temas `triste`,
    `épico` (separa por vírgula e por " e "; ignora "sim", "é", "essa",
    "mesmo"...; no máximo 5 temas).
  - `"natty, sim"` sem tema → grava como `"não classificado"`: a música é
    a certa, só ninguém opinou sobre o clima.
- A pergunta vale 3 minutos (`SEGUNDOS_PARA_RESPONDER`); depois disso
  ninguém respondeu, e a próxima mensagem é só conversa. Uma pergunta
  por servidor: uma busca nova substitui a anterior.
- Pedido pra Natty (`natty pula`, `natty toca ...`) nunca conta como resposta.
  Por isso uma resposta com palavra de pedido ("natty, bota taverna") é
  lida como pedido — melhor responder só com os temas.
- A faixa entra no `musicas.json` com origem `Descoberta em mesa` (tipo
  `outro`), id `descoberta-em-mesa-<título>`, e já com as categorias
  calculadas pelo vocabulário. A busca acha ela na hora, sem reiniciar.
  Vídeo que já está no dataset não é gravado de novo.
- Grava o link de watch do vídeo, não a URL de áudio (essa expira).
- Vale conferir de tempos em tempos as faixas `Descoberta em mesa` no
  `musicas.json`: o tema é o que a mesa digitou, não passa pelo vocabulário.

## Busca no dataset

"natty toca <texto>" sem link procura no `dataset/musicas.json` (~580
faixas de Elden Ring, Dark Souls, Bloodborne, Fire Emblem: Three Houses,
Umineko, Subahibi, Hollow Knight e NieR:Automata, cada uma com origem e
temas em português) e põe o resultado na fila. Se nada tocava, a primeira
já começa. Se não acha nada, cai na busca livre no YouTube (acima).

- `e` = E, `ou` = OU, `sem`/`não` antes de um termo = exclui o termo.
- O `ou` separa grupos inteiros: `boss fight e elden ring ou hollow knight`
  é `(boss fight e elden ring) ou hollow knight` — traz todo o Hollow
  Knight, não só os boss fights. Pra isso, repete o termo:
  `boss fight e elden ring ou boss fight e hollow knight`.
- Cada termo bate com a faixa se aparece (sem acento, sem diferenciar
  maiúscula) no nome da faixa, na origem, nos temas ou nas categorias —
  **ou** se é sinônimo de uma categoria da faixa (ver abaixo).
- Termo de várias palavras tenta a frase inteira ("boss fight", "hollow
  knight") e, se não bater, cada palavra: "luta de chefe" = luta e chefe.
- Palavras de preenchimento ("uma", "música", "de", "para", "clima"...) são
  ignoradas: "uma música para relaxar", "clima de taverna".
- Achando mais de 15 (`MAX_RESULTADOS_DA_BUSCA`), sorteia 15 e avisa
  quantas achou. A fila continua limitada a 50.

### Categorias e sinônimos

O dataset tinha ~170 temas soltos ("melancólico", "sereno-macabro",
"ódio"...), muitos com uma faixa só, e ninguém numa mesa busca assim. Por
isso existem as **categorias** (`dataset/vocabulario.json`): ~27 coisas que
alguém de fato pede — triste, calmo, tenso, combate, chefe, épico,
sombrio, terror, mistério, mágico, sagrado, alegre, engraçado, romântico,
nobreza, cidade (taverna), exploração, natureza, masmorra, descanso
(acampamento), vilão, final, abertura...

Cada categoria tem:
- `palavras`: o que as pessoas digitam e leva à categoria — "trágico",
  "tristeza", "luto" levam a *triste*; "taverna", "vila" levam a *cidade*.
- `temas`: temas crus que colocam a faixa na categoria, mas que sozinhos
  são específicos demais pra puxá-la inteira (quem busca "coral" quer
  coral, não todo o épico).

Cada faixa do `musicas.json` guarda as suas em `categorias`, geradas a
partir dos `temas`. Depois de mexer no vocabulário ou acrescentar faixas:

```
python scripts/categorizar_musicas.py
```

O script só acrescenta categorias; dá pra pôr uma à mão numa faixa (ex:
"taverna" onde o vocabulário não pegou) e ela fica. Pra tirar, apaga à mão.

**Ainda falta curadoria:**
- 37 faixas (24 do Umineko, com nomes abstratos como "Core" e "Mind", 9 da
  NieR:Automata e 4 do Subahibi) estão como "não classificado" — precisa
  ouvir pra marcar.
- Não há faixa de taverna de verdade: "taverna" cai em *cidade* (hubs,
  cotidiano, mercado), que é a aproximação mais próxima.
- Tema em português não bate com palavra em inglês que só está no nome
  da faixa ("sem chuva" não filtra "(Rain)").

## Parar não sai mais da call (desde 02/10/2026)

"natty para" (e `natty chega`, `natty sai`, `/parar`) para a música e limpa a fila, mas **a Natty continua no canal de voz**. Quem tira ela da call agora é só o Echo: "NAT20, por favor, saia" ou "@Natty, tampe os ouvidos".

Motivo: com o Echo escutando, sair da call no "para" derrubava a escuta — "NAT20, por favor, pare" (que posta `🎙️ natty para`) deixaria a Natty fora da call. E tinha um bug escondido: na conexão do Echo (`VoiceRecvClient`), `stop()` para a música **e a escuta**, então até "natty pula" deixava a Natty surda pra senha. Agora `_parar` e `_pular` usam `_parar_audio()`, que chama `stop_playing()` quando a conexão tem (só a do Echo tem) e `stop()` quando não — sem importar nada do Echo. Testes em `test_cog.py`.

Efeito colateral conhecido: usando o Bardo **sem** o Echo, depois de "natty para" a Natty fica parada no canal até alguém tirar ela (ou até o Echo mandar sair). "Sair sozinha do canal quando ficar vazio" continua nas pendências.

## Pedido falado (mensagens da própria Natty com 🎙)

O listener ignora mensagens de bots, menos a da **própria Natty que começa com 🎙** (`MARCADOR_VOZ` no `cog.py`) — a mesma convenção do Dice. É assim que o pedido de música falado numa call chega aqui: o módulo Echo grava o pedido, transcreve com Whisper e posta `🎙️ natty toca <o que ouviu>`; o Bardo trata como qualquer pedido digitado (dataset, e YouTube se não achar). Nenhum dos dois importa o outro. Quem "pediu" é a própria Natty, então a música toca no canal de voz dela — o mesmo onde o Echo está escutando. As respostas do Bardo nunca começam com 🎙, então ele não reage a si mesmo. Ver `modules/echo/README.md`, seção "Pedido de música".

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
├── youtube.py     # acesso cru ao YouTube via yt-dlp: link ou busca (equivalente a sheets.py no core)
├── service.py      # lógica pura: pedido, fila, volume, busca booleana, busca livre + aprendizado
├── cog.py           # interface Discord: on_message + slash commands, voz, playback
├── test_service.py  # testes de pedidos, fila e busca
├── dataset/
│   ├── musicas.json      # faixas taggeadas (origem, temas, categorias)
│   └── vocabulario.json  # categorias de busca e seus sinônimos
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
  ├─ nada no dataset? resolver_por_busca_livre → youtube.py (ytsearch1:) → toca + criar_pendencia()
  ├─ mensagem seguinte no canal? interpretar_resposta_de_pendencia → adicionar_descoberta_ao_dataset
  ├─ resolver_musica(link)                    → service.py → youtube.py → yt-dlp
  ├─ conecta/move pro canal de voz            → discord.py (voice_client)
  └─ toca via FFmpegPCMAudio + volume         → discord.py + FFmpeg
```

## Testes

```
python -m unittest discover -s modules/bardo -t .
```

Cobrem o reconhecimento de pedidos, a fila, a busca booleana e o
aprendizado por confirmação (resposta, prazo, gravação sem duplicar)
(`service.py`), inclusive um teste que valida o dataset real. A parte de voz foi
validada à mão no Discord.

## O que falta pro próximo passo

- Classificar as 37 faixas "não classificado" e trilhas de taverna de verdade
- Completar Dark Souls no dataset (hoje 3 faixas)
- Loop (repetir a música ou a fila), remover um item da fila, colar playlist do YouTube
- Sair sozinha do canal quando ficar vazio
- Fontes além de YouTube (Freesound, local files)
- Tratamento de erro mais fino (vídeo privado, idade-restrito, etc. — hoje
  cai tudo no mesmo `except Exception`). Visto em 01/10/2026: uma busca livre
  sem resultado (`ytsearch1:"dugeon ambience, kobold"`) só gerou traceback no
  log.
- O "era essa?" da busca livre aceita como resposta **qualquer** mensagem que
  chame a Natty nos 3 minutos seguintes — inclusive comandos de outro módulo.
  Em 02/10/2026, um pedido de música falado mal transcrito tocou um vídeo
  errado, e o "@Natty escuta" mandado logo depois foi lido como "sim, tema:
  escuta": o vídeo (`【ENG DUB】 Useless? I Made My Village Unstoppable`) entrou
  no acervo. Correção possível: ignorar mensagens que outro módulo reconhece
  como comando ("escuta", "socorro", "tampe os ouvidos", rolagem).
- Título de música com "volta", "próxima" ou "fila" vira outro comando
  ("natty toca Volta pra Casa" = continuar): pular/fila/volume/pausar/continuar
  são checados antes de "tocar". Pesa mais no pedido falado, onde não dá pra
  reescrever.
