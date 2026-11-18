# Etapa: +5 mil trilhas instrumentais (jogo, anime, filme, Ghibli) no catálogo

Pedido do Marcelo (18/11/2026): 10 mil músicas no total, **5 mil "tradicionais"
(já feitas) + 5 mil instrumentais** com foco em **RPG de mesa** (masmorra,
taverna, chefe...) e **dia a dia** (estudar, ler, relaxar, dormir).
Vocabulário novo aprovado (climas `heroico`, `aventureiro`; cenários
`montanha`, `pantano`, `campo`, `vila`, `navio`, `ceu`; ocasiões `rpg-viagem`,
`ler`; coluna `estavel`).

## A regra de ouro: a IA não escreve nome de faixa
Nome e link vêm da **playlist do YouTube** (o script extrai). A IA só
**classifica**. Assim não existe faixa inventada.

## Arquivos
- `acervo/catalogo/ost/obras.csv`: as ~195 obras (id, nome, tipo, ano,
  compositor, apelidos, grupo, meta, playlist, nota). O Marcelo corta e
  acrescenta. `apelidos` repetidos em várias obras (`ghibli`, `zelda`,
  `souls`) viram palavra de busca pra todas elas.
- `acervo/catalogo/ost/faixas/<id>.csv`: as faixas reais + a classificação.

## O comando (de `backend/`)
```bash
python scripts/catalogo_ost.py status              # o que falta e o total (meta 5000)
python scripts/catalogo_ost.py extrair             # todas que faltam (ou: extrair id1 id2)
python scripts/catalogo_ost.py mostrar <id>        # lista enxuta pra classificar
python scripts/catalogo_ost.py marcar <id> arq.txt [--resto-fora]
python scripts/catalogo_ost.py importar            # catálogo + compila + pedidos de ouro
python scripts/catalogo_ost.py links               # confere se os vídeos estão no ar (todas as 10 mil)
```
Playlist errada? Ponha o link certo (playlist ou `…/@canal/videos`) na
coluna `playlist` do `obras.csv` e rode `extrair <id>` de novo.

## Como classificar (uma linha por faixa)
`ordem|uso|cenarios|climas|energia|animacao|flags|instrumentos|ocasioes|popularidade|nota`

- **uso** (0–3, só `rpg-*`): taverna, cidade, exploracao, masmorra, combate,
  chefe, vilao, terror, misterio, corte, ritual, descanso, drama, abertura,
  final, perseguicao, humor, viagem. A pergunta: *em que cena da mesa eu
  tocaria isso?*
- **cenarios** (0–3): castelo, caverna, ruinas, floresta, mar, deserto, neve,
  chuva, vulcao, cidade-grande, templo, noite, espaco, cemiterio, montanha,
  pantano, campo, vila, navio, ceu.
- **climas** (2–4, o mais forte primeiro): ids da gaveta clima de `tags.csv`.
- **energia** 1–5 (1 dormir, 5 pancada) e **animacao** 1–5 (1 muito triste, 5 eufórica).
- **flags**: `V` tem voz (coral com letra conta), `S` estável (sem susto nem
  pico de volume: serve de fundo e pra estudar), `E` a mais famosa da obra,
  `X` fora (repetida, vinheta, versão piano/cover, jingle, excesso).
- **ocasioes** (dia a dia, sem `rpg-`): foco, ler, relaxar, dormir, meditar,
  dia-chuvoso, acordar, jogar, treino...
- **popularidade** 0–100: quanto a faixa é conhecida *entre quem joga/assiste*.

Pistas boas: o nome da faixa ("Boss", "Town", "Dungeon", "Requiem"), o lugar
do jogo onde toca, o compositor. Na dúvida, menos marcas e certas.
Exemplo completo e conferido: `ost/faixas/ghibli-chihiro.csv`.

## Metas
Cada obra tem uma `meta` (soma ~4.200 + as 560 de RPG antigo). A playlist
costuma ter mais: escolha as melhores até ~1,2× a meta e use `--resto-fora`.

## Pra gastar pouco
Uma sessão, **sem subagentes**; uma obra por vez; `importar` e commit a cada
~5 obras; `status` mostra onde parou. Rode `extrair` (todas) logo no começo:
não gasta token.
