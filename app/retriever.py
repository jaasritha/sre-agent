import logging
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from pathlib import Path
logger = logging.getLogger(__name__)
CHROMA_DIR = Path("data/chroma_db")
COLLECTION_NAME = "sre_postmortems"

_client = None
_collection = None

def get_chroma_collection():
    global _client, _collection
    if _collection is not None:
        return _collection
    try:
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        embedder = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        _collection = _client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=embedder)
        logger.info("Chroma collection initialized successfully.")
        return _collection
    except Exception as e:
        logger.error(f"Error initializing Chroma collection: {e}")
        raise

def get_similar_postmortems(query: str, k: int = 2,) -> list[str]:
    if not CHROMA_DIR.exists():
        logger.warning(f"Chroma directory {CHROMA_DIR} does not exist. Returning empty results.")
        return []
    try:
        collection = get_chroma_collection()
        results = collection.query(
            query_texts=[query],
            n_results=min(k, collection.count())
        )
        documents = results.get('documents', [[]])[0]
        sources = [
            m["source"] for m in results.get('metadatas', [[]])[0]
        ]
        logger.debug("Retrieved similar postmortems with sources: %s", sources)
        return documents
    except Exception as e:
        logger.error(f"Cannot get Chroma collection: {e}")
        return []