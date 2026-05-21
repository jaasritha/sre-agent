import os
import chromadb
from chromadb.utils.embedding_functions import (SentenceTransformerEmbeddingFunction)

from pathlib import Path

POSTMORTEM_DIR = Path("data/postmortems")
CHROMA_DIR = Path("data/chroma_db")
COLLECTION_NAME = "sre_postmortems"
CHUNKS_SIZE = 400


def chunk_text(text, chunk_size=CHUNKS_SIZE):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i+chunk_size])
        chunks.append(chunk)
    return chunks

def ingest():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    embedder = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    collection = client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=embedder)
    md_files = list(POSTMORTEM_DIR.glob("*.md"))
    print(f"Found {len(md_files)} postmortem files to ingest.")
    for md_file in md_files:
        text = md_file.read_text(encoding="utf-8")
        chunks = chunk_text(text, chunk_size=CHUNKS_SIZE)
        for idx, chunk in enumerate(chunks):
            doc_id = f"{md_file.stem}_chunk_{idx}"
            collection.upsert(
                documents=[chunk],
                metadatas={"source": md_file.name, "chunk_index": idx},
                ids=[doc_id]
            )
    print("Ingestion complete.")
if __name__ == "__main__":
    ingest()