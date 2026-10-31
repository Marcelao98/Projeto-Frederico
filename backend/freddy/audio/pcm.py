"""O formato do som dentro do Freddy: PCM 16 bits, 48 kHz, estéreo, quadros de 20 ms.

É exatamente o que o Discord pede (discord.AudioSource.read() devolve um
quadro desses). Por isso tudo passa por aqui: a caixa de som hoje, o bot na
Fase 2 e o mic virtual na Fase 4 leem o mesmo som da Mesa.
"""

TAXA = 48_000
CANAIS = 2
BYTES_POR_AMOSTRA = 2
QUADRO_MS = 20
AMOSTRAS_POR_QUADRO = TAXA * QUADRO_MS // 1000  # 960
BYTES_POR_QUADRO = AMOSTRAS_POR_QUADRO * CANAIS * BYTES_POR_AMOSTRA  # 3840
QUADROS_POR_SEGUNDO = 1000 // QUADRO_MS  # 50
SILENCIO = bytes(BYTES_POR_QUADRO)
