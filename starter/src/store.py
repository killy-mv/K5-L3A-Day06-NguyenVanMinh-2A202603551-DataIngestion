"""PostgreSQL 16 + pgvector 0.8.x, exact cosine retrieval with trusted metadata."""
from __future__ import annotations
import math
from typing import Any
import psycopg
from psycopg.types.json import Jsonb
from .models import Chunk

class PgVectorStore:
    """A and B are physical indexes. C is the B index with an optional filter."""
    def __init__(self, database_url: str, dimensions: int, model_name: str = '') -> None:
        if not database_url or not (1 <= dimensions <= 2000):
            raise ValueError('Invalid database URL or embedding dimensions')
        self.url = database_url
        self.dimensions = int(dimensions)
        self.model_name = model_name or 'unspecified'

    def _vector(self, values: list[float]) -> str:
        if len(values) != self.dimensions:
            raise ValueError(f'Expected {self.dimensions} dimensions, got {len(values)}')
        if not all(isinstance(v, (int,float)) and math.isfinite(v) for v in values):
            raise ValueError('Embedding contains non-finite/non-numeric entries')
        if not any(v != 0 for v in values):
            raise ValueError('Zero vector is invalid for cosine similarity')
        return '[' + ','.join(str(float(v)) for v in values) + ']'

    def create_schema(self) -> None:
        with psycopg.connect(self.url) as conn:
            conn.execute('CREATE EXTENSION IF NOT EXISTS vector')
            conn.execute('''CREATE TABLE IF NOT EXISTS day6_embeddings (
              strategy TEXT NOT NULL CHECK (strategy IN ('A','B')),
              chunk_id TEXT NOT NULL,
              model_name TEXT NOT NULL,
              document_id TEXT NOT NULL,
              source TEXT NOT NULL,
              page INTEGER NOT NULL CHECK (page > 0),
              chapter TEXT NOT NULL,
              content TEXT NOT NULL,
              metadata JSONB NOT NULL,
              embedding VECTOR NOT NULL,
              PRIMARY KEY (strategy, chunk_id))''')
            conn.execute('''CREATE INDEX IF NOT EXISTS day6_emb_strategy_chapter
                            ON day6_embeddings (strategy, chapter)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS day6_embedding_config (
              id INTEGER PRIMARY KEY CHECK (id=1), dimensions INTEGER NOT NULL,
              model_name TEXT NOT NULL)''')
            row = conn.execute('SELECT dimensions,model_name FROM day6_embedding_config WHERE id=1').fetchone()
            if row and row != (self.dimensions, self.model_name):
                raise ValueError(f'Existing DB is configured for {row}; expected {self.dimensions}, {self.model_name}')
            if not row:
                conn.execute('INSERT INTO day6_embedding_config VALUES (1,%s,%s)',
                             (self.dimensions, self.model_name))

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> dict[str,int]:
        if strategy not in ('A','B'):
            raise ValueError('Only A and B have physical collections; C reuses B')
        if not chunks or len(chunks) != len(vectors):
            raise ValueError('Nonempty chunks and vectors must have identical length')
        ids = [c.chunk_id for c in chunks]
        if len(set(ids)) != len(ids):
            raise ValueError('Duplicate chunk IDs')
        entries = []
        for c, vector in zip(chunks, vectors):
            chapter = c.metadata.get('chapter')
            if not c.document_id or not c.source or c.page <= 0 or not c.text or not chapter:
                raise ValueError(f'Incomplete source/metadata: {c.chunk_id}')
            entries.append((strategy,c.chunk_id,self.model_name,c.document_id,c.source,
                            c.page,chapter,c.text,Jsonb(c.metadata),self._vector(vector)))
        with psycopg.connect(self.url) as conn:
            conn.cursor().executemany('''INSERT INTO day6_embeddings
                (strategy,chunk_id,model_name,document_id,source,page,chapter,content,metadata,embedding)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)
                ON CONFLICT (strategy,chunk_id) DO UPDATE SET
                  model_name=EXCLUDED.model_name,document_id=EXCLUDED.document_id,
                  source=EXCLUDED.source,page=EXCLUDED.page,chapter=EXCLUDED.chapter,
                  content=EXCLUDED.content,metadata=EXCLUDED.metadata,embedding=EXCLUDED.embedding''', entries)
            cur = conn.execute('DELETE FROM day6_embeddings WHERE strategy=%s AND NOT (chunk_id = ANY(%s))',
                               (strategy, ids))
            deleted = cur.rowcount
            count = conn.execute('SELECT COUNT(*) FROM day6_embeddings WHERE strategy=%s',(strategy,)).fetchone()[0]
        return {'stored': int(count), 'obsolete_removed': int(deleted)}

    def search(self, strategy: str, query_vector: list[float], top_k: int = 3,
               filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if strategy not in ('A','B','C'):
            raise ValueError('Unknown strategy')
        if not (1 <= top_k <= 100):
            raise ValueError('top_k must be 1..100')
        if filters and set(filters) != {'chapter'}:
            raise ValueError('Only validated chapter metadata filtering is supported')
        chapter = (filters or {}).get('chapter')
        if chapter is not None and (not isinstance(chapter,str) or not chapter.strip()):
            raise ValueError('chapter filter must be nonempty')
        vector = self._vector(query_vector)
        where = 'strategy = %s AND model_name = %s'
        args: list[Any] = ['B' if strategy == 'C' else strategy, self.model_name]
        if chapter:
            where += ' AND chapter = %s'
            args.append(chapter)
        sql = f'''SELECT chunk_id,document_id,source,page,chapter,content,metadata,
                  1 - (embedding <=> %s::vector) AS similarity
                  FROM day6_embeddings WHERE {where}
                  ORDER BY embedding <=> %s::vector,chunk_id LIMIT %s'''
        with psycopg.connect(self.url) as conn:
            rows = conn.execute(sql, [vector, *args, vector, top_k]).fetchall()
        return [{'chunk_id':r[0], 'document_id':r[1], 'source':r[2],
                 'page':r[3], 'chapter':r[4], 'text':r[5], 'metadata':r[6],
                 'score':float(r[7])} for r in rows]

    def counts(self) -> dict[str,int]:
        with psycopg.connect(self.url) as conn:
            rows = conn.execute('SELECT strategy,COUNT(*) FROM day6_embeddings GROUP BY strategy').fetchall()
        return {key:int(count) for key,count in rows}
