# Auditoria: do Freddy ao Fredify — relatório e roadmap

Feita em 07/11/2026 a partir do `main` (v0.6.0, commit `b808dee`), seguindo
`docs/etapas/auditoria-fredify.md`. **Nada de código foi mudado nem
renomeado.** Testes rodados antes: backend 142 ✅, painel 161 ✅,
`versao.py --conferir` ✅.

> **Fredify — a calopsita que toca tudo.**

---

## 1. Resumo em 10 linhas

1. A base é boa e quase toda serve: o motor de fila com contrato, a Mesa de
   som (48 kHz, quadros de 20 ms), as saídas plugáveis, o bot do Discord com
   DAVE funcionando, o Porteiro, o yt-dlp que se atualiza e o CI que testa o
   app empacotado de verdade.
2. O que é "de RPG" está mais nos **dados e nas palavras** do que no código:
   o acervo (607 faixas de jogo/VN), os 27 climas (`chefe`, `masmorra`,
   `nobreza`...), a palavra "mestre" (23 arquivos) e "mesa" (44).
3. O maior buraco pro "toca tudo": **a faixa é um link do YouTube**. Não
   existe "arquivo do meu PC" nem banco: tudo é JSON lido inteiro na memória,
   e o painel embute o acervo no próprio bundle.
4. **Android não roda o backend Python** (o Tauri não leva sidecar pro
   celular). Recomendo duas etapas: primeiro **controle remoto** do Fredify do
   PC; depois **o celular toca sozinho** (Tauri Android + o player nativo do
   Android). Nada de Chaquopy, nada de reescrever tudo em Rust agora.
5. Achado bom: o "modo navegador congelado" (as portas em TypeScript do
   pedido, da busca e do motor) é **justamente o que o Android sozinho
   precisa**. Ele deixa de ser peso morto e vira semente.
6. **Banco: SQLite com FTS5** no backend (e o mesmo esquema no Android). A
   busca em português continua igual por cima; os testes atuais viram a régua.
7. **YouTube:** serve no desktop baixado do GitHub, mas é o maior risco do
   projeto. Na Play Store, um app que puxa áudio do YouTube é recusado.
   Arquivos locais têm que virar a fonte principal.
8. **A B2 continua valendo** (todos os 6 passos servem a um tocador
   universal), mas recomendo ela **logo depois** do banco + biblioteca local,
   que é o que mais muda a cara do produto.
9. **Nome:** não achei app "Fredify" em loja; o `fredify.net` já é de um
   músico suíço. O risco real é o Spotify, que já brigou (e ganhou) contra
   nomes "-ify" parecidos (Potify, 2022). Pra projeto aberto, dá pra usar;
   pra loja e marca, faça a busca no INPI antes.
10. A documentação inteira fala de "mesa de RPG" e o README ainda diz que o
    nome é FredBOT/Freddy/Fredérico. Falta o básico de projeto aberto
    (CONTRIBUTING, SECURITY, CHANGELOG, avisos de licença do que vem junto).

---

## 2. O que existe hoje e o que fazer com cada peça

### Reaproveitar como está (serve pra qualquer tocador)

| Peça | Onde | Por que serve |
|---|---|---|
| Contrato do motor (comandos, estado, eventos), rodado nos dois lados | `frontend/src/motor/tipos.ts`, `salas/motor.py`, `casos_contrato.json` | Fila, pular, mover, embaralhar, repetir, volume, posição: é o miolo de qualquer tocador. O teste de contrato é o que vai segurar o Android de pé. |
| Mesa + formato PCM (20 ms, 48 kHz, estéreo, 16 bits) | `audio/mesa.py`, `audio/pcm.py` | É o formato do Discord e serve pra mixar música + efeitos e pro mic virtual. Não precisa mudar. |
| Fontes e saídas plugáveis | `audio/fontes/`, `audio/saidas/` | O FFmpeg já toca **qualquer** arquivo ou URL; só falta uma fonte "arquivo" que não passe pelo yt-dlp. |
| Bot do Discord (DAVE, player do jeito do Kenku, assobio, diagnóstico) | `integracoes/discord/` | Funciona e foi difícil de chegar lá. Fica. |
| Porteiro (Host + Origin em todo pedido) | `api/porteiro.py` | Continua obrigatório. Vai precisar de um modo "rede de casa com senha/pareamento" pro controle remoto. |
| yt-dlp que se atualiza com SHA-256 | `audio/fontes/ytdlp.py` | Bom do jeito que está. |
| CI: testes, ponta a ponta, backend empacotado ligado de verdade, Releases | `.github/workflows/app.yml` | Base pronta pra acrescentar o build do Android. |
| Plumagens e o Frederico | `estilo/temas.css`, `public/aves/` | Identidade; é o que separa o Fredify do Spotify (ver o nome). |
| Playlists salvas, editor, planilha CSV, modo Acervo | `dados/`, `modos/` | Tudo útil; muda a fonte (banco no lugar de JSON). |
| Busca booleana em português ("triste e bloodborne sem chefe") | `nucleo/busca.py`, `nucleo/pedido.py` | É o diferencial do produto. Fica; só passa a rodar em cima do banco. |

