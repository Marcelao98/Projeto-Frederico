# Arquitetura do Freddy

O som da mesa de RPG: o mestre pede música em português, o Freddy toca na
caixa de som ou na call do Discord, e tudo é controlado por um painel.

## As quatro ideias

1. **O backend é o Freddy; o resto é tela.** Toda decisão (a fila, o que
   tocar, entender um pedido) mora no backend. O painel, o Discord e, no
   futuro, um Stream Deck só mandam pedidos e mostram o resultado.
2. **Plugável nas pontas.** De onde vem o som (`audio/fontes/`), pra onde
   vai (`audio/saidas/`) e quem controla (`integracoes/`) são peças
   separadas: coisa nova entra como peça nova, sem mexer no meio.
3. **Uma sala é uma mesa de RPG tocando** (`salas/`): a fila e o som dela.
   Hoje existe uma; na Fase 3, uma por servidor do Discord.
4. **Contratos conferidos por máquina.** O contrato do motor roda nos dois
   lados (`casos_contrato.json`); o Porteiro tem os ataques como teste; a
   versão é conferida no GitHub; o backend empacotado é ligado de verdade
   antes de virar app.

## O desenho

```
┌──────────────── App Freddy (um instalador) ─────────────────┐
│ Casca Tauri (Rust, frontend/src-tauri/): a janela; liga e   │
│   desliga o backend sozinho (sidecar)                       │
│                                                             │
│ Painel (React, frontend/src/): só tela                      │
│        │  WebSocket /ws (o motor) + REST (acervo, playlists,│
│        │  Discord, planilha)                                │
│        ▼                                                    │
│ Backend (Python, backend/freddy/, empacotado no app)        │
│   api/           o Porteiro + rotas por assunto + /ws       │
│   conversa/      o cérebro do chat                          │
│   salas/         a fila e os comandos (o motor)             │
│   audio/         fontes → Mesa → saídas                     │
│   integracoes/   o bot do Discord                           │
│   nucleo/        as regras: pedido, busca, vocabulário      │
│   dados/         acervo, playlists, planilha, token         │
└─────────────────────────────────────────────────────────────┘
        acervo/  (raiz): musicas.json + vocabulario.json, lidos pelos dois lados
```

## Pastas

```
acervo/                     o acervo oficial (fonte única; painel: alias @acervo)
├── musicas.json, vocabulario.json
└── tracklists/

backend/
├── freddy/
│   ├── __main__.py         python -m freddy
│   ├── config.py           porta, pastas, PASTA_ACERVO, origens permitidas
│   ├── nucleo/             regras puras (sem rede, som ou Discord)
│   │   ├── texto.py        normalizar, slug, links do YouTube
│   │   ├── pedido.py       "toca triste e bloodborne", "pula", "volume 30"
│   │   ├── vocabulario.py  temas → as 27 categorias
│   │   └── busca.py        busca booleana (e / ou / sem) e o sorteio de 15
│   ├── conversa/           o cérebro do chat (hoje: o Discord)
│   ├── salas/              o motor (comandos da fila) e a fila; o contrato
│   ├── audio/
│   │   ├── pcm.py          o formato: 20 ms, 48 kHz, estéreo, 16 bits
│   │   ├── mesa.py         onde o som é montado (o relógio e a cópia)
│   │   ├── reprodutor*.py  quem manda a Mesa tocar (o de verdade e o falso)
│   │   ├── fontes/         youtube.py, ytdlp.py (se atualiza), ffmpeg.py, assobio.py
│   │   └── saidas/         caixa.py, discord.py, muda.py
│   ├── integracoes/discord/  o bot
│   ├── dados/              acervo (+ ajustes e aprendidas do mestre), acervo_oficial,
│   │                       playlists, planilha, segredos, arquivos
│   └── api/                app.py (monta), porteiro.py, ws.py, rotas/
├── scripts/                manutenção do acervo: acervo_*.py
└── freddy_backend.py       o ponto de partida do backend empacotado

frontend/
├── src/
│   ├── api/                falar com o Freddy: freddy.ts (REST), motorRemoto.ts (/ws)
│   ├── motor/              o contrato do motor (tipos, contexto do React, casos)
│   ├── estado/             o que a tela guarda: acervo, playlists, temas, preferências
│   ├── modos/              uma pasta por tela (chat, playlist, acervo, mixer), cada uma com seu .css
│   ├── componentes/        barra do player, calopsita, janela do Discord...
│   ├── comum/              tipos, texto, links do YouTube
│   ├── navegador/          o modo reserva (sem o Freddy): MotorLocal + portas de pedido/busca
│   └── estilo/             base.css, temas.css (plumagens), telas-menores.css
└── src-tauri/              a casca em Rust

docs/                       ARQUITETURA.md (este), discord.md
scripts/versao.py           a versão nos 6 arquivos de uma vez
freddy.sh                   pra desenvolver: backend + app na ordem certa
```

## Regras que seguram isso de pé

- **Comando novo do motor** = `Comandos` (frontend/src/motor/tipos.ts) + o
  motor do backend (salas/motor.py) + a validação (api/protocolo.py) + um
  caso em `salas/casos_contrato.json`. O MotorLocal (modo reserva) também,
  enquanto ele existir.
- **`nucleo/` não importa nada de rede, som ou Discord.** `conversa/` usa o
  núcleo e o motor, sem discord.py; `integracoes/discord/` só traduz.
- **Rota nova** mora em `api/rotas/<assunto>.py` e usa `request.app.state`.
  O Porteiro já protege.
- **Dados do mestre** só na pasta dele (`~/.local/share/Freddy`,
  `%APPDATA%\Freddy`), nunca no git. As categorias sempre saem dos temas.
- **Um relógio só:** uma saída manda no ritmo da Mesa (o Discord, se ele
  estiver tocando; senão a caixa) e as outras tocam a cópia.
- **O modo navegador está congelado:** funciona sem o Freddy, mas função nova
  é só pelo Freddy.

## Etapas

| Etapa | O que entra | Situação |
|---|---|---|
| A | segurança (Porteiro), docs, versão num comando, `main` | ✅ v0.5.5 |
| B1 | esta estrutura; o yt-dlp que se atualiza; o painel espera o backend; teste do backend empacotado | ✅ v0.6.0 |
| B2 | Sala (fila + Mesa + saídas), relógio único e saídas plugáveis, Mesa com camadas, procurar a próxima música antes, fila salva ao fechar, avisos internos (eventos). Pedido completo: `docs/etapas/B2.md` | próxima |
| C | mic virtual (mais uma saída) | |
| D | um cérebro só: o chat do painel no backend; tipos do painel gerados do Python | |
| depois | mixer e soundboard (camadas) ou vários mestres (salas) | |

### Decisões

- **Backend em Python dentro do app** (não reescrever em Rust): as peças
  difíceis (yt-dlp, a voz do Discord com DAVE) só existem em Python, e quem
  usa não vê diferença.
- **Executável único** (PyInstaller `--onefile`) por enquanto: funciona e é
  testado no GitHub. Trocar pra pasta (abre mais rápido) só se a demora
  incomodar de verdade; o painel já espera o backend acordar.
- **yt-dlp atualizado em tempo de uso** (só no app instalado), do GitHub
  oficial, com SHA-256 conferido e volta pro do app se quebrar.
- **Mac fica de lado** (Linux e Windows primeiro). Mac Intel não tem backend.
