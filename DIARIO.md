# Diário do Frederico

## 2026-10-19 — Nasce o Frederico

- Decisão: a música sai da Natty. A Natty vai ser pública e na nuvem; bot de
  música na nuvem cai (termos do YouTube, bloqueio de IP de datacenter). O
  Frederico roda local, no PC de cada mestre. Na história, os Freds são
  robozinhos menores que a Natty comanda; no código, projetos separados.
- Bardo extraído da natty-bot com histórico (`git filter-repo`): 27 commits.
- Licença MIT por enquanto, repo privado. Nome final pendente (FredBOT,
  Freddy, Fredérico).

## 2026-10-20 — Núcleo sem Discord e painel pra aula

- Pedido: música por cima do mic numa aula, sem Discord. Caminho escolhido:
  mic virtual (VB-Cable) em vez de bot, mais simples de manter.
- O tocador saiu de dentro do cog (`player.py`), ganhou fonte via ffmpeg que
  aceita arquivo local, mixagem com o mic e ducking, saída + monitor, e um
  painel web local.
- Testado na nuvem: 115 testes, inclusive ffmpeg de verdade decodificando
  arquivo e o painel respondendo. **Não testado:** placa de som (a nuvem não
  tem) e YouTube (a nuvem é bloqueada). Primeiro teste de ouvido é do Marcelo.
- Falta: aviso "congelado" no Bardo da Natty; mixer em camadas (ambiente,
  pads); bot de Discord; Freesound; quebrar o `service.py` em arquivos menores.
