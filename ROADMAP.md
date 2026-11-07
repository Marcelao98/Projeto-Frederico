# Roadmap do Projeto Frederico

O Freddy é o som da mesa de RPG: você pede a música em português, ele toca
pro seu Discord (ou pro seu microfone), e o mestre controla tudo por um
painel com a cara do Frederico, a calopsita de verdade.

Atualizado em 07/11/2026 (v0.6.0).

## Onde estamos

| Peça | Situação |
|---|---|
| **Cérebro musical** (entender pedidos, buscar no acervo, fila, aprender faixa nova) | ✅ pronto (`backend/freddy/nucleo/`) |
| **Acervo** (607 faixas, 9 franquias, 27 climas) | ✅ pronto, curadoria contínua |
| **Painel** (Chat, Playlist, Acervo, 5 plumagens) | ✅ pronto; toca pelo Freddy ou sozinho pelo YouTube |
| **App desktop** (Tauri) com instaladores no GitHub (Windows, Linux, Mac) | ✅ pronto (v0.5.x): liga o backend sozinho, sem terminal |
| **Backend próprio** | ✅ pronto, vai dentro do app |
| **Bot do Discord do Freddy** | ✅ toca na call desde a v0.5.2 (DAVE resolvido) |
| **Mixer, microfone virtual, soundboard** | ⬜ só planejado (telas "em breve" no painel) |

## Como desenvolver sem sofrer

- **Testar o painel:** `cd frontend && npm run dev` e abrir http://localhost:5173.
  Recarrega sozinho a cada mudança. Não precisa de Rust nem de compilar.
- **App instalado:** só quando sai versão nova. O GitHub compila
  (`.github/workflows/app.yml`) e publica em Releases. Ninguém compila no PC.
- **Backend + app na ordem certa:** `./freddy.sh` (`--sem-som` finge que toca).
- **Testes:** `cd frontend && npm test`, `cd backend && python -m unittest
  discover -s freddy -t .` e `python3 scripts/versao.py
  --conferir` (o GitHub roda tudo antes de cada build, mais o ponta a ponta).
- **Versão nova:** `python3 scripts/versao.py 0.5.6`, commit e push.

## Fases

### Fase 0: Fundação ✅
- O módulo de música da Natty vira o Freddy, com o histórico.
- Repositório dividido em `frontend/` e `backend/`.
- Painel React + TypeScript: Chat (pedidos em português, sem LLM),
  Playlist (acervo com filtros, fila arrastável, playlists salvas).
- Plumagens: Frederico (padrão), Lutino, Cinza silvestre, Canela, Cara-branca.
  Arte do Frederico gerada a partir das fotos dele.
- App Tauri e instaladores automáticos no GitHub.

### Fase 1: Backend próprio 🟡 (falta o teste com som no Fedora)
O Freddy vira um programa Python que roda sozinho, sem a Natty: `python -m freddy`.
- ✅ Servidor local (FastAPI + WebSocket, porta 47824) com o mesmo contrato do
  `Motor`. O painel acha o Freddy sozinho e usa o `MotorRemoto`; desligado,
  volta pro `MotorLocal` (navegador). Os casos do contrato rodam nos dois
  motores e, no GitHub, pela rede.
- ✅ O som sai do backend: yt-dlp → FFmpeg → Mesa → caixa de som
  (sounddevice). Formato de 20 ms/48 kHz/estéreo, o mesmo do Discord: a
  Fase 2 é só mais uma saída. Erros do YouTube em português.
- ✅ Acervo e playlists moram no backend (pasta do mestre). Na primeira vez,
  o painel oferece levar as playlists do navegador.
- ✅ Busca livre no YouTube e o "era essa?" no chat do painel (com botões);
  a faixa vai pro `aprendidas.json` e um script leva pro acervo oficial.
- ✅ Estudo do Kenku FM pro Discord: `docs/discord.md`.
- ✅ Arrumar o acervo (v0.3.0): modo **Acervo** (tabela editável), planilha
  CSV (baixa, edita no LibreOffice/Excel, manda de volta com resumo) e pelo
  chat (`temas`, `revisar`: o Freddy mostra os temas e você diz se tá certo).
  Correções vão pro `ajustes.json` do mestre; `acervo_promover.py` leva pro oficial.
- ✅ O chat conta o que muda fora dele (Playlist, barra, outra aba).
- ✅ Playlists salvas de verdade (v0.4.0): pelo chat (`playlists`, `toca a
  playlist X`, `põe a playlist X na fila`, `salva a fila como X`), editor
  sem mexer na fila, 📁 no acervo pra montar a playlist sem tocar, busca nas
  salvas e aviso quando não cabe tudo na fila.
- 🟡 Marcelo instalou no Fedora (31/10); falta confirmar o som saindo (e um mestre no Windows).
- **Pronto quando:** o painel controla uma fila que mora no backend, com o app aberto ou no navegador.

