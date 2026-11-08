# Etapa 3 do banco do Fredify: encher o catálogo (guia pra continuar)

Escrito em 08/11/2026 pra qualquer agente pegar daqui. Leia antes:
`docs/etapas/banco-fredify.md` (o plano), `acervo/catalogo/README.md` (as
tabelas e regras) e `acervo/catalogo/blocos/README.md` (os blocos).

## A decisão do Marcelo (não refazer)

Tudo de uma vez, não bloco por bloco: o Claude gera **as ~5 mil músicas já com
as tags** em 11 listas; o Marcelo roda **um comando só** no PC dele (confere no
MusicBrainz e no YouTube, importa, compila, testa, envia pro GitHub); o Claude
lê o relatório e arruma. Ele não quer ficar indo e voltando.

## O que já está pronto (no `main`)

- Vocabulário, esquema SQLite, compilador, consulta, 108 pedidos de ouro, as 607
  de RPG migradas (etapas 1 e 2).
- `backend/freddy/catalogo/bloco.py`: o formato da lista (`COLUNAS`), o
  conferidor de lista (`python -m freddy.catalogo.bloco conferir <arquivos>`,
  pega ids errados, faltas, < 2 climas e **repetidas entre arquivos**) e as
  escolhas de gravação do MusicBrainz e de vídeo oficial do YouTube.
- `backend/freddy/catalogo/importar.py`: blocos conferidos → CSV do catálogo
  (lote `bloco-NN`, ano corrigido pelo MusicBrainz, sem link oficial vai pro
  `pendentes.csv`; idempotente).
- `backend/scripts/catalogo_bloco.py`: o comando único do PC do Marcelo.
- Testes: `freddy/catalogo/test_bloco.py` (escolhas + importação de ponta a
  ponta numa cópia do catálogo) e `test_catalogo.py`.
- As regras pra gerar uma lista: `acervo/catalogo/blocos/REGRAS_PARA_GERAR.md`
  (é o texto que vai no pedido de cada subagente).

## O que NÃO está pronto: as listas

Os 11 subagentes (modelo mais barato, todos em paralelo) bateram no limite de
uso de 5 horas da conta antes de gravar o arquivo final. **Nenhum `bloco-NN.csv`
novo foi gravado.** O que eles deixaram de rascunho foi salvo em
`acervo/catalogo/blocos/rascunhos/bloco-NN/` (cópia crua; formatos diferentes;
pode ter repetidas e versões do mesmo pedaço):

| Bloco | Tema | Meta | Rascunho (músicas distintas) | Formato do rascunho |
|---|---|---|---|---|
| 01 | essenciais (de tudo) | 562 (manter as que já estão) | 320 marcadas em código | `n\|...` com abreviações próprias do agente (ex.: `al ac co`); o `n` é a linha de `indice-numerado.txt`. **Mais seguro refazer as tags** a partir do `bloco-01.csv` atual |
| 02 | MPB, bossa, tropicália, nova MPB, choro, soul BR | 400 | 443 | **formato final completo** (sem cabeçalho), em pedaços `pN*.txt` |
| 03 | samba e pagode | 400 | 185 | `;` com colunas faltando (artista;titulo;ano;genero;energia;animacao;climas;...) |
| 04 | sertanejo (caipira → agronejo, muito 2020–2025) | 450 | 98 | `\|` com códigos abreviados (`mc` = musica-caipira; climas abreviados) |
| 05 | forró, piseiro, axé, brega, arrocha, regionais, marchinhas, São João | 450 | 715 | `artista\|titulo\|ano\|genero\|energia\|animacao\|climas(,)\|ocasioes\|temas(,)\|instrumentos\|popularidade\|flags` (E = essencial) |
| 06 | rock nacional, metal BR, reggae nacional, pop e teen BR | 450 | ~1460 (inclui versões) | `\|` parecido com o 05; `d1`, `d1c`, `d1d` são versões do mesmo pedaço (usar a última letra) |
| 07 | funk, rap/trap BR (300), gospel (130), infantil BR (70) | 500 | 0 | só um `gen.py` vazio: **gerar do zero** |
| 08 | pop internacional, latina, k-pop, anime | 500 | 654 | `artista;titulo;ano;genero;feat;idioma;energia;animacao;climas;ocasioes;temas;popularidade;flags` (C = canta_junto?) |
| 09 | rock internacional | 450 | 812 | `artista\|titulo\|ano\|genero\|energia\|animacao\|climas(,)\|popularidade\|flags` |
| 10 | soul, disco, R&B, jazz, reggae, hip hop internacional | 450 | 139 | `\|` resumido (`energia\|animacao\|popularidade\|r,T:temas`) |
| 11 | eletrônica, baladas, trilhas (filme, série, musical, novela, videogame), clássica, mundo, Natal | 400 | 519 | **quase o formato final** (`;`), em pedaços `pN`, `pNa`… |

