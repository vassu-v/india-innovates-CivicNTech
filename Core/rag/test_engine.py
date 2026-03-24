import unittest
import os
import sys
import json
import sqlite3

# Add the current directory to sys.path so we can import engine
sys.path.append(os.path.dirname(__file__))
import engine as rag_engine

class TestRAGEngine(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Ensure we use a test database
        rag_engine.DB_PATH = os.path.join(os.path.dirname(__file__), "test_rag.db")
        rag_engine.init_db()

    def setUp(self):
        rag_engine.truncate_db()

    def test_init_db(self):
        self.assertTrue(os.path.exists(rag_engine.DB_PATH))
        db = sqlite3.connect(rag_engine.DB_PATH)
        cursor = db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_nodes'")
        self.assertIsNotNone(cursor.fetchone())
        db.close()

    def test_store_and_query(self):
        # Store a node
        node_id = rag_engine.store_node(
            domain="commitment_history",
            ward="Ward 42",
            topic="drainage",
            title="Ward 42 Road Repair",
            content="The road in Ward 42 was repaired on Aug 15, 2024. It took 10 days.",
            source_ref="timely_items:101"
        )
        self.assertIsInstance(node_id, int)
        
        # Simple semantic search (using the same content should return it first)
        nodes = rag_engine.query_nodes("Ward 42 road repair", limit=1)
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]['title'], "Ward 42 Road Repair")
        self.assertGreater(nodes[0]['similarity'], 0.5)

    def test_assemble_context(self):
        rag_engine.store_node(
            domain="context_file",
            ward=None,
            topic="demographics",
            title="Ward 42 Census",
            content="Ward 42 has a population of 45,000.",
            source_ref="files:1"
        )
        
        profile = {"name": "Shri Verma", "ward_name": "Ward 42"}
        digest = {"open_right_now": {"critical": 2}}
        
        context = rag_engine.assemble_context(
            "What is the population of Ward 42?", 
            profile=profile, 
            digest=digest
        )
        
        self.assertIn("Shri Verma", context)
        self.assertIn("Critical Items: 2", context)
        self.assertIn("Ward 42 has a population of 45,000", context)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(rag_engine.DB_PATH):
            os.remove(rag_engine.DB_PATH)

if __name__ == "__main__":
    unittest.main()
