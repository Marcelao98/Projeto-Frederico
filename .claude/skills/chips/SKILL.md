---
name: chips
description: Expande o dataset de músicas do módulo Bardo (extrai playlist do YouTube, tagueia clima/tema, mescla no musicas.json). Use quando o Marcelo pedir pra adicionar uma nova playlist/franquia/gênero ao dataset do Bardo, ou pra classificar faixas "não classificado".
---

# Chips — pipeline de dataset do Bardo

"Chip" aqui é no sentido de módulo plugável pra Natty: essa skill é o chip
que sabe fazer manutenção do dataset de músicas do módulo Bardo
(`modules/bardo/dataset/musicas.json`). Roda local, porque só a máquina do
Marcelo tem acesso de rede real ao YouTube (o sandbox de nuvem onde o
Claude às vezes trabalha nisso tem yt-dlp bloqueado por proxy).

Não confundir com os módulos de verdade do bot (`modules/bardo`,
`modules/core`, `modules/dice` — cogs carregados pelo `bot.py`). Chips é
puramente uma skill de manutenção de dados, não é carregada pelo bot.

## Quando usar

- Marcelo manda uma playlist nova do YouTube pra virar parte do dataset
  (ex: "bota essa playlist de Hollow Knight completa", "quero sertanejo
  também agora").
- Marcelo pede pra classificar faixas que estão com `"temas": ["não
  classificado"]`.
- Qualquer expansão do dataset que seguiria o mesmo padrão: extrair →
  tagueiar → mesclar.

## O pipeline (3 etapas)

### Etapa 1 — Extrair

```bash
python scripts/bardo_extrair_playlist.py "<url da playlist>" \
    --origem-nome "Nome do Jogo/VN/Anime" \
    --origem-tipo jogo \
    --saida staging/<nome_curto>.json
```

- `--origem-tipo` é um de: `jogo`, `visual novel`, `anime`, `outro`.
- Isso roda `yt-dlp --flat-playlist` (não baixa áudio, só lista metadados —
  rápido mesmo em playlist de 200+ faixas) e gera um JSON de staging com
  todas as faixas, id já calculado, e `"temas": ["não classificado"]` como
  placeholder.
- **Staging fica fora do dataset de verdade** (`staging/` não é lido pelo
  bot) — dá pra revisar/corrigir sem risco de quebrar produção.

### Etapa 2 — Tagueiar (a parte que não dá pra automatizar 100%)

Abra o JSON de staging e, pra cada faixa, troque `["não classificado"]"`
por 2 a 5 temas reais. Isso é julgamento — o Marcelo já topou que vai errar
tag às vezes e vai ajustar depois manualmente, então não trave por
perfeição, mas siga estas regras:

1. **Reuse o vocabulário existente sempre que possível.** A busca booleana
   do Bardo é por substring exato — inventar sinônimo novo ("triste" vs
   "trágico" vs "melancólico") fragmenta a busca em vez de enriquecer ela.
   Antes de inventar um tema novo, rode:
   ```bash
   python3 -c "
   import json, collections
   d = json.load(open('modules/bardo/dataset/musicas.json', encoding='utf-8'))['musicas']
   c = collections.Counter(t for m in d for t in m['temas'])
   for tema, n in c.most_common(): print(n, tema)
   "
   ```
   e prefira um termo que já apareça ali. Vocabulário mais usado hoje
   (pra não precisar rodar toda vez): melancólico, sombrio, tenso, calmo,
   batalha, boss fight, épico, intenso, dramático, emocionante, vocal,
   final, mistério, trágico, leve, sereno, elegante, triste, cotidiano,
   exploração, grandioso, estratégia, esperançoso, heroico, nostálgico,
   etéreo, clímax, perturbador, alegre, cômico, coral, contemplativo,
   sagrado, introspectivo, dinâmico, terror, tema principal, atmosférico,
   urgente, hub, duelo, abertura, masmorra, morte, orquestral, piano.
2. **Tema de gameplay/contexto conta tanto quanto clima.** "boss fight",
   "hub", "exploração", "duelo", "menu", "abertura" são tão válidos quanto
   "triste"/"épico" — é o que permite busca tipo "toca boss fight e elden
   ring".
3. **Sem fonte, não chuta.** Se o nome da faixa é críptico (comum em
   Umineko/Subahibi — títulos tipo "Core", "Mind", "Dir") e não há review
   de fã, letra ou contexto que sustente uma tag, deixe `["não
   classificado"]` mesmo. Tag errada é pior que faixa sem tag, porque
   contamina resultado de busca silenciosamente.
4. **`escopo`**: praticamente sempre `"faixa_individual"` pra faixa que
   veio de playlist. Só usa `"album_completo"` se for uma entrada única
   representando o álbum inteiro (raro, evite — o Marcelo pediu
   granularidade por faixa explicitamente).
5. **`comentario_pessoal`**: deixa `""` a menos que o Marcelo tenha dito
   algo específico sobre aquela faixa na conversa — esse campo é a opinião
   pessoal dele, não uma descrição gerada.

### Etapa 3 — Mesclar

```bash
python scripts/bardo_mesclar_dataset.py staging/<nome_curto>.json --dry-run
# confere a contagem, aí roda de verdade:
python scripts/bardo_mesclar_dataset.py staging/<nome_curto>.json
```

O script valida schema, nunca sobrescreve entrada existente (checa id E
link), e é seguro rodar de novo em cima do mesmo staging (idempotente).

Depois do merge, roda os testes pra garantir que não quebrou nada:

```bash
python -m unittest discover -s modules/bardo -t .
```

## Reclassificar faixas "não classificado" já existentes

Não precisa do pipeline completo — é edição direta em
`modules/bardo/dataset/musicas.json`: ache a entrada pelo `id` ou `nome`,
troque o array `temas`. Só lembra da regra 1 (reusar vocabulário) e da
regra 3 (sem fonte, não chuta) acima.

## No final

Sempre feche explicando pro Marcelo, em português, o que foi feito e por
quê — não só rodar os comandos calado. Ele quer entender a decisão de
tagueamento (por que essa tag, de onde veio), não só ver o resultado. Se
sobrar faixa sem classificar por falta de fonte confiável, lista elas
separado e explica que precisa da memória/opinião dele ali — fandom não
documenta clima musical faixa a faixa, então tem limite real no que dá pra
automatizar.