Os rascunhos são ponto de partida, não verdade: conferir ids (o conferidor
pega), completar colunas que faltam, tirar repetidas e cortar até a meta
(ficar com as mais conhecidas).

## Próximos passos (em ordem)

### 1. Fazer as 11 listas finais (`acervo/catalogo/blocos/bloco-NN.csv`)

**Dividido entre vários agentes:** o protocolo está em
`acervo/catalogo/blocos/ORQUESTRACAO.md` (pegar a vez, lotes de 50, enviar a
cada lote) e o texto pronto pra colar em qualquer agente em
`acervo/catalogo/blocos/PROMPT_AGENTE.md`. O que falta:
`cd backend && python3 -m freddy.catalogo.bloco status`.

Pra cada bloco:
1. Ler o rascunho (só o bloco da vez, pra economizar) e escrever um conversor
   pequeno no diretório de rascunho da sessão (não no repositório) que gera
   `bloco-NN.csv` no formato final:
   `artista;titulo;ano;genero;genero2;feat;idioma;tem_voz;energia;animacao;climas;ocasioes;temas;instrumentos;popularidade;essencial;canta_junto;explicita;ao_vivo;nota`
2. Completar o que o rascunho não tem (idioma, tem_voz, temas, ocasiões, as
   flags) pelo conhecimento da música; seguir `REGRAS_PARA_GERAR.md`.
3. Cortar/completar até a meta da tabela acima (total ≈ 5.000 com o 01).
4. Rodar, de `backend/`:
   `python3 -m freddy.catalogo.bloco conferir ../acervo/catalogo/blocos/bloco-NN.csv`
   até "0 erros".
5. **Gravar e commitar a cada bloco pronto** (não esperar todos).

Bloco 01: o `bloco-01.csv` atual está no formato ANTIGO
(`artista;titulo;ano;genero;feat;nota`, 562 músicas, sem tags). Reescrever no
formato novo mantendo as mesmas músicas. **Enquanto ele estiver no formato
antigo, o script do PC quebra** (a importação lê todas as listas).

**Lição da tentativa anterior:** 11 subagentes ao mesmo tempo estouraram o
limite de 5 horas da conta e perderam tudo que não estava gravado. Rodar **no
máximo 3 ou 4 ao mesmo tempo**, e mandar cada um **gravar o arquivo aos
poucos** (anexar a cada ~50 músicas) pra não perder trabalho.

### 2. Conferir tudo junto

```bash
cd backend
python3 -m freddy.catalogo.bloco conferir ../acervo/catalogo/blocos/bloco-*.csv   # 0 erros, sem repetidas entre blocos
python3 -m unittest discover -s freddy -t .                                        # tudo OK
```

Depois: commit, `git push -u origin <branch>` e `git push origin HEAD:main`.

### 3. Passar pro Marcelo o comando único (Fedora)

Ele cola no terminal (o primeiro baixa/atualiza o projeto e instala só o yt-dlp
num ambiente separado):

```bash
cd ~ && ( [ -d Projeto-Frederico ] && cd Projeto-Frederico && git checkout main && git pull || git clone https://github.com/Marcelao98/Projeto-Frederico.git ) && cd ~/Projeto-Frederico && python3 -m venv ~/.venv-fredify && ~/.venv-fredify/bin/pip install -q -U yt-dlp && echo PRONTO
```

```bash
cd ~/Projeto-Frederico/backend && ~/.venv-fredify/bin/python scripts/catalogo_bloco.py
```

Leva ~3 horas pra 5 mil (MusicBrainz e YouTube ao mesmo tempo); se parar, roda
de novo e continua. No fim ele faz commit + push no `main` sozinho. Se o push
pedir senha (Git dele sem login no GitHub), ele roda `git push origin HEAD:main`
depois de logar, ou manda os arquivos `bloco-*.musicbrainz.csv`,
`bloco-*.youtube.csv`, `pendentes.csv` e `relatorio.md`.

A nuvem do Claude não alcança o MusicBrainz nem o YouTube (o proxy recusa); o
Marcelo recusou abrir um ambiente com esses sites. Por isso roda no PC dele.

### 4. Depois que ele rodar

1. `git pull` e ler `acervo/catalogo/blocos/relatorio.md`.
2. Pendentes (sem upload oficial): decidir caso a caso (às vezes o título está
   diferente do oficial: corrigir na lista e ele roda de novo, que só confere as novas).
3. Pedidos de ouro que falharem: agora há música geral no catálogo, então os
   33 que estavam pendentes passam a ser conferidos. Ajustar gíria, perfil de
   ocasião ou a expectativa (`acervo/catalogo/pedidos_de_ouro.csv`).
4. Anos corrigidos pelo MusicBrainz: olhar os mais estranhos (o "mais antigo"
   às vezes é uma demo ou um relançamento errado).
5. Sortear 50 pra o Marcelo conferir (o plano pede).
6. Atualizar o "Onde paramos" do `ROADMAP.md`. **Próxima etapa: 4 (ligar a
   busca nova no Fredify).**
