# Roadmap do Projeto Frederico

O Freddy é o som da mesa de RPG: você pede a música em português, ele toca
pro seu Discord (ou pro seu microfone), e o mestre controla tudo por um
painel com a cara do Frederico, a calopsita de verdade.

Atualizado em 31/10/2026.

## Onde estamos

| Peça | Situação |
|---|---|
| **Cérebro musical** (Bardo: entender pedidos, buscar no acervo, fila, aprender faixa nova) | ✅ pronto, em uso na Natty |
| **Acervo** (607 faixas, 9 franquias, 27 climas) | ✅ pronto, curadoria contínua |
| **Painel** (modo Chat, modo Playlist, 5 plumagens) | ✅ pronto, toca sozinho pelo YouTube |
| **App desktop** (Tauri) com instaladores no GitHub (Windows, Linux, Mac) | ✅ pronto (v0.1.0) |
| **Backend próprio** (o Freddy sem a Natty) | ⬜ não começou |
| **Bot do Discord próprio do Freddy** | ⬜ hoje o som no Discord só existe pela Natty |
| **Mixer, microfone virtual, soundboard** | ⬜ só planejado (telas "em breve" no painel) |

## Como desenvolver sem sofrer

- **Testar o painel:** `cd frontend && npm run dev` e abrir http://localhost:5173.
  Recarrega sozinho a cada mudança. Não precisa de Rust nem de compilar.
- **App instalado:** só quando sai versão nova. O GitHub compila
  (`.github/workflows/app.yml`) e publica em Releases. Ninguém compila no PC.
- **Testes:** `cd frontend && npm test` e
  `cd backend && python -m unittest discover -s modules/bardo -t .`
  (o GitHub roda os dois antes de cada build).

## Fases

### Fase 0: Fundação ✅
- Bardo extraído da Natty com o histórico.
- Repositório dividido em `frontend/` e `backend/`.
- Painel React + TypeScript: Chat (pedidos sem LLM, mesmas regras da Natty),
  Playlist (acervo com filtros, fila arrastável, playlists salvas).
- Plumagens: Frederico (padrão), Lutino, Cinza silvestre, Canela, Cara-branca.
  Arte do Frederico gerada a partir das fotos dele.
- App Tauri e instaladores automáticos no GitHub.

### Fase 1: Backend próprio (o próximo passo)
O Freddy vira um programa Python que roda sozinho, sem a Natty.
- Servidor local (FastAPI + WebSocket) com o mesmo contrato do `Motor` que o
  painel já usa. No painel, troca o `MotorLocal` pelo `MotorRemoto`: uma linha.
- O acervo e as playlists salvas passam a morar no backend (um lugar só).
- Busca livre no YouTube e o "era essa?" que ensina faixa nova, agora no painel.
- O `yt-dlp` resolve o áudio: acaba o problema de vídeo bloqueado no player embutido.
- **Pronto quando:** o painel controla uma fila que mora no backend, com o app aberto ou no navegador.

### Fase 2: Bot do Discord do Freddy
O som chega na call sem a Natty.
- Bot próprio (o Cog do Bardo vira o bot do Freddy), tocando pelo backend.
- O painel escolhe a saída: este computador ou o Discord (servidor e canal).
- Pedidos digitados no Discord continuam funcionando (`@Freddy toca...`).
- Convivência com a Natty: ela pode mandar o Freddy tocar pela convenção 🎙
  (os módulos não se importam; conversam por mensagem).
- **Pronto quando:** um mestre toca música na call pelo painel, sem a Natty.

### Fase 3: Vários mestres no mesmo Freddy
Um Freddy ligado num PC de casa, atendendo todos os mestres.
- Login no painel pela conta do Discord (OAuth2). Cada um vê só os
  servidores onde tem permissão.
- Permissão por cargo do Discord (ex.: "Mestre") ou lista de pessoas.
- Fila e volume separados por servidor (o Bardo já faz isso).
- **Limite do Discord:** um bot fica em um canal de voz por servidor. Duas
  mesas ao mesmo tempo no mesmo servidor = um "pool" de contas de bot
  (Freddy 1, Freddy 2) e o backend distribui.
- Rodar num PC de casa (não em nuvem): o YouTube bloqueia IP de datacenter.
- Acesso ao painel de fora de casa (túnel seguro, ex.: Tailscale ou Cloudflare Tunnel).
- **Pronto quando:** dois mestres, cada um no seu servidor, controlam o som ao mesmo tempo.

### Fase 4: Mixer e microfone virtual
- Motor de áudio com camadas: música, ambiente (loops de chuva, taverna,
  masmorra) e efeitos, cada uma com seu volume.
- Crossfade entre faixas e ducking (a música abaixa quando um efeito toca ou
  quando o mestre fala).
- Saída "mic virtual": seu microfone + o som, num cabo virtual (VB-Cable no
  Windows, BlackHole no Mac, PipeWire no Linux). Serve pra Zoom, Meet e OBS,
  sem bot.
- Modo Mixer no painel (hoje "em breve").

### Fase 5: Soundboard e cenas
- Grade de pads com atalhos de teclado globais (funcionam com o jogo em
  primeiro plano, via Tauri); depois Stream Deck e MIDI.
- Cenas: "Taverna" = música calma + ambiente + os pads da cena, num clique.
- Fontes: arquivos do PC e Freesound (CC0 por padrão, créditos guardados).

### Fase 6: App redondo pra outros mestres
- O app sobe o backend sozinho (sidecar do Tauri): um programa só pra abrir.
- Ícone na bandeja, iniciar com o sistema, atualização automática.
- Instaladores assinados (some o aviso "o Windows protegeu o computador").
- Repositório público e licença revisada (hoje MIT, privado).
- Guia de instalação simples: baixar, abrir, conectar o Discord.

## Sempre em andamento
- **Acervo:** classificar as 37 faixas "não classificado", trilhas de taverna
  de verdade, completar Dark Souls, franquias novas (skill `chips`).
- **Plumagens:** arte das outras quatro (Lutino, Cinza, Canela, Cara-branca)
  com o mesmo prompt do Frederico; recorte com `frontend/scripts/recortar_ave.py`.
- **Pendências herdadas do Bardo:** loop da fila inteira, remover item pelo
  chat, colar playlist do YouTube, sair da call quando ficar vazia, erros mais
  claros (vídeo privado, idade), títulos com "volta"/"próxima" virando comando.

## Decisões em aberto
- **Nome:** Freddy, FredBOT ou Fredérico? (o app já se chama Freddy)
- **Bot:** um Freddy compartilhado por todos (Fase 3) ou cada mestre com o seu?
  A recomendação é compartilhado, num PC de casa.
- **Sistema principal:** Linux (Fedora, o PC do Marcelo) e Windows (a
  maioria dos mestres) são prioridade; Mac depois.
- **Quando abrir o repositório** pro público.
