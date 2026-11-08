# O banco de músicas do Fredify

Combinado com o Marcelo em 08/11/2026, depois da auditoria
(`docs/etapas/auditoria-fredify-relatorio.md`). **Prioridade agora: um
dataset muito bom**, antes de crossfade e afins. Público geral do Brasil
primeiro (sem abandonar o RPG: ele volta como ocasiões e pacotes).

## A meta

A pessoa não precisa saber nada de gênero ou tag. Ela fala **"toca um modão
de 2024 pra um churrasco e depois um pagode"** e o Fredify entende. Pra isso
o banco guarda duas coisas: **as músicas bem descritas** e **o jeito que o
brasileiro fala de música** (modão, sofrência, pagodão, piseiro, flashback,
"pra chorar").

Primeira meta: **5 mil músicas** (BR e internacionais conhecidas por todo
mundo), mais as 607 de RPG que já existem.

## Tecnologia

- **SQLite** (+ FTS5 pra texto, sem acento). Um arquivo, sem servidor, roda
  no Android. 5 mil músicas ≈ 5–8 MB.
- **Dois arquivos:** `catalogo.db` (vem com o app, trocado inteiro a cada
  versão do catálogo) e `usuario.db` (correções, playlists, histórico,
  biblioteca da pessoa). Atualizar o catálogo nunca apaga nada da pessoa.
- **No git, o catálogo fica em CSV por tabela** (`acervo/catalogo/`); um
  script compila o `catalogo.db` e confere as regras.

## As tabelas

```
ARTISTA        id, nome, tipo (solo/dupla/banda/orquestra), país, estado/região,
               ano de início, mbid
OBRA           id, nome, tipo (álbum/jogo/anime/filme/novela/série), ano
MUSICA         id, título, ano, duração, idioma, obra, energia (1–5),
               animação (triste↔alegre, 1–5), tem_voz, canta_junto, ao_vivo,
               explicita, popularidade (0–100), essencial, mbid, isrc
MUSICA_ARTISTA música, artista, papel (principal/feat)
GENERO         id, nome, pai                     (árvore: sertanejo → raiz/universitário/sofrência...)
TAG            id, gaveta (clima/ocasião/instrumento/tema da letra), nome
MUSICA_GENERO  música, gênero, peso (0–1)
MUSICA_TAG     música, tag, peso (0–1), quem_marcou (curadoria/claude/analise/lastfm)
FONTE          música, tipo (youtube/arquivo/jamendo...), endereço, oficial, viva, conferida_em
PALAVRA        palavra, aponta_pra (gênero/tag/década/ocasião), peso   (as gírias)
OCASIAO_PERFIL ocasião, gêneros que combinam, energia mín/máx, climas que combinam/evitar
BUSCA          FTS5: título, artista, obra, gêneros, tags
```

**Perfis de ocasião:** "churrasco" não é marcado em 5 mil músicas à mão. O
perfil diz a cara do churrasco (sertanejo, pagode, samba, funk, axé;
energia ≥ 3; nada triste demais); a marcação manual só reforça ou tira.

## Regras de qualidade (o compilador barra)

- Toda música: gênero, ano, energia, ≥ 2 climas, 1 fonte oficial viva,
  popularidade. Fonte: preferir upload oficial (canal "- Topic", VEVO, do
  artista ou da produtora); nada de site pirata; letra e capa não vão pro banco.
- **Pedidos de ouro:** ~100 frases reais, cada uma com o que tem que
  aparecer e o que não pode. Rodam como teste a cada mudança.

## Etapas

| Etapa | O que sai | Pronto quando | Sessões | Tokens (aprox.) |
|---|---|---|---|---|
| 1. Vocabulário | árvore de gêneros (~150), climas (~25), ocasiões com perfil (~40), temas de letra (~20), ~300 gírias | o Marcelo aprovou as listas | 1 | 150–300 mil |
| 2. Banco de pé | esquema, compilador dos CSV, regras, ~100 pedidos de ouro, as 607 de RPG migradas | compila; testes de busca de hoje e pedidos de RPG passam | 1–2 | 400–700 mil |
| 3. Encher (10 blocos de 500) | 5 mil músicas catalogadas com link oficial | cada bloco passa nas regras e nos pedidos de ouro dele | 10 curtas | 80–120 mil por bloco |
| 4. Ligar no Fredify | busca nova no backend, o "e depois", gírias no chat, painel buscando no banco | o pedido do modão funciona no app | 2–3 | 1–2 milhões |

Total: ~15 sessões, ~2,5–4 milhões de tokens (estimativa; recalibrar depois
da 1ª sessão).

### Como roda um bloco da etapa 3 (barato)
1. Claude gera a lista do bloco em arquivo (`artista;título;ano;gênero`).
2. O Marcelo corta e acrescenta.
3. Scripts sem token: MusicBrainz (ano, mbid, duplicatas) e o link oficial do
   YouTube (**roda no Fedora do Marcelo**: o YouTube bloqueia a nuvem).
4. Tags em código, lotes de 100, por subagente com modelo mais barato; Claude
   só confere o estranho.
5. O Marcelo confere 50 aleatórias na planilha.

### Divisão sugerida (pra 1000; multiplicar pras 5 mil)
Brasil 60%: MPB/bossa, rock nacional, samba/pagode, sertanejo, forró/axé/
nordeste, funk/rap BR, pop BR, datas (Carnaval, São João, Natal). Mundo 40%:
pop 80s–hoje, rock clássico, soul/funk/disco, baladas, hip hop, eletrônica,
trilhas de filme, clássica famosa. Todas as décadas dos anos 60 aos 2020.

## Economizar tokens
Um bloco por sessão; listas sempre em arquivo, nunca no chat; modelo barato
pras tags; gírias e perfis bem feitos na etapa 1 (deixa a tag por música
mais simples).

**Etapa 1 feita** (08/11/2026, `acervo/catalogo/`), esperando aprovação.
**Próximo passo:** etapa 2.
