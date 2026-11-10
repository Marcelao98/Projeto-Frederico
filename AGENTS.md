# AGENTS.md (Codex e outros agentes)

As regras do projeto estão no **`CLAUDE.md`**: leia ele inteiro antes de
mexer em qualquer coisa (vale pra qualquer agente, não só o Claude). Depois,
o `ROADMAP.md` ("Onde paramos") e o `docs/ARQUITETURA.md`.

Resumo do que não pode esquecer:

- Responder em português do Brasil, direto, sem jargão. O usuário é o
  Marcelo (Fedora KDE: sem `apt`).
- Testes antes de commitar:
  `cd frontend && npm test && npm run build`,
  `cd backend && python -m unittest discover -s freddy -t .`,
  `python3 scripts/versao.py --conferir`.
- Encher o catálogo (etapa 3 do banco): `acervo/catalogo/blocos/ORQUESTRACAO.md`
  e `PROMPT_AGENTE.md`.
- Nunca commitar token, `.env`, `discord.json` ou dados da pasta do mestre.
- Licença GPL-3.0.
