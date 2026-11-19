# Etapa: modo Explorar (navegar pelas músicas sem digitar)

Pedido do Marcelo (19/11/2026). Vem **depois** das 5 mil instrumentais
(`catalogo-ost.md`) e **antes** da B2: os botões de cena da B2 nascem daqui.

## A ideia
Um modo novo no painel (`frontend/src/modos/explorar/`), irmão do Chat. O chat
continua pra quem digita; o Explorar é pra quem clica. Os dois usam o mesmo
catálogo e a mesma busca (`freddy/catalogo/`).

## A tela
1. **Prateleiras por pra que serve** (a tela inicial)
   - Dia a dia: Estudar (foco) · Ler · Relaxar · Dormir · Dia chuvoso · Treinar ·
     Festa · Churrasco.
   - Mesa de RPG (grade de cenas): Taverna · Cidade · Viagem · Exploração ·
     Masmorra · Combate · Chefe · Vilão · Terror · Mistério · Drama · Descanso · Final.
   - Cada prateleira: ▶ toca embaralhado; clique abre a lista.
2. **Filtros por cima de qualquer prateleira**: sem voz · só estável · energia
   (1–5) · climas · cenários · época. Ex.: Masmorra + caverna + sem voz.
3. **Coleções**: por obra/franquia (Ghibli, Zelda, Souls...), gênero, época,
   artista/compositor. Com contagem de músicas.
4. **Cenas fixas da campanha**: salvar uma combinação de filtros com nome
   ("Taverna do Javali", "Cripta do Lich") e virar botão. Ficam na pasta do
   mestre (como as playlists). É a base do "botão de cena" da B2.

## Backend (`api/rotas/catalogo.py`, lógica em `freddy/catalogo/`)
- `GET /catalogo/facetas`: as prateleiras e os filtros com quantas músicas
  cada um tem (ocasiões, climas, cenários, gêneros-família, obras, épocas).
- `POST /catalogo/lista`: filtros estruturados → músicas (`{titulo, link,
  faixaId, ...}`), paginado, com opção "sorteia N". Reaproveitar
  `Catalogo.forca` e as receitas de ocasião (`ocasioes_perfil.csv`): a
  prateleira "Estudar" é a receita `foco`, não uma lista fixa.
- `GET/POST/DELETE /cenas`: as cenas fixas (pasta do mestre, `cenas.json`).
- Testes do lado do backend (como `test_servico.py`) e rota nova no Porteiro
  já nasce protegida.

## Regras
- Função nova é só com o Freddy ligado (o modo navegador está congelado).
- Tocar = `motor.executar({tipo: "adicionar", musicas})`, igual ao chat.
- Telas seguem o padrão: `.css` próprio, entra em `modos/registro.tsx`,
  `telas-menores.css` por último. Testar no celular (largura 400 px).
- Versão nova do app ao terminar (0.8.0).
