# Orquestração: vários agentes enchendo o catálogo ao mesmo tempo

Pra qualquer agente (Claude em outra sessão, Codex, Gemini, etc.) pegar um
pedaço do trabalho, fazer o quanto o limite dele deixar e parar sem perder
nada. Contexto completo: `docs/etapas/banco-fredify-etapa3.md`.

## A ideia

- **Uma tarefa = um bloco** (`bloco-NN.csv`). Cada bloco é um arquivo só dele:
  dois agentes nunca mexem no mesmo arquivo, então o git não dá conflito.
- **Progresso salvo aos poucos:** o agente grava e envia a cada ~50 músicas.
  Se o limite acabar no meio, o próximo agente continua do mesmo arquivo.
- **Quem está em qual bloco** fica num arquivo por bloco:
  `blocos/vez/bloco-NN.txt` (nome do agente e hora). Vez com mais de 6 horas
  sem envio é considerada abandonada: pode pegar.
- **Tudo no branch `main`** (o Marcelo autorizou; sem PR).

## Ver o que falta

```bash
cd backend && python3 -m freddy.catalogo.bloco status
```

Mostra cada bloco: quantas tem, a meta, erros e quem está com a vez.

## O passo a passo de um agente

1. **Atualizar e escolher:**
   ```bash
   git checkout main && git pull --rebase origin main
   cd backend && python3 -m freddy.catalogo.bloco status
   ```
   Pegue o primeiro bloco que não está PRONTO e não tem vez recente (ou o que
   o Marcelo mandou). O `bloco-01` (formato antigo) tem prioridade.

2. **Pegar a vez** (e enviar logo, pra os outros verem):
   ```bash
   mkdir -p ../acervo/catalogo/blocos/vez
   echo "<seu nome/sessão> $(date -u +%FT%TZ)" > ../acervo/catalogo/blocos/vez/bloco-NN.txt
   git add ../acervo/catalogo/blocos/vez && git commit -m "Catálogo: pegando o bloco-NN" && git push origin HEAD:main
   ```
   Se o push for recusado: `git pull --rebase origin main`, rode o status de
   novo (alguém pode ter pegado o mesmo bloco) e tente outro.

3. **Ler só o necessário** (economiza tokens):
   `acervo/catalogo/blocos/REGRAS_PARA_GERAR.md`, `acervo/catalogo/generos.csv`,
   `acervo/catalogo/tags.csv`, o seu `bloco-NN.csv` (se já existir: continue
   dele, não repita) e o seu rascunho em `acervo/catalogo/blocos/rascunhos/bloco-NN/`
   (formatos descritos na tabela do guia da etapa 3). Não leia o `musicas.json`.

4. **Gerar em lotes de ~50**, anexando ao `bloco-NN.csv` (com a linha de
   cabeçalho se o arquivo for novo). A cada lote:
   ```bash
   python3 -m freddy.catalogo.bloco conferir ../acervo/catalogo/blocos/bloco-NN.csv   # até 0 erros
   touch ../acervo/catalogo/blocos/vez/bloco-NN.txt
   git add ../acervo/catalogo/blocos && git commit -m "Catálogo: bloco-NN +50" && git pull --rebase origin main && git push origin HEAD:main
   ```

5. **Ao chegar na meta:** confira contra todos os blocos (tira repetidas entre
   eles; quem chegou primeiro fica com a música, então tire da SUA lista e
   complete com outras):
   ```bash
   python3 -m freddy.catalogo.bloco conferir ../acervo/catalogo/blocos/bloco-*.csv
   ```
   Depois apague a vez e envie:
   ```bash
   git rm -q ../acervo/catalogo/blocos/vez/bloco-NN.txt
   git add ../acervo/catalogo/blocos && git commit -m "Catálogo: bloco-NN pronto" && git pull --rebase origin main && git push origin HEAD:main
   ```

6. **Se o limite estiver acabando:** pare no fim de um lote já enviado. Não
   apague a vez; o próximo agente vê o "há X h" e continua.

## Regras

- Mexa só no seu `bloco-NN.csv` e no seu `vez/bloco-NN.txt`. Nada de código,
  nada de outros CSV do catálogo.
- Gênero ou tag que faz falta: não invente id. Escreva a sugestão no fim de
  `acervo/catalogo/blocos/sugestoes.md` (crie se não existir) e use o id mais
  próximo que existe.
- Commit em português, sem nome de modelo de IA.
- Só músicas reais, na gravação famosa (detalhes no `REGRAS_PARA_GERAR.md`).

## Quando todos os 11 estiverem PRONTOS (o "integrador", qualquer agente)

```bash
cd backend
python3 -m freddy.catalogo.bloco status                                          # 11/11 prontos
python3 -m freddy.catalogo.bloco conferir ../acervo/catalogo/blocos/bloco-*.csv  # 0 erros
python3 -m unittest discover -s freddy -t .                                      # OK
```

Depois: ler `sugestoes.md` (se houver), atualizar o "Onde paramos" do
`ROADMAP.md`, enviar, e passar pro Marcelo os 2 comandos do passo 3 do
`docs/etapas/banco-fredify-etapa3.md`.
