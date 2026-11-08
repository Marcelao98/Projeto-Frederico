-- O catálogo do Fredify (catalogo.db). Fonte: acervo/catalogo/*.csv.
-- Compilado por freddy/catalogo/compilar.py; trocado inteiro a cada versão.
-- Plano: docs/etapas/banco-fredify.md.

PRAGMA foreign_keys = ON;

CREATE TABLE info (chave TEXT PRIMARY KEY, valor TEXT NOT NULL);

CREATE TABLE artista (
  id TEXT PRIMARY KEY, nome TEXT NOT NULL,
  tipo TEXT CHECK (tipo IN ('solo','dupla','banda','orquestra','grupo') OR tipo IS NULL),
  pais TEXT, regiao TEXT, ano_inicio INTEGER, mbid TEXT
);

CREATE TABLE obra (
  id TEXT PRIMARY KEY, nome TEXT NOT NULL,
  tipo TEXT NOT NULL CHECK (tipo IN ('álbum','jogo','visual novel','anime','filme','novela','série')),
  ano INTEGER
);

CREATE TABLE genero (id TEXT PRIMARY KEY, nome TEXT NOT NULL, pai TEXT REFERENCES genero(id), nota TEXT);

CREATE TABLE tag (
  id TEXT PRIMARY KEY,
  gaveta TEXT NOT NULL CHECK (gaveta IN ('clima','ocasiao','tema','instrumento','cenario')),
  nome TEXT NOT NULL, nota TEXT
);

CREATE TABLE musica (
  id TEXT PRIMARY KEY, titulo TEXT NOT NULL, ano INTEGER, duracao INTEGER, idioma TEXT,
  obra TEXT REFERENCES obra(id),
  energia INTEGER CHECK (energia BETWEEN 1 AND 5),
  animacao INTEGER CHECK (animacao BETWEEN 1 AND 5),
  tem_voz INTEGER NOT NULL CHECK (tem_voz IN (0,1)),
  canta_junto INTEGER NOT NULL DEFAULT 0, ao_vivo INTEGER NOT NULL DEFAULT 0,
  explicita INTEGER NOT NULL DEFAULT 0,
  popularidade INTEGER NOT NULL CHECK (popularidade BETWEEN 0 AND 100),
  essencial INTEGER NOT NULL DEFAULT 0, mbid TEXT, isrc TEXT,
  lote TEXT NOT NULL, revisar INTEGER NOT NULL DEFAULT 0, nome_original TEXT
);

CREATE TABLE musica_artista (
  musica TEXT NOT NULL REFERENCES musica(id), artista TEXT NOT NULL REFERENCES artista(id),
  papel TEXT NOT NULL CHECK (papel IN ('principal','feat')), PRIMARY KEY (musica, artista)
);

CREATE TABLE musica_genero (
  musica TEXT NOT NULL REFERENCES musica(id), genero TEXT NOT NULL REFERENCES genero(id),
  peso REAL NOT NULL CHECK (peso > 0 AND peso <= 1), PRIMARY KEY (musica, genero)
);

CREATE TABLE musica_tag (
  musica TEXT NOT NULL REFERENCES musica(id), tag TEXT NOT NULL REFERENCES tag(id),
  peso REAL NOT NULL CHECK (peso > 0 AND peso <= 1),
  quem_marcou TEXT NOT NULL CHECK (quem_marcou IN ('curadoria','claude','analise','lastfm')),
  PRIMARY KEY (musica, tag)
);

CREATE TABLE fonte (
  musica TEXT NOT NULL REFERENCES musica(id),
  tipo TEXT NOT NULL CHECK (tipo IN ('youtube','youtube-album','arquivo','jamendo')),
  endereco TEXT NOT NULL, oficial INTEGER NOT NULL, viva INTEGER NOT NULL, conferida_em TEXT,
  PRIMARY KEY (musica, endereco)
);

-- As gírias. palavra já normalizada (minúscula, sem acento).
CREATE TABLE palavra (
  palavra TEXT NOT NULL,
  tipo TEXT NOT NULL CHECK (tipo IN ('genero','clima','ocasiao','tema','instrumento','cenario','epoca','campo','obra','artista')),
  alvo TEXT NOT NULL, peso REAL NOT NULL CHECK (peso > 0 AND peso <= 1),
  PRIMARY KEY (palavra, tipo, alvo)
);

CREATE TABLE ocasiao_perfil (
  ocasiao TEXT PRIMARY KEY REFERENCES tag(id),
  generos TEXT NOT NULL, energia_min INTEGER NOT NULL, energia_max INTEGER NOT NULL,
  voz TEXT NOT NULL CHECK (voz IN ('sim','nao','qualquer')),
  climas_combinam TEXT NOT NULL, climas_evitar TEXT NOT NULL
);

CREATE VIRTUAL TABLE busca USING fts5(
  musica UNINDEXED, titulo, artista, obra, generos, tags,
  tokenize = 'unicode61 remove_diacritics 2'
);

CREATE INDEX musica_tag_por_tag ON musica_tag(tag);
CREATE INDEX musica_genero_por_genero ON musica_genero(genero);
