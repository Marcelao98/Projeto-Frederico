# Ilustrações das plumagens

Uma imagem por tema, com o nome do tema:

| Arquivo | Plumagem |
|---|---|
| `frederico.png` | Frederico (padrão): cara-branca, asa prateada |
| `lutino.png` | Lutino |
| `cinza.png` | Cinza silvestre |
| `canela.png` | Canela |
| `cara-branca.png` | Cara-branca |

Opcional: `<tema>-rosto.png`, só a cabeça, pros tamanhos pequenos (logo,
seletor, avatar do chat). Sem ele, esses lugares usam o corpo inteiro, que
fica pequeno demais por causa da cauda. O rosto aparece num círculo.

PNG quadrado (1024x1024 é bom), fundo transparente, a ave centralizada e
ocupando quase todo o quadro. Aparece pequena (30px no seletor e no chat,
36px no logo) e grande (88px nas boas-vindas), então precisa ser legível
pequena.

Tema sem arquivo aqui usa o desenho em SVG com as cores do tema
(`src/componentes/Calopsita.tsx`). Dá pra pôr só algumas e o resto continua
no desenho.

O ícone do app sai do Frederico: depois de trocar, rodar de dentro de `frontend/`:

    npx tauri icon public/aves/frederico.png

Arte do Gemini com fundo escuro ou xadrez falso: `python scripts/recortar_ave.py
arte.jpg public/aves/<tema>.png` tira o fundo e enquadra.
