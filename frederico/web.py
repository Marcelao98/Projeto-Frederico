"""Painel web local: o controle remoto do Frederico, em http://127.0.0.1:8765.

Só HTTP + JSON da biblioteca padrão (sem framework). O painel pergunta o
estado a cada segundo; cada botão é um POST. Escuta só no 127.0.0.1, e recusa
pedido cujo Host não seja local (um site aberto no navegador não consegue
mandar comandos pra cá fingindo ser o painel).
"""

from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from frederico import audio

log = logging.getLogger(__name__)

PAINEL = Path(__file__).with_name("painel.html")
CONFIG = Path(__file__).resolve().parent.parent / "config_local.json"  # fora do git


def carregar_config() -> dict:
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def salvar_config(config: dict) -> None:
    CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


class App:
    """O que o painel controla: o player e (se tiver placa de som) o motor."""

    def __init__(self, player, motor):
        self.player = player
        self.motor = motor

    def estado(self) -> dict:
        m = self.motor
        return {
            "player": self.player.estado(),
            "audio": {
                "ligado": m.ligado, "config": m.config, "erro": m.erro,
                "mic_ligado": m.mic_ligado, "ganho_mic": round(m.ganho_mic * 100), "ducking": m.ducking, "ouvir_saida": m.ouvir_saida,
                "nivel_mic": round(m.nivel_mic, 4), "nivel_saida": round(m.nivel_saida, 4),
            },
        }

    def post(self, rota: str, dados: dict) -> dict:
        p, m = self.player, self.motor
        if rota == "/api/tocar":
            return {"msg": p.tocar(str(dados.get("texto", "")))}
        if rota == "/api/frase":
            return {"msg": p.executar(str(dados.get("texto", "")))}
        if rota == "/api/comando":
            acoes = {
                "pular": p.pular, "parar": p.parar, "pausar": p.pausar, "continuar": p.continuar,
                "repetir": p.repetir, "limpar_fila": p.limpar_fila,
            }
            acao = acoes.get(dados.get("acao"))
            if acao is None:
                raise ValueError("ação desconhecida")
            return {"msg": acao()}
        if rota == "/api/volume":
            return {"msg": p.mudar_volume(int(dados["valor"]))}
        if rota == "/api/mic":
            if "ligado" in dados:
                m.mic_ligado = bool(dados["ligado"])
            if "ganho" in dados:
                m.ganho_mic = max(0, min(int(dados["ganho"]), 300)) / 100
            if "ducking" in dados:
                m.ducking = bool(dados["ducking"])
            if "ouvir_saida" in dados:
                m.ouvir_saida = bool(dados["ouvir_saida"])
            return {"msg": "ok"}
        if rota == "/api/audio":
            def _id(chave):
                valor = dados.get(chave)
                return None if valor in (None, "") else int(valor)

            saida = _id("saida")
            if saida is None:
                raise ValueError("Escolhe a saída (o VB-Cable é \"CABLE Input\").")
            m.ligar(saida, _id("mic"), _id("monitor"))
            salvar_config({**carregar_config(), "dispositivos": m.config})
            return {"msg": "Som ligado 🎧"}
        if rota == "/api/desligar":
            m.desligar()
            return {"msg": "Som desligado"}
        raise LookupError(rota)


def criar_servidor(app: App, porta: int = 8765) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, formato, *args):
            log.debug(formato, *args)

        def _responder(self, codigo: int, corpo: bytes, tipo: str = "application/json; charset=utf-8"):
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corpo)

        def _json(self, codigo: int, dados) -> None:
            self._responder(codigo, json.dumps(dados, ensure_ascii=False).encode("utf-8"))

        def _host_ok(self) -> bool:
            porta_real = self.server.server_address[1]
            if self.headers.get("Host") in (f"127.0.0.1:{porta_real}", f"localhost:{porta_real}"):
                return True
            self._json(403, {"erro": "só pelo painel local"})
            return False

        def do_GET(self):
            if not self._host_ok():
                return
            if self.path in ("/", "/index.html"):
                self._responder(200, PAINEL.read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/estado":
                self._json(200, app.estado())
            elif self.path == "/api/dispositivos":
                try:
                    self._json(200, {**audio.listar_dispositivos(), "salvos": carregar_config().get("dispositivos")})
                except Exception as e:
                    self._json(500, {"erro": f"Sem acesso à placa de som: {e}"})
            else:
                self._json(404, {"erro": "não achei"})

        def do_POST(self):
            if not self._host_ok():
                return
            try:
                tamanho = int(self.headers.get("Content-Length") or 0)
                dados = json.loads(self.rfile.read(tamanho) or b"{}")
                self._json(200, app.post(self.path, dados))
            except LookupError:
                self._json(404, {"erro": "não achei"})
            except Exception as e:
                log.exception("erro em %s", self.path)
                self._json(400, {"erro": str(e)})

    return ThreadingHTTPServer(("127.0.0.1", porta), Handler)