### Generalizar (está amarrado ao RPG ou ao YouTube)

| O quê | Hoje | Pro Fredify |
|---|---|---|
| **A faixa** | `link` é sempre do YouTube; `origem.tipo` = jogo/VN/outro; `extrair_link_youtube` é o único jeito de reconhecer link | Faixa com **fonte** (`youtube`, `arquivo`, `url`, `jamendo`, `freesound`...) + artista, álbum, duração, gênero. |
| **Climas** (27 categorias) | Mistura humor geral (triste, calmo, épico) com uso de RPG (chefe, masmorra, nobreza, vilão) | Dois níveis: **climas gerais** pra qualquer música + **pacotes de uso** (o de RPG vira um pacote que se liga). Gênero do arquivo (rock, jazz...) também vira tema. |
| **Acervo oficial** | 607 faixas de 9 franquias, embutido no app e no bundle do painel | Vira o **pacote "Trilhas de jogo e RPG"**: importado no banco, opcional, atualizável. |
| **Vocabulário de pessoas e lugares** | "mestre", "mesa", "sala = mesa de RPG", "pasta do mestre" | "você", "lugar tocando", "pasta do Fredify". |
| **Limites** | Fila de 50; busca sorteia 15 | Fazem sentido pra mesa; num tocador, a fila pode ser bem maior e "toca tudo de Queen" não deve sortear 15. Vira preferência. |
| **Sala** | "uma mesa de RPG tocando" | "um lugar tocando" (este PC, um servidor do Discord, o celular). A ideia é a mesma, e a B2 já prepara. |

### O que sobra ou pesa

- **O painel embute o acervo no bundle** (alias `@acervo`) e filtra tudo na
  memória. Com uma biblioteca de 20 mil músicas isso não aguenta: o painel tem
  que **perguntar pro backend** (busca paginada).
- **Duplicação Python ↔ TypeScript** (pedido, busca, motor). Hoje é custo; com
  o Android sozinho vira vantagem, desde que o teste de contrato continue
  rodando nos dois lados. A etapa D ("um cérebro só no backend") precisa ser
  repensada: com o Android tocando sozinho, o cérebro **tem** que existir
  também fora do Python.
- **localStorage preso à porta 47823**: com banco no backend, temas e
  playlists param de depender disso.
- **Mac:** sem backend no Mac Intel, e o CI compila Mac a cada push. É
  esforço que não está nas prioridades (Windows, Linux, Android).
- **Laços com a Natty** no README e no CLAUDE: fica como história, sai da
  descrição do produto.

---

## 3. Arquitetura pras plataformas novas

### 3.1 Android: as saídas avaliadas

