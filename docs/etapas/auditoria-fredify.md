# Auditoria: do Freddy ao Fredify

Pedido do Marcelo em 07/11/2026. **É uma auditoria e um plano, não código:**
mostrar o resultado pro Marcelo e esperar a aprovação antes de mudar
qualquer coisa.

## A visão nova

O Freddy deixa de ser "o som da mesa de RPG" e vira o **Fredify**: um
**tocador de música universal**. RPG é um dos usos, não o único.

- **Música e efeitos sonoros** (soundboard), com tudo que uma pessoa
  precisa num tocador, de forma dinâmica (filas, playlists, misturar
  música com efeitos, climas).
- **Plataformas:** Windows, Linux, Android (e PC em geral).
- **Toca em vários lugares:** no próprio aparelho, numa call do Discord (o
  bot que já existe) e em outras plataformas.
- **Banco de dados** pra facilitar a busca e a pesquisa direta (hoje o
  acervo é um `musicas.json` de 607 faixas de trilhas de jogo/anime,
  marcadas por clima).
- O mascote continua o Frederico (a calopsita), e as plumagens também.

## O que auditar

1. **O que existe hoje e serve pra visão nova** (ler `CLAUDE.md`,
   `docs/ARQUITETURA.md`, `ROADMAP.md`, o código e a documentação toda):
   o que reaproveitar, o que é específico de RPG e precisa generalizar, o
   que sobra.
2. **Arquitetura pras plataformas novas.** Pontos que pesam:
   - **Android:** hoje o app (Tauri) leva o backend em Python empacotado
     junto (sidecar). Isso não roda no Android. Avaliar as saídas: o Android
     como controle remoto de um Fredify num PC, reescrever o núcleo (Rust,
     Kotlin), Python embutido no Android (ex.: Chaquopy), tocar direto no
     aparelho... e o custo de cada uma.
   - **O som:** a Mesa (quadros de 20 ms, 48 kHz, estéreo) e as saídas
     (caixa, Discord, mic virtual planejado) servem pra um tocador universal?
     A etapa B2 (`docs/etapas/B2.md`) ainda é o próximo passo certo?
   - **"Outras plataformas":** quais faz sentido (Discord já tem; ex.:
     Twitch/OBS, chamadas no Zoom/Meet pelo mic virtual, Chromecast/DLNA,
     tocar em outro aparelho da casa) e o que cada uma pede.
3. **Banco de dados e busca:** trocar o JSON por banco (ex.: SQLite com
   busca de texto, FTS5) sem perder o que existe: os climas/categorias, a
   busca em português ("toca triste e bloodborne"), as correções do mestre
   (`ajustes.json`), as faixas aprendidas, as playlists. Como escala pra
   milhares de faixas e pra biblioteca da própria pessoa (arquivos do PC).
4. **De onde vem a música:** hoje é YouTube via yt-dlp. Pra um tocador
   público e distribuído (lojas de app, Play Store), avaliar com
   honestidade os riscos (termos do YouTube, regras das lojas sobre
   "baixar do YouTube", bloqueio de IP) e as alternativas (arquivos locais,
   Jamendo/Free Music Archive, Freesound pros efeitos, outras APIs).
5. **O nome "Fredify":** conferir se não esbarra em marca registrada
   (a semelhança com o Spotify) ou em app/domínio que já exista. Só
   avaliar; quem decide é o Marcelo.
6. **Documentação:** o que está desatualizado, o que falta pra um projeto
   aberto (GPL-3.0) que outras pessoas vão usar e talvez contribuir.

## O que entregar

- **Relatório da auditoria:** como está, o que serve, os riscos, as
  decisões que o Marcelo precisa tomar (com uma recomendação pra cada).
- **Um roadmap de produto do Fredify:** fases em ordem, cada uma com o que
  entra e o "pronto quando", começando pelo que dá valor mais rápido.
- **Nada de código nem renomear arquivos** antes do Marcelo aprovar o plano.
- O usuário é o Marcelo: português do Brasil, informal, direto, sem
  jargão. Ele usa Fedora KDE; a maioria dos usuários vai estar no Windows
  e no Android.
