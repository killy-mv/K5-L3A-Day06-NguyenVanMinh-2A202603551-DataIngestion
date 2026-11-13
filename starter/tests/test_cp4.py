"""CP4 integration checks use live pgvector and real local model, no gold test queries."""
import math
import os
import unittest
from pathlib import Path
from dotenv import load_dotenv
from src.embeddings import MyEmbedder,DEFAULT_MODEL
from src.store import PgVectorStore

ROOT=Path(__file__).resolve().parents[2]
load_dotenv(ROOT/'starter/.env')

class CP4UnitTests(unittest.TestCase):
    def test_invalid_vectors_and_filters(self):
        store=PgVectorStore('postgresql://unused',3,'temporary')
        with self.assertRaises(ValueError): store._vector([1,2])
        with self.assertRaises(ValueError): store._vector([0,0,0])
        with self.assertRaises(ValueError): store._vector([1,math.nan,2])
        with self.assertRaises(ValueError): store.search('X',[1,0,0])
        with self.assertRaises(ValueError): store.search('A',[1,0,0],top_k=0)
        with self.assertRaises(ValueError): store.search('B',[1,0,0],filters={'page':23})
        with self.assertRaises(ValueError): store.search('C',[1,0,0],filters={'chapter':''})

    def test_live_store_and_filter(self):
        url=os.environ.get('DATABASE_URL')
        self.assertTrue(url,'DATABASE_URL is required for integration testing')
        store=PgVectorStore(url,384,DEFAULT_MODEL+'@1110a243fdf4706b3f48f1d95db1a4f5529b4d41')
        self.assertEqual(store.counts(),{'A':170,'B':160})
        query=[1.0]+[0.0]*383
        a=store.search('A',query,top_k=3)
        b=store.search('B',query,top_k=3)
        c=store.search('C',query,top_k=3)
        self.assertEqual([r['chunk_id'] for r in b],[r['chunk_id'] for r in c])
        self.assertEqual(len(a),3)
        filtered=store.search('C',query,top_k=3,filters={'chapter':'chapter_4'})
        self.assertEqual(len(filtered),3)
        self.assertTrue(all(r['chapter']=='chapter_4' for r in filtered))
        self.assertTrue(all(r['document_id']=='thinkpython2_pdf' for r in filtered))
        self.assertEqual(store.search('C',query,filters={'chapter':'does_not_exist'}),[])

    def test_real_model_encoding(self):
        model=MyEmbedder()
        vec=model.embed_query('A function can take arguments.')
        self.assertEqual(len(vec),384)
        self.assertAlmostEqual(sum(x*x for x in vec),1.0,places=4)
        self.assertEqual(model.embed_documents([]),[])
        with self.assertRaises(ValueError):model.embed_documents([''])

if __name__=='__main__': unittest.main()