| Caminho | O que é | Custo | Toca no celular? | Discord no celular? | YouTube? | Veredito |
|---|---|---|---|---|---|---|
| **A. Controle remoto** | O app do celular é o painel, falando com o Fredify do PC pela rede de casa | **Baixo**: o painel já é web; falta pareamento (QR code + senha) e o Porteiro aceitar a rede local com login | Não (toca no PC/Discord) | Sim, pelo PC | Sim, pelo PC | ✅ **Primeiro passo** |
| **B. Python dentro do Android (Chaquopy)** | Leva o backend Python pro APK | **Alto e frágil**: sem sidecar no Tauri; sounddevice/PortAudio não existe no Android; FFmpeg pro Android ficou sem o ffmpeg-kit (arquivado); `davey` (DAVE) é extensão em Rust sem pacote pra Android | Sim | Talvez, com muito sofrimento | Sim (fora da Play Store) | ❌ Não recomendo |
| **C. Reescrever o núcleo em Rust** | Um núcleo só pra todos (Tauri em tudo): `symphonia`/`cpal`/`rusqlite`/`songbird` | **Muito alto**: meses; o yt-dlp não tem equivalente em Rust; o DAVE no Rust ainda é terreno novo | Sim | Sim (se o songbird estiver em dia com o DAVE) | Não | ⏸ Reavaliar daqui a um ano |
| **D. Player nativo do Android** | Tauri Android com o mesmo painel React + um plugin Kotlin com o **Media3/ExoPlayer** (toca em segundo plano, notificação, tela bloqueada, fone Bluetooth) + SQLite no aparelho + as portas TS do pedido/busca/motor | **Médio** | Sim, de verdade | Não sozinho (usa o PC) | Não (versão da loja) | ✅ **Segundo passo** |

**Recomendação: A depois D.** O celular primeiro vira controle do PC (rápido
de entregar, serve pra quem usa o Discord), depois ganha vida própria como
tocador da biblioteca do aparelho e das fontes abertas. Tudo que precisa de
Python pesado (yt-dlp, Discord) continua no PC, que vira "a estação".

Atenção: **desde setembro de 2026, no Brasil, o Android só instala app de
desenvolvedor verificado pelo Google**, mesmo fora da Play Store. Pra
distribuir o APK pelo GitHub, você vai precisar se cadastrar e verificar como
desenvolvedor (conferir o estado atual da regra na hora).

### 3.2 O som: a Mesa e as saídas servem?

**Servem.** 48 kHz, estéreo, 16 bits em quadros de 20 ms é o padrão do
Discord e dá pra somar camadas (música + efeitos) sem conversão. O que falta
pra um tocador universal, além da B2:

- **Volume igualado entre faixas** (normalização de loudness): misturar trilha
  de jogo do YouTube com MP3 da pessoa dá saltos de volume. Medir uma vez
  (FFmpeg `loudnorm`/EBU R128), guardar no banco, aplicar na Mesa.
- **Crossfade e sem silêncio** (a B2 passo 5 resolve o silêncio; o crossfade
  vem fácil com as camadas do passo 4).
- **Teclas de mídia e controles do sistema** (MPRIS no Linux/KDE, SMTC no
  Windows): play/pause no teclado, no fone e no widget do KDE.
- **Escolher a saída de som** (o `SaidaLocal` já aceita dispositivo, só não é
  exposto no painel).

**A B2 ainda é o passo certo?** Sim, os seis passos servem:

| Passo da B2 | Serve ao Fredify? |
|---|---|
| 1. Avisos internos | Sim: base pra teclas de mídia, Android remoto, saída por rede |
| 2. Sala | Sim, renomeada pra "lugar tocando" |
| 3. Relógio único e saídas plugáveis | Sim: indispensável pra mic virtual e saída por rede |
| 4. Mesa com camadas | Sim: é o soundboard (efeitos por cima da música) e o crossfade |
| 5. Próxima procurada antes | Sim: fim do silêncio, o que mais se nota |
| 6. Fila salva | Sim: o básico de qualquer tocador |

