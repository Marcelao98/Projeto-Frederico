<img src="docs/frederico.svg" width="96" alt="Frederico, calopsita albina">

# Projeto Frederico

> Nome de trabalho. O nome final (FredBOT, Freddy ou Fredérico) ainda não foi escolhido.

Uma aplicação de som inspirada no **Frederico**, a calopsita albina de verdade
do Marcelo, que ama música e barulho de todo tipo. No universo da
[Natty](https://github.com/Marcelao98/natty-bot) ele vira uma calopsita robô:
um dos robozinhos menores que a Natty comanda, o que cuida do som.

**O que faz hoje:** toca música **por cima do seu microfone**. Você fala, a
música toca junto (e abaixa sozinha quando você fala), e tudo sai num
microfone virtual que o Zoom, o Meet, o Discord ou o OBS enxergam como um mic
qualquer. Serve pra aula online, live, gravação de vídeo, mesa de RPG.

```
seu mic ─────┐
             ├─► Frederico (mistura + abaixa a música quando você fala) ─► VB-Cable ─► Zoom/Meet/Discord/OBS
música ──────┘                                                        └─► seu fone (só a música)
```

## Instalar (Windows)

1. **Python 3.11+** e **ffmpeg** no PATH (o mesmo ffmpeg que a Natty usa serve).
2. **VB-Cable** (grátis): baixa em <https://vb-audio.com/Cable/>, roda o
   `VBCABLE_Setup_x64.exe` **como administrador** e reinicia o PC. Ele cria
   dois dispositivos: **CABLE Input** (onde o Frederico toca) e
   **CABLE Output** (o "microfone" que os outros programas usam).
3. Dois cliques no **`iniciar.bat`**. Na primeira vez ele instala tudo; depois
   é só abrir. O painel abre sozinho em <http://127.0.0.1:8765>.

## Usar

1. No painel, em **Dispositivos**: escolhe o seu **microfone de verdade**, a
   saída **CABLE Input** e, no monitor, o seu **fone**. Clica **Ligar som**.
   (Ele lembra da escolha na próxima vez.)
2. No Zoom / Meet / Discord / OBS, escolhe **CABLE Output** como microfone.
3. Em **Tocar**, cola um link do YouTube, o caminho de um arquivo
   (`C:\Musicas\aula.mp3`) ou uns temas do catálogo (`taverna`,
   `triste e bloodborne`). Sem link e sem tema que bata, ele toca o primeiro
   resultado do YouTube.
4. **Volume da música** e **volume do mic** são separados. O botão
   "Abaixar música quando eu falo" liga o ducking.
5. **Testar antes da aula:** com o fone no Monitor, liga **"Testar: ouvir o
   que sai"**. Você ouve no fone exatamente o que vai pro microfone virtual
   (sua voz + música, com um pouco de atraso). Desliga depois.

**No Discord:** desliga a **supressão de ruído** (Krisp) e o **cancelamento
de eco** em Voz e Vídeo, senão eles cortam a música, e usa **detecção de voz**
(com push-to-talk a música só vai quando você aperta a tecla).

**Cuidado em live e vídeo monetizado:** música do YouTube pode dar strike /
Content ID. Pra isso, prefira arquivos seus ou trilhas livres (CC0,
biblioteca de áudio do YouTube Studio).

## Como é por dentro

```
frederico/
├── service.py    # catálogo (~585 faixas com tags), busca, fila, frases ("pula", "volume 30")
├── youtube.py    # yt-dlp: link ou busca → URL de áudio
├── fonte.py      # ffmpeg → PCM 48 kHz estéreo, num buffer
├── player.py     # o tocador: fila, repetir, pular, pausar, volume, tenta de novo se falhar
├── mixer.py      # mic + música, ducking, limitador (funções puras)
├── audio.py      # placa de som (sounddevice): mic → mistura → saída + monitor
├── web.py        # painel: HTTP + JSON, só em 127.0.0.1
├── painel.html
├── dataset/      # musicas.json + vocabulario.json
└── discord_pendente/   # o bot de Discord, parado por enquanto
```

O núcleo **não depende do Discord**. Bot, painel ou linha de comando são só
formas de chamar o `Player`.

## Testes

```
python -m unittest discover -s frederico -t .
```

Sem rede e sem placa de som (dublês). Os testes de ponta a ponta usam o ffmpeg
de verdade se ele estiver instalado.

## Licença

MIT (ver `LICENSE`). Repositório privado por enquanto; a licença será
revisada antes de abrir.
