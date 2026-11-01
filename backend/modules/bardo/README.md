# Bardo: o cérebro musical do Freddy

Veio do módulo de música da Natty (com o histórico do git) e agora é do
Freddy: **não** fica em sincronia com a natty-bot. Sobrou só a lógica pura,
sem Discord:

```
modules/bardo/
├── service.py       entender pedidos, buscar no acervo, utilitários do dataset
├── youtube.py       a única peça que fala com o YouTube (yt-dlp)
├── test_service.py  testes (rodar de dentro de backend/)
└── dataset/         o acervo: musicas.json + vocabulario.json (fonte única)
```

Quem usa: o servidor do Freddy (`backend/freddy/`), o bot do Discord
(`backend/freddy/bot/`) e os scripts de manutenção do acervo. O painel tem
portas fiéis de `interpretar_pedido` e `buscar_por_tags` em
`frontend/src/nucleo/` (mudou um, muda o outro).

## Pedidos (`interpretar_pedido`)

Texto livre → `Pedido(acao, ...)`: `tocar` (link ou busca), `pular`, `fila`,
`limpar_fila`, `pausar`, `continuar`, `parar`, `repetir`, `volume`.
Exemplos: "toca triste e bloodborne", "toca <link>", "pula", "volume 30",
"aumenta", "repete", "para de repetir", "limpa a fila". A ordem das regras
importa ("para de repetir" desliga o loop, não para a música; em "toca uma
música para relaxar" o "para" é preposição): os casos estão em
`test_service.py`.

## Busca no acervo (`buscar_por_tags`)

Busca booleana em português: `e`, `ou`, `sem`/`não`. Cada termo bate no
nome, na franquia, nos temas ou nas categorias (com sinônimos do
`vocabulario.json`, e o feminino vale: "sombria" acha "sombrio"). Mais
de 15 resultados → o Freddy sorteia 15, pra não prender a mesa numa
franquia só.

## O acervo

`dataset/musicas.json`: cada faixa tem `id`, `nome`, `link`, `origem`
(franquia), `temas` (as tags cruas) e `categorias` (os 27 climas da busca,
calculados dos temas pelo `vocabulario.json`). Pra acrescentar uma franquia:
a skill `chips` (`.claude/skills/chips/`). Pra levar o que os mestres
arrumaram no Freddy pro acervo oficial: `scripts/freddy_promover.py`.
