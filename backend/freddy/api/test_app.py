"""O servidor de ponta a ponta: REST e WebSocket, com reprodutor falso e pasta temporária."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from freddy.api.app import criar_app
from freddy.audio.reprodutor_falso import ReprodutorFalso
from freddy.config import Config

PAINEL = {"origin": "http://localhost:5173"}
WS = "ws://127.0.0.1:47824/ws"  # o TestClient usa "testserver" se não disser o endereço


def m(n: int) -> dict:
    return {"titulo": f"Música {n}", "link": f"https://youtu.be/v{n}"}


class YoutubeFalso:
    def info(self, link):
        return {"titulo": "Vídeo Colado", "link": link, "duracaoSegundos": 123}

    def buscar(self, texto):
        if texto == "nada":
            raise LookupError(texto)
        if texto == "quebra":
            raise RuntimeError("ERROR: Private video")
        return {"titulo": f"Achei {texto}", "link": "https://www.youtube.com/watch?v=abc123", "duracaoSegundos": 200}


class BotFalso:
    """Faz o papel do BotDoFreddy (o de verdade precisa do Discord)."""

    def __init__(self, *args):
        self.segredos = args[5]
        self.ao_mudar = lambda: None
        self.tokens: list[str] = []
        self.canal: str | None = None
        self.ouvir = True

    def estado(self):
        return {"situacao": "conectado" if self.tokens else "desligado", "canal": self.canal, "ouvirAqui": self.ouvir}

    async def ligar(self):
        if self.segredos.token():
            self.tokens.append("guardado")

    async def conectar(self, token):
        self.tokens.append(token)
        self.ao_mudar()

    async def desconectar(self):
        self.tokens.clear()
        self.canal = None

    async def entrar(self, canal_id):
        from freddy.integracoes.discord.bot import ErroDoBot

        if canal_id == 404404:
            raise ErroDoBot("não achei esse canal de voz")
        self.canal = str(canal_id)
        self.ao_mudar()

    async def sair(self):
        self.canal = None

    def definir_ouvir_aqui(self, ligado):
        self.ouvir = ligado


class Base(unittest.TestCase):
    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.pasta, True)
        self.reprodutores: list[ReprodutorFalso] = []

        def criar(_config, loop):
            r = ReprodutorFalso(agendar=loop.call_soon_threadsafe)
            self.reprodutores.append(r)
            return r

        config = Config(pasta=self.pasta, pasta_downloads=self.pasta / "Downloads")
        self.bot = None

        def bot(*args):
            self.bot = BotFalso(*args)
            return self.bot

        app = criar_app(config, criar=criar, youtube=YoutubeFalso(), bot=bot)
        self.cliente = TestClient(app, base_url="http://127.0.0.1:47824")
        self.cliente.__enter__()
        self.addCleanup(self.cliente.__exit__, None, None, None)


class TestWebSocket(Base):
    def conectar(self):
        ws = self.cliente.websocket_connect(WS, headers=PAINEL)
        ws.__enter__()
        self.addCleanup(ws.__exit__, None, None, None)
        ola = ws.receive_json()
        self.assertEqual(ola["tipo"], "ola")
        self.assertEqual(ola["protocolo"], 1)
        estado = ws.receive_json()
        self.assertEqual(estado["tipo"], "estado")
        self.assertEqual(ws.receive_json()["tipo"], "progresso")
        self.assertEqual(ws.receive_json()["tipo"], "discord")
        return ws, estado["estado"]

    def comando(self, ws, id_, comando):
        ws.send_json({"tipo": "comando", "id": id_, "comando": comando})
        recebidas = []
        while True:
            msg = ws.receive_json()
            recebidas.append(msg)
            if msg["tipo"] == "resposta":
                self.assertEqual(msg["id"], id_)
                return msg, recebidas[:-1]

    def test_ao_conectar_recebe_o_estado(self):
        _, estado = self.conectar()
        self.assertEqual(estado, {"tocando": None, "proximas": [], "situacao": "parado", "repetir": False, "volume": 50})

    def test_comando_muda_o_estado_antes_da_resposta(self):
        ws, _ = self.conectar()
        resposta, antes = self.comando(ws, 1, {"tipo": "adicionar", "musicas": [m(1), m(2)]})
        self.assertEqual(resposta["resultado"], {"entraram": 2, "posicao": 0, "comecou": True})
        estados = [x["estado"] for x in antes if x["tipo"] == "estado"]
        self.assertEqual(estados[-1]["tocando"]["titulo"], "Música 1")
        self.assertEqual([x["titulo"] for x in estados[-1]["proximas"]], ["Música 2"])
        self.assertTrue(estados[-1]["tocando"]["uid"])

    def test_dois_paineis_veem_a_mesma_fila(self):
        a, _ = self.conectar()
        b, _ = self.conectar()
        self.comando(a, 1, {"tipo": "adicionar", "musicas": [m(1)]})
        msg = b.receive_json()
        while msg["tipo"] != "estado":
            msg = b.receive_json()
        self.assertEqual(msg["estado"]["tocando"]["titulo"], "Música 1")

    def test_eventos_chegam(self):
        ws, _ = self.conectar()
        self.comando(ws, 1, {"tipo": "adicionar", "musicas": [m(1), m(2)]})
        _, antes = self.comando(ws, 2, {"tipo": "pular"})
        _, antes = self.comando(ws, 3, {"tipo": "pular"})
        eventos = [x["evento"] for x in antes if x["tipo"] == "evento"]
        self.assertEqual(eventos, [{"tipo": "fila_acabou"}])

    def test_aviso_do_reprodutor_vira_evento(self):
        ws, _ = self.conectar()
        self.comando(ws, 1, {"tipo": "adicionar", "musicas": [m(1), m(2)]})
        r = self.reprodutores[0]
        r.agendar(r.ouvinte.fim)  # como o reprodutor de verdade avisa: pelo loop
        msg = ws.receive_json()
        while msg["tipo"] != "evento":
            msg = ws.receive_json()
        self.assertEqual(msg["evento"]["tipo"], "tocando_agora")
        self.assertEqual(msg["evento"]["musica"]["titulo"], "Música 2")

    def test_comando_torto_responde_erro_sem_derrubar(self):
        ws, _ = self.conectar()
        resposta, _ = self.comando(ws, 1, {"tipo": "dançar"})
        self.assertFalse(resposta["ok"])
        self.assertIn("inválido", resposta["erro"])
        resposta, _ = self.comando(ws, 2, {"tipo": "adicionar", "musicas": [{"titulo": "sem link"}]})
        self.assertFalse(resposta["ok"])
        ws.send_text("isso não é json")
        self.assertEqual(ws.receive_json()["erro"], "mensagem não é JSON")
        resposta, _ = self.comando(ws, 3, {"tipo": "volume", "valor": 30})
        self.assertEqual(resposta["resultado"], {"volume": 30})

    def test_ping(self):
        ws, _ = self.conectar()
        ws.send_json({"tipo": "ping"})
        self.assertEqual(ws.receive_json(), {"tipo": "pong"})

    def test_site_estranho_nao_conecta(self):
        with self.assertRaises(WebSocketDisconnect) as erro:
            with self.cliente.websocket_connect(WS, headers={"origin": "https://site-malvado.example"}) as ws:
                ws.receive_json()
        self.assertEqual(erro.exception.code, 4403)

    def test_programa_local_sem_origin_conecta(self):
        with self.cliente.websocket_connect(WS) as ws:
            self.assertEqual(ws.receive_json()["tipo"], "ola")


class TestDiscord(Base):
    def test_token_guarda_na_pasta_e_conecta(self):
        token = "x" * 70
        r = self.cliente.put("/discord/token", json={"token": token})
        self.assertEqual(r.json()["situacao"], "conectado")
        self.assertEqual(self.bot.tokens, [token])
        arquivo = self.pasta / "discord.json"
        self.assertIn(token, arquivo.read_text())
        self.assertEqual(self.cliente.put("/discord/token", json={"token": "curto"}).status_code, 422)
        self.assertEqual(self.cliente.post("/discord/religar").status_code, 200)
        self.assertEqual(self.cliente.delete("/discord/token").json()["situacao"], "desligado")
        self.assertEqual(self.cliente.post("/discord/religar").status_code, 409)
        self.assertFalse(arquivo.exists())

    def test_entrar_sair_e_ouvir_aqui(self):
        self.assertEqual(self.cliente.post("/discord/entrar", json={"canalId": "123456789012345678"}).json()["canal"], "123456789012345678")
        r = self.cliente.post("/discord/entrar", json={"canalId": "404404"})
        self.assertEqual((r.status_code, r.json()["detail"]), (409, "não achei esse canal de voz"))
        self.assertEqual(self.cliente.post("/discord/entrar", json={"canalId": "abc"}).status_code, 422)
        self.assertIsNone(self.cliente.post("/discord/sair").json()["canal"])
        self.assertFalse(self.cliente.put("/discord/ouvir-aqui", json={"ligado": False}).json()["ouvirAqui"])

    def test_painel_fica_sabendo_na_hora(self):
        with self.cliente.websocket_connect(WS, headers=PAINEL) as ws:
            for _ in range(4):
                ws.receive_json()
            self.cliente.post("/discord/entrar", json={"canalId": "123456789012345678"})
            msg = ws.receive_json()
            while msg["tipo"] != "discord":
                msg = ws.receive_json()
            self.assertEqual(msg["discord"]["canal"], "123456789012345678")


class TestPorteiro(Base):
    """Os ataques da revisão de 07/11: site estranho e DNS rebinding."""

    MAL = {"origin": "https://site-malvado.example"}

    def test_site_estranho_nao_reescreve_o_acervo(self):
        faixa = self.cliente.get("/acervo").json()["musicas"][0]
        csv = f"id;nome;franquia;link;temas;categorias;comentario\r\n{faixa['id']};;;;hackeado;;\r\n"
        # POST "simples" (text/plain): o navegador manda sem preflight de CORS.
        r = self.cliente.post("/acervo/planilha?aplicar=true", content=csv.encode(), headers={**self.MAL, "content-type": "text/plain"})
        self.assertEqual(r.status_code, 403)
        self.assertFalse((self.pasta / "ajustes.json").exists())

    def test_site_estranho_nao_mexe_no_bot(self):
        for rota in ("/discord/sair", "/discord/religar", "/discord/assobio", "/acervo/planilha/salvar", "/abrir"):
            with self.subTest(rota):
                self.assertEqual(self.cliente.post(rota, headers=self.MAL).status_code, 403)

    def test_site_estranho_nem_le(self):
        self.assertEqual(self.cliente.get("/acervo", headers=self.MAL).status_code, 403)

    def test_dns_rebinding(self):
        r = self.cliente.get("/acervo", headers={"host": "evil.example:47824"})
        self.assertEqual(r.status_code, 403)
        self.assertIn("endereço não permitido", r.json()["detail"])
        with self.assertRaises(WebSocketDisconnect):
            with self.cliente.websocket_connect(WS, headers={"host": "evil.example:47824"}) as ws:
                ws.receive_json()

    def test_painel_e_programas_locais_passam(self):
        for origem in ("http://localhost:5173", "http://localhost:47823", "tauri://localhost"):
            with self.subTest(origem):
                self.assertEqual(self.cliente.get("/saude", headers={"origin": origem}).status_code, 200)
        self.assertEqual(self.cliente.get("/saude").status_code, 200)  # curl, script
        self.assertEqual(self.cliente.get("/saude", headers={"host": "localhost:47824"}).status_code, 200)


class TestAbrir(Base):
    def test_so_abre_discord_e_github(self):
        from unittest import mock

        with mock.patch("webbrowser.open", return_value=True) as abrir:
            ok = self.cliente.post("/abrir", json={"url": "https://discord.com/oauth2/authorize?client_id=1"})
            self.assertEqual(ok.status_code, 200)
            abrir.assert_called_once()
            self.assertEqual(self.cliente.post("/abrir", json={"url": "https://site-malvado.example"}).status_code, 400)
            self.assertEqual(self.cliente.post("/abrir", json={"url": "file:///etc/passwd"}).status_code, 400)
            self.assertEqual(abrir.call_count, 1)


class TestRest(Base):
    def test_saude(self):
        r = self.cliente.get("/saude").json()
        self.assertTrue(r["ok"])
        self.assertEqual(r["protocolo"], 1)

    def test_cors_so_pro_painel(self):
        ok = self.cliente.get("/saude", headers=PAINEL)
        self.assertEqual(ok.headers.get("access-control-allow-origin"), "http://localhost:5173")
        estranho = self.cliente.get("/saude", headers={"origin": "https://site-malvado.example"})
        self.assertIsNone(estranho.headers.get("access-control-allow-origin"))

    def test_acervo_traz_o_dataset(self):
        r = self.cliente.get("/acervo").json()
        self.assertGreater(len(r["musicas"]), 100)
        self.assertIn("categorias", r["vocabulario"])

    def test_aprender_faixa(self):
        nova = {"titulo": "Música da Taverna", "link": "https://youtu.be/xyz789", "temas": ["taverna", "alegre"]}
        r = self.cliente.post("/acervo/faixas", json=nova)
        self.assertEqual(r.status_code, 201)
        faixa = r.json()
        self.assertEqual(faixa["link"], "https://www.youtube.com/watch?v=xyz789")
        self.assertEqual(faixa["origem"]["nome"], "Descoberta em mesa")
        self.assertIn(faixa["id"], {f["id"] for f in self.cliente.get("/acervo").json()["musicas"]})
        self.assertTrue((self.pasta / "aprendidas.json").exists())
        # De novo: já está lá.
        self.assertEqual(self.cliente.post("/acervo/faixas", json=nova).status_code, 409)

    def test_aprender_faixa_que_ja_esta_no_dataset(self):
        existente = self.cliente.get("/acervo").json()["musicas"][0]
        r = self.cliente.post("/acervo/faixas", json={"titulo": "x", "link": existente["link"], "temas": []})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["detail"]["faixa"]["id"], existente["id"])

    def test_editar_faixa(self):
        faixa = self.cliente.get("/acervo").json()["musicas"][0]
        r = self.cliente.patch(f"/acervo/faixas/{faixa['id']}", json={"temas": ["Taverna", "alegre"]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["temas"], ["taverna", "alegre"])
        self.assertTrue((self.pasta / "ajustes.json").exists())
        novo = next(f for f in self.cliente.get("/acervo").json()["musicas"] if f["id"] == faixa["id"])
        self.assertEqual(novo["temas"], ["taverna", "alegre"])
        self.assertEqual(self.cliente.patch("/acervo/faixas/nada", json={"temas": ["x"]}).status_code, 404)

    def test_planilha(self):
        r = self.cliente.get("/acervo/planilha")
        self.assertIn("attachment", r.headers["content-disposition"])
        texto = r.content.decode("utf-8")
        self.assertTrue(texto.startswith("\ufeffid;"))

        salvo = self.cliente.post("/acervo/planilha/salvar").json()["caminho"]
        self.assertTrue(salvo.startswith(str(self.pasta / "Downloads")))

        cabecalho, primeira, *resto = texto.lstrip("\ufeff").split("\r\n")
        id_ = primeira.split(";")[0]
        editada = f"{cabecalho}\r\n{id_};;;;taverna, alegre;;\r\n"
        previa = self.cliente.post("/acervo/planilha", content=editada.encode(), headers={"content-type": "text/csv"}).json()
        self.assertEqual((previa["mudaram"], previa["aplicado"]), (1, False))
        self.assertFalse((self.pasta / "ajustes.json").exists())
        feito = self.cliente.post("/acervo/planilha?aplicar=true", content=editada.encode()).json()
        self.assertTrue(feito["aplicado"])
        self.assertTrue((self.pasta / "ajustes.json").exists())
        self.assertEqual(self.cliente.post("/acervo/planilha", content=b"a;b\n1;2").status_code, 400)

    def test_playlists(self):
        self.assertEqual(self.cliente.get("/playlists").json(), [])
        p = {"id": "p1", "nome": "Sessão 12", "musicas": [m(1)], "atualizadaEm": 1}
        self.assertEqual(self.cliente.put("/playlists/p1", json=p).status_code, 200)
        self.cliente.put("/playlists/p2", json={**p, "id": "p2", "nome": "Cripta"})
        self.assertEqual([x["nome"] for x in self.cliente.get("/playlists").json()], ["Cripta", "Sessão 12"])
        self.cliente.put("/playlists/p1", json={**p, "nome": "Sessão 12 (nova)"})
        self.assertEqual([x["nome"] for x in self.cliente.get("/playlists").json()], ["Sessão 12 (nova)", "Cripta"])
        self.assertEqual(self.cliente.delete("/playlists/p2").status_code, 204)
        self.assertEqual(self.cliente.delete("/playlists/p2").status_code, 404)
        self.assertEqual(self.cliente.put("/playlists/outro", json=p).status_code, 400)

    def test_youtube(self):
        r = self.cliente.get("/youtube/info", params={"link": "https://youtu.be/abc"})
        self.assertEqual(r.json()["titulo"], "Vídeo Colado")
        self.assertEqual(self.cliente.get("/youtube/info", params={"link": "oi"}).status_code, 400)
        r = self.cliente.post("/youtube/buscar", json={"texto": "taverna medieval"})
        self.assertEqual(r.json()["titulo"], "Achei taverna medieval")
        self.assertEqual(self.cliente.post("/youtube/buscar", json={"texto": "nada"}).status_code, 404)
        r = self.cliente.post("/youtube/buscar", json={"texto": "quebra"})
        self.assertEqual((r.status_code, r.json()["detail"]), (502, "o vídeo é privado"))


if __name__ == "__main__":
    unittest.main()
