# Blocos da etapa 3 (encher o catálogo)

Cada bloco tem ~500 músicas (`docs/etapas/banco-fredify.md`, "Como roda um bloco").

1. **Lista** (`bloco-NN.csv`: `artista;titulo;ano;genero;feat;nota`): o Claude gera;
   o gênero é o id de `../generos.csv`; na `nota`, ocasião óbvia (Natal, Carnaval…)
   e "ano = composição" na clássica.
2. **O Marcelo corta e acrescenta** direto no CSV (abre no LibreOffice Calc com
   separador `;`, ou em qualquer editor de texto).
3. **Conferir e achar o link oficial** (no computador do Marcelo: a nuvem não
   alcança o MusicBrainz nem o YouTube), de dentro de `backend/`:

   ```bash
   python scripts/catalogo_bloco.py ../acervo/catalogo/blocos/bloco-01.csv
   ```

   Gera `bloco-01.musicbrainz.csv` (ano conferido: `confere` = sim/NÃO/?) e
   `bloco-01.youtube.csv` (o link e o motivo: canal Topic, VEVO, do artista; sem
   link quando só tem cover/letra/karaokê). Pode parar e rodar de novo: continua.
4. **Tags** (energia, animação, climas, ocasiões, temas, popularidade): em lotes
   de 100, por subagente; o Claude só confere o estranho.
5. **Entra no catálogo** (lote `bloco-NN`, com as regras completas: ano e fonte
   oficial viva obrigatórios) e o Marcelo confere 50 sorteadas.
