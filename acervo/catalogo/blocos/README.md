# Blocos da etapa 3 (encher o catálogo)

As listas de músicas do Fredify (`docs/etapas/banco-fredify.md`), já com as tags.
Tudo de uma vez: o Claude gera todas as listas; o Marcelo roda **um comando** no
computador dele; o Claude lê o relatório e arruma o que precisar.

| Arquivo | O quê |
|---|---|
| `bloco-NN.csv` | a lista (o Claude gera): artista, título, ano, gênero e as tags |
| `bloco-NN.musicbrainz.csv` | o que o MusicBrainz diz (ano de verdade, mbid, duração) |
| `bloco-NN.youtube.csv` | o link oficial escolhido e por quê |
| `pendentes.csv` | as que ficaram de fora (sem upload oficial no YouTube) |
| `relatorio.md` | o resumo da última rodada |
| `REGRAS_PARA_GERAR.md` | como gerar uma lista (vai no pedido de cada subagente) |
| `rascunhos/` | o que os subagentes deixaram antes de parar (ver `docs/etapas/banco-fredify-etapa3.md`) |

Blocos: 01 essenciais (de tudo) · 02 MPB e soul BR · 03 samba e pagode ·
04 sertanejo · 05 forró, axé, brega e regionais · 06 rock e pop BR ·
07 funk, rap, gospel e infantil · 08 pop internacional e latina ·
09 rock internacional · 10 black music, jazz, reggae e hip hop ·
11 eletrônica, baladas, trilhas, clássica e mundo.

## O comando (no computador do Marcelo, de dentro de `backend/`)

```bash
python scripts/catalogo_bloco.py
```

Confere tudo no MusicBrainz e no YouTube (ao mesmo tempo), põe no catálogo as
que têm link oficial (com o ano corrigido), compila, roda os pedidos de ouro,
escreve o `relatorio.md` e faz commit + push no `main`. Umas 3 horas pra 5 mil;
pode parar e rodar de novo que continua. `--so-importar` refaz só o fim;
`--sem-enviar` não manda pro GitHub.

## Formato da lista

`artista;titulo;ano;genero;genero2;feat;idioma;tem_voz;energia;animacao;climas;ocasioes;temas;instrumentos;popularidade;essencial;canta_junto;explicita;ao_vivo;nota`

Ids de `../generos.csv` e `../tags.csv`; listas com `|`. Conferir uma lista:
`python -m freddy.catalogo.bloco conferir ../acervo/catalogo/blocos/bloco-NN.csv`.
