# ============================================================
# services/pinecone_service.py
# Reusable Pinecone utility service.
# Handles: index creation, upsert, update, delete, fetch vectors.
# Uses sentence-transformers (all-MiniLM-L6-v2) for embedding generation.
# ============================================================

from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import os
import logging

load_dotenv()

logger = logging.getLogger(__name__)


# ============================================================
# PineconeService class
# Singleton-style service — instantiate once and reuse
# ============================================================
class PineconeService:
    def __init__(self):
        # Load Pinecone configuration from environment variables
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.environment = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "job-embeddings")
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

        # Initialize Pinecone client
        self.pc = Pinecone(api_key=self.api_key)

        # Initialize sentence-transformers embedding model
        # all-MiniLM-L6-v2 produces 384-dimensional vectors — lightweight and accurate
        logger.info(f"Loading embedding model: {self.embedding_model_name}")
        self.embedding_model = SentenceTransformer(self.embedding_model_name)

        # Connect to (or create) Pinecone index
        self.index = self._get_or_create_index()

    # ============================================================
    # Create Pinecone index if it doesn't already exist
    # Uses ServerlessSpec for cloud-based serverless deployment
    # ============================================================
    def _get_or_create_index(self):
        existing_indexes = [idx.name for idx in self.pc.list_indexes()]

        if self.index_name not in existing_indexes:
            logger.info(f"Creating Pinecone index: {self.index_name}")
            self.pc.create_index(
                name=self.index_name,
                dimension=384,           # Matches all-MiniLM-L6-v2 output dimension
                metric="cosine",         # Cosine similarity for semantic matching
                spec=ServerlessSpec(
                    cloud="aws",
                    region=self.environment
                )
            )
            logger.info(f"Index '{self.index_name}' created successfully")
        else:
            logger.info(f"Connected to existing Pinecone index: {self.index_name}")

        return self.pc.Index(self.index_name)

    # ============================================================
    # Generate embedding vector from text using sentence-transformers
    # Returns a 384-dimensional float list
    # ============================================================
    def generate_embedding(self, text: str) -> list[float]:
        # Encode the text and convert to Python list
        embedding = self.embedding_model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    # ============================================================
    # Build a text representation of the job for embedding
    # Concatenates key fields to create a rich semantic representation
    # ============================================================
    def build_job_embedding_text(self, job_data: dict) -> str:
        parts = []
        if job_data.get("title"):
            parts.append(f"Job Title: {job_data['title']}")
        if job_data.get("department"):
            parts.append(f"Department: {job_data['department']}")
        if job_data.get("description"):
            parts.append(f"Description: {job_data['description']}")
        if job_data.get("required_skills"):
            parts.append(f"Required Skills: {job_data['required_skills']}")
        if job_data.get("experience"):
            parts.append(f"Experience: {job_data['experience']}")
        if job_data.get("education"):
            parts.append(f"Education: {job_data['education']}")
        return " | ".join(parts)

    # ============================================================
    # Upsert a vector into Pinecone (insert or update)
    # vector_id: unique string identifier (e.g. "job-42")
    # text: the text to embed
    # metadata: additional data stored alongside the vector
    # ============================================================
    def upsert_vector(self, vector_id: str, text: str, metadata: dict = None) -> str:
        # Generate embedding from text
        embedding = self.generate_embedding(text)

        # Build the upsert payload
        vector = {
            "id": vector_id,
            "values": embedding,
            "metadata": metadata or {}
        }

        # Upsert into Pinecone index
        self.index.upsert(vectors=[vector])
        logger.info(f"Upserted vector '{vector_id}' to Pinecone")
        return vector_id

    # ============================================================
    # Update an existing vector with new text (re-generate embedding)
    # This is used for INCREMENTAL SYNC after job updates
    # ============================================================
    def update_vector(self, vector_id: str, new_text: str, metadata: dict = None) -> str:
        # In Pinecone, update = upsert with same ID (overwrites existing)
        return self.upsert_vector(vector_id, new_text, metadata)

    # ============================================================
    # Delete a vector by its ID
    # Called when a job is deleted to keep Pinecone in sync with SQLite
    # ============================================================
    def delete_vector(self, vector_id: str) -> bool:
        self.index.delete(ids=[vector_id])
        logger.info(f"Deleted vector '{vector_id}' from Pinecone")
        return True

    # ============================================================
    # Fetch a vector by ID to inspect its stored values and metadata
    # ============================================================
    def fetch_vector(self, vector_id: str) -> dict:
        result = self.index.fetch(ids=[vector_id])
        vectors = result.get("vectors", {})
        if vector_id in vectors:
            return vectors[vector_id]
        logger.warning(f"Vector '{vector_id}' not found in Pinecone")
        return {}

    # ============================================================
    # Query Pinecone for the top-K most similar vectors to input text
    # Used for semantic skill matching (candidate vs job)
    # ============================================================
    def query_similar(self, text: str, top_k: int = 10, filter_dict: dict = None) -> list:
        # Generate query embedding
        query_embedding = self.generate_embedding(text)

        # Run similarity query
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter=filter_dict
        )

        return results.get("matches", [])

    # ============================================================
    # Get index statistics (total vectors, dimension, etc.)
    # ============================================================
    def get_index_stats(self) -> dict:
        return self.index.describe_index_stats()


# ============================================================
# Module-level singleton instance
# Import this in other modules: from services.pinecone_service import pinecone_service
# ============================================================
pinecone_service = PineconeService()