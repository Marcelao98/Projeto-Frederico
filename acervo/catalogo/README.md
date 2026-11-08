# Catálogo do Fredify (fonte em CSV)

Etapa 1 do banco (`docs/etapas/banco-fredify.md`): o **vocabulário**. Na etapa 2
um script compila estes CSV no `catalogo.db` (SQLite) e confere as regras.
Separador `;`, listas dentro de um campo com `|`, UTF-8, com acento (o
compilador tira acento e caixa na hora de buscar).

| Arquivo | Tabela | O que tem |
|---|---|---|
| `generos.csv` | GENERO | árvore: `pai` vazio = família (23 famílias, 213 gêneros) |
| `tags.csv` | TAG | gavetas `clima` (28), `ocasiao` (47, 17 de RPG com prefixo `rpg-`), `tema` da letra (24), `instrumento` (18), `cenario` (14) |
| `ocasioes_perfil.csv` | OCASIAO_PERFIL | a cara de cada ocasião: gêneros (a família vale pros filhos), energia 1–5, `voz` (sim/nao/qualquer), climas que combinam e que evitar |
| `palavras.csv` | PALAVRA | o jeito que se fala: `palavra → tipo:alvo` com peso 0–1. Uma palavra pode apontar pra várias coisas (uma linha cada) |
| `mapa_tags_acervo.csv` | (migração) | pra onde foi cada uma das 226 tags do `acervo/musicas.json` |

Tipos de alvo em `palavras.csv` e no mapa: `genero`, `clima`, `ocasiao`, `tema`,
`instrumento`, `cenario` (ids destes arquivos), `epoca` (`1980-1989`,
`ate-1999`, `ultimos-3-anos`, `ultimos-12-meses`), `campo` (coluna da MUSICA:
`popularidade-alta`, `essencial`, `canta-junto`, `ao-vivo`, `acustico`,
`sem-voz`, `com-voz`, `nao-explicita`, `internacional`, `brasileira`). Só no
mapa: `artista`, `obra`, `descartar`, `revisar`.

Ids: minúsculas, sem acento, com hífen. Id é único entre todas as gavetas.
