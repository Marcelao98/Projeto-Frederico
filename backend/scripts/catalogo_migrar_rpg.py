"""Leva as faixas do acervo/musicas.json pro catálogo novo (acervo/catalogo/*.csv).

Etapa 2 do banco do Fredify (docs/etapas/banco-fredify.md). Usa o de-para
das tags (acervo/catalogo/mapa_tags_acervo.csv) e completa o que o JSON não
tem (gênero, ano, energia, animação, popularidade) com regras simples e
explícitas, marcadas como quem_marcou=claude. As faixas entram no lote
"rpg-legado": o compilador cobra ano e fonte oficial delas só como aviso.

Rodar de dentro de backend/:  python scripts/catalogo_migrar_rpg.py
Reescreve musicas.csv, obras.csv, artistas.csv, musica_*.csv e fontes.csv.
(Roda de novo sem problema; o musicas.json continua sendo a fonte do app
até a etapa 4.)
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "backend"))
from freddy.nucleo.texto import slug  # noqa: E402

CAT = RAIZ / "acervo" / "catalogo"
LOTE = "rpg-legado"

# Obras: o "origem" do JSON e as que estavam escondidas em "Descoberta em mesa".
OBRAS = {
    "umineko": ("Umineko no Naku Koro ni", "visual novel", 2007),
    "fire-emblem-three-houses": ("Fire Emblem: Three Houses", "jogo", 2019),
    "elden-ring": ("Elden Ring", "jogo", 2022),
    "hollow-knight": ("Hollow Knight", "jogo", 2017),
    "subahibi": ("Subarashiki Hibi", "visual novel", 2010),
    "nier-automata": ("NieR: Automata", "jogo", 2017),
    "bloodborne": ("Bloodborne", "jogo", 2015),
    "dark-souls": ("Dark Souls", "jogo", 2011),
    "skyrim": ("The Elder Scrolls V: Skyrim", "jogo", 2011),
    "zelda-ocarina-of-time": ("The Legend of Zelda: Ocarina of Time", "jogo", 1998),
    "zelda-majoras-mask": ("The Legend of Zelda: Majora's Mask", "jogo", 2000),
    "witcher-3": ("The Witcher 3: Wild Hunt", "jogo", 2015),
    "pokemon": ("Pokémon", "jogo", None),
    "trails-in-the-sky-3rd": ("The Legend of Heroes: Trails in the Sky the 3rd", "jogo", 2007),
    "return-of-the-obra-dinn": ("Return of the Obra Dinn", "jogo", 2018),
    "spectral-sails": ("Spectral Sails", "jogo", None),
}
APELIDOS = {
    "umineko": "umineko|umineko no naku", "fire-emblem-three-houses": "fire emblem|fe3h|three houses|fe 3 houses",
    "subahibi": "subahibi|subarashiki hibi", "nier-automata": "nier|nier automata", "dark-souls": "dark souls",
    "skyrim": "skyrim", "zelda-ocarina-of-time": "zelda|ocarina of time", "zelda-majoras-mask": "zelda|majora|majoras mask|majora mask",
    "witcher-3": "witcher|witcher 3", "trails-in-the-sky-3rd": "trails in the sky|trails", "return-of-the-obra-dinn": "obra dinn",
}
ORIGEM_OBRA = {
    "Umineko no Naku Koro ni": "umineko", "Fire Emblem: Three Houses": "fire-emblem-three-houses",
    "Elden Ring": "elden-ring", "Hollow Knight": "hollow-knight",
    "Subarashiki Hibi (Subahibi)": "subahibi", "Nier: Automata": "nier-automata",
    "Bloodborne": "bloodborne", "Dark Souls": "dark-souls",
}
# Compositor quando a trilha inteira é de uma pessoa só (só onde é certo).
COMPOSITOR = {"hollow-knight": "Christopher Larkin", "nier-automata": "Keiichi Okabe",
              "dark-souls": "Motoi Sakuraba"}

# As faixas "Descoberta em mesa": o que o nome do vídeo não diz.
# começo do id -> (título, obra, artistas, gêneros {id: peso}, ano, idioma, tem_voz, popularidade, oficial)
P = "descoberta-em-mesa-"
EXTRA = {
    P + "the-elder-scrolls-v-skyrim": ("Ragnar the Red", "skyrim", [], {"trilha-de-jogo": 1, "medieval": 0.7}, 2011, "en", 1, 45, 0),
    P + "milton-nascimento-lo-borge": ("Clube da Esquina nº 2", None, ["Milton Nascimento", "Lô Borges"], {"clube-da-esquina": 1}, 1972, "pt", 1, 65, 0),
    P + "zelda-original-soundtrack-": ("Song of Storms", "zelda-ocarina-of-time", [], {"trilha-de-jogo": 1}, 1998, None, 0, 60, 0),
    P + "reginaldo-rossi-garcom-ofi": ("Garçom", None, ["Reginaldo Rossi"], {"brega-romantico": 1}, 1987, "pt", 1, 80, 1),
    P + "gloria-gaynor-i-will-survi": ("I Will Survive", None, ["Gloria Gaynor"], {"disco": 1}, 1978, "en", 1, 95, 0),
    P + "trio-parada-dura-grao-de-a": ("Grão de Areia", None, ["Trio Parada Dura"], {"sertanejo-raiz": 1}, None, "pt", 1, 55, 0),
    P + "tim-maia-ela-partiu-offici": ("Ela Partiu", None, ["Tim Maia"], {"soul-brasileiro": 1}, None, "pt", 1, 70, 1),
    P + "gwyn-lord-of-cinder": ("Gwyn, Lord of Cinder", "dark-souls", ["Motoi Sakuraba"], {"trilha-de-jogo": 1}, 2011, None, 0, 60, 0),
    P + "d-d-background-music-city-": ("City/Town Square - Day", None, [], {"trilha-de-jogo": 1, "medieval": 0.6}, None, None, 0, 20, 0),
    P + "frozen-tundra-arctic-ambie": ("Frozen Tundra (Arctic Ambience)", None, [], {"paisagem-sonora": 1, "ambient": 0.7}, None, None, 0, 20, 0),
    P + "the-witcher-3-wild-hunt-os": ("The Fields of Ard Skellig", "witcher-3", [], {"trilha-de-jogo": 1, "nordico": 0.6}, 2015, None, 1, 55, 0),
    P + "1-hour-of-dungeon-and-drag": ("Mystery Music: Investigation", None, [], {"ambient": 1, "trilha-de-jogo": 0.6}, None, None, 0, 20, 0),
    P + "blizzard-ambience-and-musi": ("Blizzard Ambience and Music", None, [], {"paisagem-sonora": 1, "ambient": 0.7}, None, None, 0, 20, 0),
    P + "d-d-ambience-damp-cave": ("Damp Cave", None, [], {"paisagem-sonora": 1, "dark-ambient": 0.6}, None, None, 0, 20, 0),
    P + "5e-d-d-combat-music-d-d-ic": ("Combat Music (Icewind Dale)", None, [], {"epic-music": 1, "trilha-de-jogo": 0.7}, None, None, 0, 20, 0),
    P + "paul-vs-gladion-pokemon-ba": ("Paul vs Gladion (Pokémon Battle)", "pokemon", [], {"trilha-de-jogo": 1}, None, None, 0, 30, 0),
    P + "dnd-calm-fantasy-music-for": ("Calm Fantasy Music for Adventure and Exploration", None, [], {"trilha-de-jogo": 1, "celta": 0.5}, None, None, 0, 20, 0),
    P + "aline-barros-ressuscita-me": ("Ressuscita-me", None, ["Aline Barros"], {"gospel-pop": 1}, None, "pt", 1, 75, 1),
    P + "hope": ("Hope", "umineko", [], {"trilha-de-jogo": 1}, 2007, None, 0, 30, 0),
    P + "song-of-healing-the-legend": ("Song of Healing", "zelda-majoras-mask", [], {"trilha-de-jogo": 1}, 2000, None, 0, 50, 0),
    P + "trails-in-the-sky-3rd-ost-": ("Cradle Where Feelings Rest", "trails-in-the-sky-3rd", [], {"trilha-de-jogo": 1}, 2007, None, 0, 30, 0),
    P + "trio-parada-dura-ultimo-ad": ("Último Adeus", None, ["Trio Parada Dura", "Eduardo Costa"], {"sertanejo-raiz": 1}, None, "pt", 1, 50, 0),
    P + "wasteland-d-d-ttrpg-music-": ("Wasteland", None, [], {"ambient": 1, "trilha-de-jogo": 0.6}, None, None, 0, 20, 0),
    P + "deep-waters-d-d-ttrpg-musi": ("Deep Waters", None, [], {"ambient": 1, "trilha-de-jogo": 0.6}, None, None, 0, 20, 0),
    P + "pedras-escondidas": ("Pedras Escondidas", None, [], {"trilha-de-jogo": 1}, None, None, 0, 20, 0),
    P + "weight-of-the-world-piano-": ("Weight of the World (Piano Collections)", "nier-automata", ["Keiichi Okabe"], {"trilha-de-jogo": 1}, 2017, None, 0, 60, 0),
    P + "return-of-the-obra-dinn-so": ("Theme", "return-of-the-obra-dinn", [], {"trilha-de-jogo": 1}, 2018, None, 0, 40, 0),
    P + "spectral-sails-original-ga": ("Spectral Sails", "spectral-sails", [], {"trilha-de-jogo": 1}, None, None, 0, 20, 0),
}

# Energia (1 calma … 5 pancada) e animação (1 triste … 5 alegre) de cada clima/ocasião.
ENERGIA = {
    "calmo": 1, "sonhador": 2, "contemplativo": 2, "aconchegante": 2, "melancolico": 2, "triste": 2,
    "saudade": 2, "sagrado": 2, "romantico": 2, "nostalgico": 2, "misterioso": 2, "magico": 2,
    "sombrio": 3, "assustador": 3, "estranho": 3, "dramatico": 3, "tenso": 3, "sofrido": 2,
    "esperancoso": 3, "alegre": 3, "engracado": 3, "sensual": 3, "confiante": 4,
    "epico": 4, "empolgante": 4, "animado": 4, "festivo": 4, "agressivo": 5,
    "rpg-descanso": 1, "rpg-chefe": 5, "rpg-combate": 5, "rpg-perseguicao": 5, "rpg-final": 4,
}
FORTE = {"rpg-chefe": 5, "rpg-combate": 4, "rpg-perseguicao": 4, "agressivo": 4}  # energia mínima
ANIMACAO = {
    "triste": 1, "sofrido": 1, "assustador": 1, "melancolico": 2, "saudade": 2, "sombrio": 2,
    "tenso": 2, "dramatico": 2, "agressivo": 2, "misterioso": 3, "calmo": 3, "contemplativo": 3,
    "magico": 3, "sagrado": 3, "epico": 3, "nostalgico": 3, "estranho": 3, "sonhador": 3,
    "empolgante": 4, "esperancoso": 4, "romantico": 4, "aconchegante": 4, "animado": 4,
    "confiante": 4, "sensual": 4, "alegre": 5, "festivo": 5, "engracado": 5,
}
# Quando só há um clima: o vizinho mais óbvio (regra do "≥ 2 climas").
VIZINHO = {
    "triste": "melancolico", "melancolico": "triste", "calmo": "contemplativo", "contemplativo": "calmo",
    "epico": "empolgante", "empolgante": "epico", "tenso": "sombrio", "sombrio": "tenso",
    "alegre": "animado", "animado": "alegre", "assustador": "sombrio", "misterioso": "tenso",
    "magico": "sonhador", "sonhador": "calmo", "sagrado": "calmo", "esperancoso": "calmo",
    "nostalgico": "saudade", "saudade": "nostalgico", "romantico": "calmo", "engracado": "alegre",
    "estranho": "misterioso", "agressivo": "tenso", "dramatico": "triste", "aconchegante": "calmo",
    "festivo": "alegre", "sofrido": "triste", "confiante": "empolgante", "sensual": "romantico",
}


def ler(nome: str) -> list[dict]:
    with open(CAT / nome, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def escrever(nome: str, cabecalho: list[str], linhas: list[list]) -> None:
    with open(CAT / nome, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n")
        w.writerow(cabecalho)
        w.writerows([["" if v is None else v for v in linha] for linha in linhas])


def main() -> None:
    faixas = json.loads((RAIZ / "acervo" / "musicas.json").read_text(encoding="utf-8"))["musicas"]
    mapa = {r["tag_antiga"]: r["destino"].split("|") for r in ler("mapa_tags_acervo.csv")}
    perfil = {p["ocasiao"]: p for p in ler("ocasioes_perfil.csv")}
    gaveta = {t["id"]: t["gaveta"] for t in ler("tags.csv")}

    musicas, mus_art, mus_gen, mus_tag, fontes = [], [], [], [], []
    artistas: dict[str, str] = {}
    obras_usadas: set[str] = set()

    def artista(nome: str) -> str:
        artistas[slug(nome)] = nome
        return slug(nome)

    for x in faixas:
        mid = x["id"]
        extra = next((v for k, v in EXTRA.items() if mid == k or mid.startswith(k)), None)
        if extra:
            titulo, obra, nomes_art, generos, ano, idioma, voz, pop, oficial = extra
        else:
            obra = ORIGEM_OBRA[x["origem"]["nome"]]
            titulo, generos, ano = x["nome"], {"trilha-de-jogo": 1}, OBRAS[obra][2]
            nomes_art = [COMPOSITOR[obra]] if obra in COMPOSITOR else []
            idioma, voz, pop, oficial = None, 0, 30, 0

        tags: dict[str, tuple[float, str]] = {}  # id -> (peso, quem)
        campos: set[str] = set()
        revisar = 0
        for tema in x["temas"]:
            for destino in mapa[tema]:
                tipo, alvo = destino.split(":", 1)
                if tipo in ("clima", "ocasiao", "tema", "instrumento", "cenario"):
                    tags[alvo] = (1.0, "curadoria")
                elif tipo == "genero":
                    generos = {**generos, alvo: 1}
                elif tipo == "campo":
                    campos.add(alvo)
                elif tipo == "revisar":
                    revisar = 1
                # artista/obra/epoca/descartar: já estão no EXTRA/OBRAS acima

        if "com-voz" in campos:
            voz = 1
        if "sem-voz" in campos:
            voz = 0
        essencial = 1 if "essencial" in campos else 0
        if essencial and pop < 60:
            pop = 60

        climas = [t for t in tags if gaveta[t] == "clima"]
        if not revisar:
            # ≥ 2 climas: primeiro pelo perfil da ocasião marcada, depois o vizinho.
            for oc in [t for t in tags if gaveta[t] == "ocasiao"]:
                for c in perfil[oc]["climas_combinam"].split("|"):
                    if len(climas) >= 2:
                        break
                    if c not in tags:
                        tags[c] = (0.5, "claude")
                        climas.append(c)
            for c in list(climas):
                if len(climas) >= 2:
                    break
                v = VIZINHO[c]
                if v not in tags:
                    tags[v] = (0.4, "claude")
                    climas.append(v)
            if len(climas) < 2:
                for c in ("calmo", "contemplativo"):  # só cenário/ambiente marcado
                    if c not in tags and len(climas) < 2:
                        tags[c] = (0.4, "claude")
                        climas.append(c)

        marcas = list(tags)
        if marcas and not revisar:
            valores = [ENERGIA[t] for t in marcas if t in ENERGIA]
            energia = round(sum(valores) / len(valores)) if valores else 3
            energia = max([energia] + [FORTE[t] for t in marcas if t in FORTE])
            anim = [ANIMACAO[t] for t in marcas if t in ANIMACAO]
            animacao = round(sum(anim) / len(anim)) if anim else 3
        else:
            energia = animacao = None

        if obra:
            obras_usadas.add(obra)
        musicas.append([mid, titulo, ano, None, idioma, obra, energia, animacao, voz,
                        0, 0, 0, pop, essencial, None, None, LOTE, revisar, x["nome"]])
        for i, n in enumerate(nomes_art):
            mus_art.append([mid, artista(n), "principal" if i == 0 else "feat"])
        for g, peso in generos.items():
            mus_gen.append([mid, g, peso])
        for t, (peso, quem) in tags.items():
            mus_tag.append([mid, t, peso, quem])
        tipo_fonte = "youtube" if x["escopo"] == "faixa_individual" else "youtube-album"
        fontes.append([mid, tipo_fonte, x["link"], oficial, 1, None])

    escrever("musicas.csv", ["id", "titulo", "ano", "duracao", "idioma", "obra", "energia", "animacao",
                             "tem_voz", "canta_junto", "ao_vivo", "explicita", "popularidade", "essencial",
                             "mbid", "isrc", "lote", "revisar", "nome_original"], musicas)
    escrever("obras.csv", ["id", "nome", "tipo", "ano", "apelidos"],
             [[o, *OBRAS[o], APELIDOS.get(o, "")] for o in sorted(obras_usadas)])
    escrever("artistas.csv", ["id", "nome", "tipo", "pais", "regiao", "ano_inicio", "mbid"],
             [[a, n, None, None, None, None, None] for a, n in sorted(artistas.items())])
    escrever("musica_artista.csv", ["musica", "artista", "papel"], mus_art)
    escrever("musica_genero.csv", ["musica", "genero", "peso"], mus_gen)
    escrever("musica_tag.csv", ["musica", "tag", "peso", "quem_marcou"], mus_tag)
    escrever("fontes.csv", ["musica", "tipo", "endereco", "oficial", "viva", "conferida_em"], fontes)
    print(f"{len(musicas)} músicas, {len(obras_usadas)} obras, {len(artistas)} artistas, "
          f"{len(mus_tag)} marcações, {sum(m[17] for m in musicas)} pra revisar")


if __name__ == "__main__":
    main()
