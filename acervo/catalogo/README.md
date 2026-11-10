# Catálogo do Fredify (fonte em CSV)

O banco de músicas do Fredify (`docs/etapas/banco-fredify.md`). Estes CSV são a
fonte; o `catalogo.db` (SQLite + FTS5) sai deles e não vai pro git:

```bash
cd backend
python -m freddy.catalogo.compilar --conferir   # só confere as regras
python -m freddy.catalogo.compilar              # gera acervo/catalogo.db
python -m unittest freddy.catalogo.test_catalogo   # regras + pedidos de ouro
```
Separador `;`, listas dentro de um campo com `|`, UTF-8, com acento (o
compilador tira acento e caixa na hora de buscar).

| Arquivo | Tabela | O que tem |
|---|---|---|
| `generos.csv` | GENERO | árvore: `pai` vazio = família (23 famílias, 213 gêneros) |
| `tags.csv` | TAG | gavetas `clima` (28), `ocasiao` (47, 17 de RPG com prefixo `rpg-`), `tema` da letra (24), `instrumento` (18), `cenario` (14) |
| `ocasioes_perfil.csv` | OCASIAO_PERFIL | a cara de cada ocasião: gêneros (a família vale pros filhos), energia 1–5, `voz` (sim/nao/qualquer), climas que combinam e que evitar |
| `palavras.csv` | PALAVRA | o jeito que se fala: `palavra → tipo:alvo` com peso 0–1. Uma palavra pode apontar pra várias coisas (uma linha cada) |
| `mapa_tags_acervo.csv` | (migração) | pra onde foi cada tag do `acervo/musicas.json` |
| `musicas.csv` | MUSICA | uma linha por música; `lote` diz de onde veio (`rpg-legado` = as 560 do musicas.json), `revisar=1` = sem classificação ainda |
| `obras.csv`, `artistas.csv` | OBRA, ARTISTA | `apelidos` da obra (separados por `\|`) também viram palavra |
| `musica_genero.csv`, `musica_tag.csv`, `musica_artista.csv` | ligações | peso 0–1; `quem_marcou`: `curadoria` (o Marcelo), `claude` (inferido) |
| `fontes.csv` | FONTE | onde tocar; `oficial`/`viva` conferidos na etapa 3 |
| `pedidos_de_ouro.csv` | (teste) | frases reais: o que tem que entender e o que tem que (e não pode) aparecer |

As 560 faixas de RPG vêm do `musicas.json` pelo `backend/scripts/catalogo_migrar_rpg.py`
(roda de novo sem problema; ele reescreve os CSV de música). Até a etapa 4 o app
continua usando o `musicas.json`.

**Regras** (o compilador barra): ids e referências válidos, toda ocasião com
perfil, toda música com gênero, energia, animação, ≥ 2 climas, popularidade,
ano e fonte oficial viva. Pro `rpg-legado`, ano e fonte oficial são aviso; música
com `revisar=1` não precisa de clima nem energia.

**Pedidos de ouro:** `entende` = alvos que a consulta tem que reconhecer (`!` =
negado; partes do "e depois" separadas por ` > `); `deve`/`nao_pode` = condições
nas 10 primeiras de cada parte (`tipo:alvo`, `energia>=4`). Se nenhuma música
do catálogo cumpre o `deve`, o resultado fica pendente (música geral antes da
etapa 3); o `entende` é conferido sempre.

Todo nome de gênero, tag, obra (e apelido) e artista vira palavra sozinho na compilação.
Tipos de alvo em `palavras.csv` e no mapa: `genero`, `clima`, `ocasiao`, `tema`,
`instrumento`, `cenario` (ids destes arquivos), `epoca` (`1980-1989`,
`ate-1999`, `ultimos-3-anos`, `ultimos-12-meses`), `campo` (coluna da MUSICA:
`popularidade-alta`, `essencial`, `canta-junto`, `ao-vivo`, `acustico`,
`sem-voz`, `com-voz`, `nao-explicita`, `internacional`, `brasileira`). Só no
mapa: `artista`, `obra`, `descartar`, `revisar`.

Ids: minúsculas, sem acento, com hífen. Id é único entre todas as gavetas.
