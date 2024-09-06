import os
from threading import Lock

from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer


PINECONE_INDEX_NAME = "docs-index"
TRANSFORMER_MODEL = 'all-MiniLM-L6-v2'
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')

class PineConeDB:
    _instance = None
    _lock = Lock() 

    def __init__(self):
        raise RuntimeError('Call instance() instead')
    
    @classmethod
    def instance(cls):
        if cls._instance is None:
            with cls._lock:
                cls._instance = cls.__new__(cls)
                pc = Pinecone(api_key=PINECONE_API_KEY, environment="production")
                if PINECONE_INDEX_NAME not in str(pc.list_indexes()):
                    try:
                        res = pc.create_index(
                            name=PINECONE_INDEX_NAME,
                            dimension=384,
                            metric="cosine",
                            spec=ServerlessSpec(
                                cloud="aws",
                                region="us-east-1"
                            ) 
                        )
                        print(f"Created new pinecone index")
                    except Exception as e:
                        print(f"Error creating pinecone index: {str(e)}")
                cls._instance.index = pc.Index(PINECONE_INDEX_NAME)
                cls._instance.pc = pc
        return cls._instance

    def query_docs(self, query, top_k, filters):
        model = SentenceTransformer(TRANSFORMER_MODEL)
        query_vector = model.encode([query], convert_to_tensor=False, normalize_embeddings=True)
        # Convert to list if not already
        query_vector = query_vector[0].tolist()
        return self.index.query(vector=[query_vector], top_k=top_k, filter=filters, include_metadata=True)