Só mudo a **ordem no roadmap**: o banco e a biblioteca local vêm antes, porque
mudam o modelo da faixa (o cache do passo 5 é "por link" e passa a ser "por
fonte"). Fazer a B2 depois evita retrabalho.

### 3.3 "Outras plataformas"

| Onde tocar | Como | Custo | Recomendação |
|---|---|---|---|
| **Este aparelho** | Caixa de som (já existe) | — | ✅ |
| **Discord** | Bot (já existe) | — | ✅ |
| **Outro aparelho da casa / celular / VLC / navegador** | Nova saída "rede": a Mesa vira um stream (Opus ou MP3 por HTTP) com senha | **Baixo** (é só mais uma saída do relógio da B2) | ✅ Primeira "outra plataforma" |
| **Zoom, Meet, Discord sem bot, jogos** | Mic virtual (etapa C). Linux: o PipeWire cria; Windows: VB-Cable (instalado pela pessoa, é de terceiro) | Médio | ✅ Depois |
| **OBS / Twitch** | O OBS já captura o som do app (Windows e Linux/PipeWire) ou o mic virtual. **Risco:** música com direitos na Twitch = DMCA no canal do streamer. Pede um "modo streamer" que só toca faixas liberadas (CC0, Jamendo, arquivos próprios) | Baixo + curadoria | 🟡 Com modo streamer |
| **Chromecast** | Biblioteca de envio (ex.: pychromecast) apontando pra saída "rede" | Médio | ⏸ Depois |
| **DLNA/UPnP (TVs, caixas)** | Servidor/renderizador UPnP | Médio | ⏸ Depois |
| **Spotify/Deezer/Apple Music** | Os SDKs deles só tocam no player deles e não deixam o áudio ir pro Discord ou pra mixer | — | ❌ Não dá |

---

## 4. Banco de dados e busca

**Recomendação: SQLite com FTS5**, um arquivo `fredify.db` na pasta do usuário.
Vem com o Python (sem dependência nova pro PyInstaller), existe no Android, e
o FTS5 com o tokenizador `unicode61 remove_diacritics 2` já busca sem acento
("trágico" = "tragico"), igual ao `normalizar()` de hoje.

Desenho (resumo):

```
faixas       id, titulo, artista, album, duracao, genero,
             fonte_tipo (youtube|arquivo|url|jamendo|freesound),
             fonte_ref (link, caminho do arquivo...), pacote (oficial-rpg|minha-biblioteca|...),
             loudness, licenca, credito, adicionada_em, tocada_vezes, ultima_vez
temas        faixa_id, tema                   (o que a pessoa ou o pacote marcou)
categorias   faixa_id, categoria              (sempre calculada dos temas pelo vocabulário)
busca_fts    tabela FTS5: titulo, artista, album, origem, temas, categorias
playlists, playlist_itens, fila_salva, preferencias
arquivos     caminho, tamanho, modificado_em  (pra rever a pasta só no que mudou)
```

Como nada se perde:

- **Acervo oficial** → importado como o pacote `oficial-rpg` (com a versão do
  arquivo). Atualizar o pacote não apaga o que a pessoa mudou.
- **`ajustes.json`** → tabela de ajustes por cima do pacote, igual a hoje
  (camadas). O `acervo_promover.py` continua levando pro oficial.
- **`aprendidas.json`** → faixas do pacote `descobertas`.
- **Playlists** → tabelas; migração automática na primeira vez (como já foi
  feito com as playlists do navegador).
- **A busca em português** → o `_parse_query` continua igual; cada termo vira
  um pedaço de consulta (FTS + categorias), e o resultado é o mesmo. Os
  testes de `test_busca.py` e `busca.test.ts` viram a régua: passou neles,
  não mudou nada pra quem usa.

**Escala:** FTS5 responde em milissegundos com 100 mil faixas. A biblioteca do
PC entra por um "ler pasta" (tags com `mutagen`, que é GPL e combina com a
GPL-3.0), revisto só no que mudou (tamanho/data). O gênero e o humor das
tags viram temas pelo vocabulário, então "toca calmo e jazz" funciona na
biblioteca da pessoa sem ela marcar nada à mão.

**O painel** deixa de carregar o acervo inteiro: o modo Acervo e a Playlist
passam a pedir páginas de resultado (`GET /busca?q=...&pagina=`).

---

## 5. De onde vem a música (com honestidade)

| Fonte | Risco | Pra quê |
|---|---|---|
| **Arquivos do aparelho** | Nenhum | **A fonte principal do Fredify.** Funciona em todo lugar, inclusive na loja. |
| **YouTube via yt-dlp** | **Alto.** Os termos do YouTube proíbem acessar o áudio fora do player deles. A Play Store recusa/remove app que baixa do YouTube (o NewPipe vive fora dela por isso). Os bots Groovy e Rythm (Discord) fecharam em 2021 depois de notificação do Google. IP de servidor é bloqueado; o YouTube muda e quebra o yt-dlp com frequência. | Desktop baixado do GitHub, uso pessoal, rodando no PC da pessoa (nunca bot público na nuvem). Rotulado como "fonte opcional, por sua conta". **Fora da versão da Play Store.** |
| **Player oficial do YouTube (IFrame)** | Baixo (é o permitido), mas tem que aparecer o vídeo e não toca em segundo plano nem vai pro Discord | O que o modo navegador já faz. Serve de reserva. |
| **Jamendo** (API) | Baixo. Música com licença Creative Commons; a API é grátis pra uso não comercial e pede uma chave | Música "de verdade" legal, inclusive pra modo streamer |
| **Freesound** (API) | Baixo. Precisa de chave; cada som tem licença (CC0, CC-BY, CC-BY-NC): guardar o crédito | **Efeitos sonoros** do soundboard (CC0 por padrão, como já estava planejado) |
| **Internet Archive** | Baixo, mas a licença varia por item | Domínio público, gravações antigas |
| **Rádios online (Radio Browser)** | Baixo (só toca o stream da rádio) | Dezenas de milhares de rádios: bem "toca tudo", custo pequeno |
| **Free Music Archive** | Conferir: hoje não achei API aberta | Talvez |
| **Spotify/Deezer/Apple** | — | Não dá (o áudio não sai do player deles) |

---

## 6. O nome "Fredify"

O que achei (busca na web; os domínios não deu pra conferir daqui, o proxy
bloqueou os registros):

- **Nenhum app "Fredify"** apareceu nas buscas de lojas. Existe uma
  biblioteca Ruby `fredify` de 2015 (sem relação) e **`fredify.net` é o site
  de um músico suíço ("This Is Fredi Fy")** que vende um "album app": mesmo
  ramo (música), mas pequeno e de outro país.
- **O risco de verdade é o Spotify.** Ele se opõe a nomes "-ify" que lembram
  o dele. No caso **Potify** (2022) o órgão de marcas dos EUA deu razão ao
  Spotify por "diluição" da marca; também se opôs ao **Opstify**. Um tocador
  de música chamado Fredify fica na mesma área do Spotify, o que pesa contra.
- Na prática: **pra projeto aberto e sem fins comerciais, o risco é baixo.**
  Sobe se for pra loja com destaque, registrar marca, ganhar dinheiro ou
  usar visual parecido (verde, logo redondo com ondas).

**Recomendação:** pode usar "Fredify" agora. Antes de ir pra Play Store ou de
fazer logo definitivo: (1) busca no INPI (busca.inpi.gov.br, classes 9 e 41);
(2) conferir `fredify.com`, `.app` e `.com.br` no registro.br e num
registrador; (3) visual 100% calopsita, nada de verde Spotify. Se quiser um
plano B sem "-ify": **Frederico**, **Fredtoca** ou **Calopsom**.

---

## 7. Documentação

**Desatualizado:**

- `README.md`: "nome de trabalho FredBOT, Freddy ou Fredérico"; toda a
  seção "Pra onde vai" é de RPG.
- `CLAUDE.md`, `docs/ARQUITETURA.md`, `ROADMAP.md`: "o som da mesa de RPG",
  "sala = mesa de RPG", fases de mestres; a etapa D vai contra o Android
  sozinho.
- `tauri.conf.json`/`Cargo.toml`: "O som da mesa de RPG", "Painel de som para
  mesas de RPG".
- O branch principal no GitHub ainda é `bardo-inicial` (Settings → General →
  Default branch → `main`; só você consegue).

**Falta pra projeto aberto que outras pessoas vão usar:**

- `CONTRIBUTING.md` (como rodar, testar, a regra do contrato, português) e
  modelos de issue.
- `SECURITY.md`: o app abre um servidor local; tem que dizer como avisar uma
  falha.
- `CHANGELOG.md` (as Releases existem, mas não dizem o que mudou).
- **Avisos de licença do que vai junto** (`THIRD_PARTY.md`): o FFmpeg que vem
  no Windows (build GPL: tem que dizer de onde vem o código), discord.py,
  yt-dlp, PyNaCl, davey, o Kenku FM.
- **Guia de quem só usa** (instalar no Windows/Fedora/Android, primeira vez,
  Discord), separado do guia de quem programa.
- **Privacidade:** o que fica guardado e onde, e que nada sai do computador
  (exceto o que a pessoa pede pras fontes).
- README em inglês curto (opcional, ajuda a atrair contribuidor).

---

## 8. Decisões que são suas (com a minha recomendação)

| # | Decisão | Opções | Recomendo |
|---|---|---|---|
| **D1** | **Que tamanho tem o Fredify?** | (a) projeto aberto pra você, mestres e amigos, pelo GitHub; (b) app público na Play Store/lojas | **(a) agora, sem fechar a porta pra (b).** Muda o peso do nome, do YouTube e da loja. |
| **D2** | **Nome** | Fredify / um nome sem "-ify" | **Fredify**, com a busca no INPI antes de loja/logo. Slogan: "a calopsita que toca tudo". |
| **D3** | **O que vira o RPG** | Continua o centro / vira um pacote | **Pacote "Trilhas de jogo e RPG"** + climas gerais pra tudo. |
| **D4** | **Android** | Controle remoto / Python no celular / reescrever em Rust / player nativo | **Controle remoto primeiro, player nativo (Tauri + Media3) depois.** |
| **D5** | **Onde mora o cérebro** (pedido, busca, fila) | Só no Python (etapa D como estava) / Python + TypeScript com contrato / tudo em Rust | **Python + TypeScript com o teste de contrato.** O modo navegador sai do "congelado" e vira a base do Android sozinho. A etapa D muda: o chat do painel usa o cérebro TS no celular e o do Python no PC. |
| **D6** | **YouTube** | Fica como está / opcional e só no desktop / tirar | **Opcional, só no desktop baixado do GitHub, fora da versão da loja.** Arquivos locais viram a fonte principal. |
| **D7** | **Banco** | SQLite + FTS5 / outro (ex.: Postgres, busca externa) | **SQLite + FTS5**, com migração automática dos JSON. |
| **D8** | **A B2** | Fazer já / depois do banco / cortar | **Depois do banco e da biblioteca**, inteira. |
| **D9** | **Distribuir no Android** | APK no GitHub (+ Obtainium) / F-Droid / Play Store | **APK no GitHub primeiro** (exige o cadastro de desenvolvedor verificado do Google); Play Store só com a versão sem YouTube. |
| **D10** | **Mac** | Manter no CI / tirar do caminho | **Tirar do push de cada branch** (só nas Releases), "melhor esforço". |
| **D11** | **Vários mestres no mesmo Fredify** (antiga Fase 3) | Manter cedo / pro fim | **Pro fim** (vira "Fredify compartilhado"). |
| **D12** | **Trocar o identificador do app** (`io.github.marcelao98.freddy`) e a pasta (`~/.local/share/Freddy`) | Trocar / manter | **Trocar junto com o nome**, copiando a pasta antiga na primeira vez. Aviso: o instalador vira outro app (no Windows aparece como programa novo; o Freddy antigo tem que ser desinstalado). |

---

## 9. Roadmap de produto do Fredify

Ordem pensada pra entregar valor rápido. Cada fase é uma ou mais etapas no
jeito de sempre (pedido em `docs/etapas/`, commits por passo, Release).

### Fase 0 — Virar Fredify (pequena)
- Nome, identificador, pasta do usuário (com cópia da antiga), textos do app,
  `README`/`CLAUDE`/`ARQUITETURA`/`ROADMAP` com a visão nova.
- `CONTRIBUTING`, `SECURITY`, `CHANGELOG`, `THIRD_PARTY`, guia de quem usa.
- Mac fora do push de cada branch.
- **Pronto quando:** você instala o Fredify no Fedora por cima do Freddy, abre,
  e as playlists, os ajustes e o token do Discord continuam lá.

### Fase 1 — Toca o que é seu (banco + biblioteca local)
- SQLite + FTS5; migração automática de acervo, ajustes, aprendidas e
  playlists.
- Faixa com fonte (`youtube`, `arquivo`, `url`); fonte "arquivo" na Mesa
  (FFmpeg direto, sem yt-dlp).
- "Minha biblioteca": escolher pastas, ler as tags, rever só o que mudou.
- Busca em português em cima do banco (mesmos testes); painel com busca
  paginada; climas gerais + pacote RPG.
- **Pronto quando:** você aponta pra uma pasta com milhares de MP3/FLAC, pede
  "toca calmo e jazz" ou "toca queen" no chat e começa em menos de 1 s; os
  testes de busca de hoje passam sem mudar.

### Fase 2 — Tocador completo (a B2 + o que um tocador precisa)
- B2 inteira (avisos, lugar tocando, relógio único, camadas, sem silêncio,
  fila salva).
- Crossfade, volume igualado entre faixas, teclas de mídia (KDE/Windows),
  escolher a caixa de som, ícone na bandeja.
- **Pronto quando:** uma faixa emenda na outra sem silêncio nem salto de
  volume, o play/pause do teclado funciona, e a fila volta depois de fechar.

### Fase 3 — Soundboard
- Camada de efeitos por cima da música, pads com atalhos globais, cenas
  ("Taverna" = música + ambiente + pads), ducking.
- Efeitos dos arquivos da pessoa e do Freesound (CC0 por padrão, crédito
  guardado).
- **Pronto quando:** um trovão toca por cima da música na caixa e na call ao
  mesmo tempo, com a música abaixando sozinha.

### Fase 4 — O celular manda (Android controle remoto)
- Fredify do PC aceita a rede de casa com pareamento (QR code + senha); o
  Porteiro ganha o modo "com login".
- App Android (Tauri) com o mesmo painel.
- **Pronto quando:** do sofá, pelo celular, você pede música e dispara efeito
  e o som sai no PC e na call.

### Fase 5 — Toca em mais lugares
- Saída "rede": o som do Fredify em outro aparelho da casa, no navegador, no
  VLC, no celular.
- Mic virtual (a antiga etapa C): Zoom, Meet, OBS, Discord sem bot.
- Modo streamer (só faixas liberadas, contra DMCA na Twitch).
- **Pronto quando:** o mesmo som sai na caixa, no Discord e no mic virtual sem
  andar em dobro (um relógio só).

### Fase 6 — O celular toca sozinho (Android de verdade)
- Player nativo (Media3): segundo plano, notificação, tela bloqueada, fone.
- Banco no aparelho com o mesmo esquema; biblioteca do celular; as portas TS
  do pedido/busca/motor (o ex-modo navegador) com o contrato.
- Fontes abertas (Jamendo, rádios online). Sem YouTube na versão da loja.
- **Pronto quando:** sem PC nenhum, o celular toca a biblioteca dele em
  segundo plano e "toca triste" funciona igual ao PC.

### Fase 7 — Fredify compartilhado e loja
- Vários usuários num Fredify só (login pelo Discord, um lugar por servidor,
  pool de bots): a antiga Fase 3.
- Instaladores assinados, atualização automática, Play Store (se D1 for (b)).
- Chromecast/DLNA, Stream Deck/MIDI.

### Sempre em andamento
- Curadoria do pacote RPG (skill `chips`), plumagens, pendências antigas
  (loop da fila inteira, colar playlist do YouTube...).

---

## 10. Próximo passo

Você aprova (ou muda) as decisões D1–D12 e a ordem das fases. Aí eu escrevo
o pedido da **Fase 0** em `docs/etapas/`, atualizo o ROADMAP e começo.

### Fontes da pesquisa
- [GitHub: imtayadeway/fredify](https://github.com/imtayadeway/fredify)
- [fredify.net (This Is Fredi Fy)](https://www.fredify.net/)
- [IPWatchdog: Spotify vence a oposição contra Potify (2022)](https://ipwatchdog.com/2022/01/17/spotify-successfully-opposes-two-marijuana-related-trademark-applications/)
- [Law Street Media: Spotify se opõe a Opstify](https://lawstreetmedia.com/tech/spotify-opposes-opstify-trademark-as-likely-to-cause-confusion/)
- [Tauri: issue #9774, sidecar no celular](https://github.com/tauri-apps/tauri/issues/9774)
- [Tauri: Embedding External Binaries](https://v2.tauri.app/develop/sidecar/)
- [Android Authority: regras novas de instalar app fora da loja](https://androidauthority.com/android-open-source-apps-sideloading-oppose-3674808/)
- [Gigazine: NewPipe e o DMCA](https://gigazine.net/gsc_news/en/20230713-newpipe-dmca-google-search)
