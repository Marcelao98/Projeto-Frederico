# Como gerar uma lista de bloco do catálogo do Fredify

Repositório: /home/user/projeto-frederico. NÃO faça commit nem push. NÃO mexa em nenhum arquivo além do seu bloco.
Leia antes (só estes): acervo/catalogo/generos.csv e acervo/catalogo/tags.csv (ids válidos), e
acervo/catalogo/blocos/bloco-01.csv só pra NÃO repetir músicas que já estão lá (coluna artista/titulo).

Arquivo de saída: UTF-8, separador ';', sem ';' dentro de campo, esta primeira linha exata:
artista;titulo;ano;genero;genero2;feat;idioma;tem_voz;energia;animacao;climas;ocasioes;temas;instrumentos;popularidade;essencial;canta_junto;explicita;ao_vivo;nota

Colunas:
- artista: artista principal exatamente como nos streamings (duplas como uma coisa só: "Chitãozinho & Xororó"). feat: convidados separados por ", ".
- titulo: o nome oficial da faixa. Só músicas REAIS que você tem certeza que existem, na gravação famosa (nada de cover, remix, versão ao vivo inventada).
- ano: ano do primeiro lançamento dessa gravação. Clássica: ano da composição e nota "ano = composição".
- genero: o id MAIS específico de generos.csv; genero2: outro id opcional.
- idioma: pt, en, es, it, fr, de, ja, ko, la, outro; vazio se instrumental. tem_voz: 1 ou 0.
- energia 1–5: 1 de dormir, 2 calma, 3 média, 4 animada, 5 pancada (pista, treino).
- animacao 1–5: 1 muito triste, 2 triste/melancólica, 3 neutra, 4 alegre, 5 eufórica.
- climas: 2 a 4 ids da gaveta "clima" de tags.csv, separados por "|" (o mais forte primeiro).
- ocasioes: 0 a 4 ids da gaveta "ocasiao" SÓ quando a música é a cara daquela ocasião (ex.: Natal, Carnaval, São João, casamento, treino, fossa, karaoke). As de RPG (rpg-...) só pra trilha sonora, clássica ou épica que sirva de cena.
- temas: 0 a 3 ids da gaveta "tema" (assunto da letra); vazio se instrumental.
- instrumentos: 0 a 2 ids da gaveta "instrumento", só se o instrumento é marcante na música.
- popularidade 0–100 = quanto o público brasileiro de hoje conhece: 90+ todo mundo; 70–89 sucesso grande; 50–69 conhecida de quem curte o gênero; 30–49 de nicho.
- essencial 1 só pros clássicos absolutos (uns 10% da lista). canta_junto 1 se a galera canta junto em festa/karaokê. explicita 1 se tem palavrão ou sexo explícito na letra. ao_vivo 1 só se a versão famosa é a gravação ao vivo.
- nota: opcional, curta (ex.: "Natal", "ano = composição").

Variedade: todas as décadas relevantes do estilo, homens e mulheres, regiões diferentes, hits e lado B famoso. Não repita música (nem a mesma música de outro artista, a não ser versão muito famosa).

Quando terminar, confira (de dentro de backend/):
  python3 -m freddy.catalogo.bloco conferir ../acervo/catalogo/blocos/SEU_ARQUIVO.csv
e corrija até dar "0 erros". Se faltar músicas boas, complete até o número pedido.
Responda no fim só com: o nome do arquivo, quantas músicas e quantas você está menos certo (ano ou título) — sem listar músicas.
