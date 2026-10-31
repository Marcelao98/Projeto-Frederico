# Ilustrações das plumagens

Uma imagem por tema, com o nome do tema:

| Arquivo | Plumagem |
|---|---|
| `albina.png` | Albina (padrão): o Frederico |
| `lutino.png` | Lutino |
| `cinza.png` | Cinza silvestre |
| `canela.png` | Canela |
| `cara-branca.png` | Cara-branca |

PNG quadrado (1024x1024 é bom), fundo transparente, a ave centralizada e
ocupando quase todo o quadro. Aparece pequena (30px no seletor e no chat,
36px no logo) e grande (88px nas boas-vindas), então precisa ser legível
pequena.

Tema sem arquivo aqui usa o desenho em SVG com as cores do tema
(`src/componentes/Calopsita.tsx`). Dá pra pôr só algumas e o resto continua
no desenho.

O ícone do app sai da albina: depois de trocar, rodar de dentro de `frontend/`:

    npx tauri icon public/aves/albina.png