### Fase 2: Bot do Discord do Freddy ✅
O som chega na call pelo Freddy. Guia e detalhes em `docs/discord.md`.
- ✅ Bot próprio dentro do `python -m freddy` (`backend/freddy/integracoes/discord/`), com o
  jeito de conectar do Kenku FM: token colado no painel, lista de servidores
  e canais, um player que nunca para, "ouvir aqui também". O `cog.py` da
  Natty saiu (com o `@Natty`, o 🎙 do Echo e o "não sair da call").
- ✅ Janela Discord no painel: token, convite, servidor → canal → entrar/sair.
- ✅ `@Freddy toca…`, `pula`, `fila`, `volume`, playlists e `sai` no chat do
  Discord, na mesma fila do painel; avisa quando a fila anda; sai sozinho
  da call vazia depois de 5 minutos.
- ✅ Tocando na call (v0.5.2): a criptografia DAVE travava a call muda
  (`davey<0.2`); player do jeito do Kenku; 🐦 assobio de teste e Diagnóstico.
- **Pronto quando:** um mestre toca música na call pelo painel.

### Fase 3: Vários mestres no mesmo Freddy
Um Freddy ligado num PC de casa, atendendo todos os mestres.
- Login no painel pela conta do Discord (OAuth2). Cada um vê só os
  servidores onde tem permissão.
- Permissão por cargo do Discord (ex.: "Mestre") ou lista de pessoas.
- Fila e volume separados por servidor (uma sala por servidor: `backend/freddy/salas/`).
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
- ✅ O app sobe o backend sozinho (sidecar do Tauri): um programa só pra abrir, sem terminal (v0.5.3, 03/11/2026). Falta: Mac Intel, abrir mais rápido, yt-dlp que se atualiza.
- Ícone na bandeja, iniciar com o sistema, atualização automática.
- Instaladores assinados (some o aviso "o Windows protegeu o computador").
- ✅ Repositório público e licença GPL-3.0 (01/11/2026).
- Guia de instalação simples: baixar, abrir, conectar o Discord.

## Sempre em andamento
- **Acervo:** classificar as 37 faixas "não classificado", trilhas de taverna
  de verdade, completar Dark Souls, franquias novas (skill `chips`).
- **Plumagens:** por enquanto todas usam a arte do Frederico (pedido do
  Marcelo). Arte própria das outras quatro é opcional: mesmo prompt do
  Frederico no Gemini, recorte com `frontend/scripts/recortar_ave.py`.
- **Pendências antigas:** loop da fila inteira, remover item pelo
  chat, colar playlist do YouTube, títulos com "volta"/"próxima" virando comando.

## Arrumação da casa (07/11/2026)
Revisão geral do código e da arquitetura. A **etapa A** (v0.5.5):
- ✅ Segurança: o Porteiro (`api/porteiro.py`). Antes, qualquer site aberto
  no navegador conseguia reescrever o acervo ou tirar o bot da call.
- ✅ Convite do bot e Developer Portal abrem no app (`POST /abrir`).
- ✅ Versão num comando só (`scripts/versao.py`) e conferida no GitHub.
- ✅ Documentação em dia; `main` como branch principal; workflow em
  qualquer branch `claude/**`.

A arquitetura nova (aprovada em 07/11/2026) está em `docs/ARQUITETURA.md`:
- ✅ **Etapa B1** (v0.6.0): a estrutura nova de pastas (as regras viraram
  `backend/freddy/nucleo/`, o acervo foi pra `acervo/` na raiz, rotas
  divididas, CSS por tela); o yt-dlp do app se atualiza sozinho; o painel
  espera o backend que o app ligou; o GitHub liga o backend empacotado antes
  de virar app.
- ⬜ **B2:** Sala, relógio único, saídas plugáveis, Mesa com camadas, próxima
  música procurada antes, fila salva.
- ⬜ **C:** mic virtual. ⬜ **D:** um cérebro só pro chat.

## Decisões tomadas
- **O Freddy é o áudio do Nattyverso.** A Natty não toca mais nada e não
  precisa mudar: o módulo de música que veio de lá é do Freddy agora e não
  fica em sincronia com a natty-bot. (31/10/2026)
- **Bot:** um Freddy compartilhado pelos mestres, rodando num PC de casa (Fase 3). (31/10/2026)
- **Sistemas:** Linux e Windows são prioridade; Mac depois. (31/10/2026)
- **Quem toca:** o backend toca o som ele mesmo (não o navegador), num formato
  único que serve à caixa de som, ao Discord e ao mixer. (31/10/2026)
- **Faixa aprendida:** vai pra um arquivo na pasta do mestre, não direto pro
  `musicas.json`; um script promove pro acervo oficial. (31/10/2026)
- **Sem o Freddy ligado:** o painel continua tocando sozinho pelo navegador. (31/10/2026)

## Licença
- **GPL-3.0** (01/11/2026): o Freddy é open source por natureza. Permite usar
  código do Kenku FM (também GPL-3.0) com crédito, e quem fizer algo em cima
  do Freddy também tem que abrir o código. Não impede ganhar dinheiro no
  futuro (vender o app pronto, doações, suporte); só impede fechar o código.

## Decisões em aberto
- **Nome:** Freddy, FredBOT ou Fredérico? (o app já se chama Freddy)
