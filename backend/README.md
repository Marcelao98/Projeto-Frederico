# Backend do Freddy

Hoje é o **Bardo**, o módulo de música da Natty: Python, `discord.py`,
`yt-dlp` e FFmpeg. O som só existe pelo Discord por enquanto.

```
backend/
├── modules/bardo/          o Bardo (service.py, cog.py, youtube.py) e testes
│   └── dataset/            musicas.json + vocabulario.json: o acervo
├── scripts/                manutenção do acervo (extrair playlist, mesclar, categorizar)
├── data/                   tracklists exportadas
└── requirements.txt
```

O acervo em `modules/bardo/dataset/` é a fonte única: o frontend importa os
mesmos JSON (alias `@dataset` em `frontend/vite.config.ts`). Mover ou
renomear essa pasta quebra o frontend.

Todos os comandos rodam **de dentro de `backend/`**:

```
pip install -r requirements.txt
python -m unittest discover -s modules/bardo -t .
python scripts/categorizar_musicas.py
```

O que vem: o motor de áudio (mixer, mic virtual, bot próprio do Discord) e
uma API (WebSocket) que o frontend usa no lugar do player do navegador.
