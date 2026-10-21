# Changelog

## Botão de teste e calopsita albina - 2026-10-21

- **"Testar: ouvir o que sai"**: o monitor (fone) passa a receber a mistura completa (mic + música), igual ao que sai no VB-Cable.
- O 🦜 virou um desenho da calopsita albina (painel, favicon, README).

## Núcleo sem Discord + painel web + música por cima do mic - 2026-10-20

- O código saiu de `modules/bardo/` pra `frederico/` (histórico preservado com `git mv`).
- **`player.py`**: o tocador que morava dentro do cog do Discord, agora sem Discord. Fila, repetir, pular, pausar, volume, "falhou em menos de 5 s → tenta de novo com URL nova", pula música que não abre. API síncrona; em vez de mandar mensagem, registra eventos.
- **`fonte.py`**: ffmpeg decodifica link ou **arquivo local** em PCM 48 kHz estéreo.
- **`mixer.py`** e **`audio.py`**: mic + música com **ducking** (a música abaixa quando você fala) e limitador; saída principal (VB-Cable) + monitor (fone só com a música). sounddevice/PortAudio.
- **`web.py`** + **`painel.html`**: painel em `http://127.0.0.1:8765` (tocar, pausa, pular, repetir, parar, fila, volume da música e do mic, medidores, escolha de dispositivos, que ficam salvos em `config_local.json`). Recusa pedido de Host que não seja local.
- **`iniciar.bat`**: cria o ambiente, instala e abre o painel.
- O cog e o README do Bardo foram pra `frederico/discord_pendente/`, parados.
- Testes: 91 do Bardo + 24 novos (player, mixer, buffer, motor, ffmpeg de verdade, painel).

## Frederico nasce - 2026-10-19

- Bardo extraído da natty-bot com histórico (`git filter-repo`), README e licença MIT.
