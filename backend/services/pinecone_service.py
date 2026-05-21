# ============================================================
# services/pinecone_service.py
# Reusable Pinecone utility service.
# Handles: index creation, upsert, update, delete, fetch vectors.
# Uses sentence-transformers (all-MiniLM-L6-v2) for embedding generation.
#
# IMPORTANT RENDER OPTIMIZATION:
# --------------------------------
# Original implementation loaded SentenceTransformer immediately
# during application startup:
#
#     self.embedding_model = SentenceTransformer(...)
#
# This caused Render free tier deployments to crash because:
# - sentence-transformers loads PyTorch into memory
# - model initialization consumes large RAM
# - Render free tier has only 512MB memory
#
# SOLUTION:
# --------------------------------
# Implement LAZY LOADING:
# - model loads only when first embedding is requested
# - startup memory usage stays low
# - deployment succeeds
# - functionality remains identical
#
# No functionality removed.
# Only startup behavior optimized.
# ============================================================

from pinecone import Pinecone, ServerlessSpec

# ============================================================
# ORIGINAL IMPORT (COMMENTED FOR RENDER OPTIMIZATION)
# ------------------------------------------------------------
# Importing SentenceTransformer globally can increase startup
# memory usage on Render free tier.
#
# from sentence_transformers import SentenceTransformer
# ============================================================

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

        # ====================================================
        # Load Pinecone configuration from environment variables
        # ====================================================
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.environment = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "job-embeddings")

        self.embedding_model_name = os.getenv(
            "EMBEDDING_MODEL",
            "all-MiniLM-L6-v2"
        )

        # ====================================================
        # Initialize Pinecone client only — lightweight
        # ====================================================
        self.pc = Pinecone(api_key=self.api_key)

        # ====================================================
        # ORIGINAL IMPLEMENTATION (COMMENTED)
        # ----------------------------------------------------
        # This eagerly loaded the embedding model during
        # application startup and caused Render OOM crashes.
        #
        # logger.info(
        #     f"Loading embedding model:
        #     {self.embedding_model_name}"
        # )
        #
        # self.embedding_model = SentenceTransformer(
        #     self.embedding_model_name
        # )
        # ====================================================

        # ====================================================
        # NEW IMPLEMENTATION (LAZY LOADING)
        # ----------------------------------------------------
        # Model is initialized ONLY when first needed.
        # This dramatically reduces startup RAM usage.
        # ====================================================
        self._embedding_model = None

        # ====================================================
        # Connect to (or create) Pinecone index
        # ====================================================
        self.index = self._get_or_create_index()

    # ============================================================
    # Lazy-load embedding model only when required
    #
    # WHY THIS EXISTS:
    # ------------------------------------------------------------
    # Render free tier crashes if SentenceTransformer loads
    # during startup.
    #
    # This method delays model loading until:
    # - generate_embedding()
    # - query_similar()
    # - upsert_vector()
    #
    # are actually called.
    #
    # BENEFITS:
    # ------------------------------------------------------------
    #  Lower startup memory
    #  Successful Render deployment
    #  Same functionality
    #  Same embedding quality
    # ============================================================
    def _get_embedding_model(self):

        # ====================================================
        # Load model only once
        # ====================================================
        if self._embedding_model is None:

            logger.info(
                f"Lazy-loading embedding model: "
                f"{self.embedding_model_name}"
            )

            # =================================================
            # LOCAL IMPORT
            # -------------------------------------------------
            # Delays importing sentence-transformers until
            # actually needed.
            # =================================================
            from sentence_transformers import SentenceTransformer

            # =================================================
            # Initialize embedding model
            # =================================================
            self._embedding_model = SentenceTransformer(
                self.embedding_model_name
            )

            logger.info("Embedding model loaded successfully")

        return self._embedding_model

    # ============================================================
    # Create Pinecone index if it doesn't already exist
    # Uses ServerlessSpec for cloud-based serverless deployment
    # ============================================================
    def _get_or_create_index(self):

        existing_indexes = [
            idx.name for idx in self.pc.list_indexes()
        ]

        if self.index_name not in existing_indexes:

            logger.info(
                f"Creating Pinecone index: {self.index_name}"
            )

            self.pc.create_index(
                name=self.index_name,

                # ====================================================
                # Matches all-MiniLM-L6-v2 output dimension
                # ====================================================
                dimension=384,

                # ====================================================
                # Cosine similarity for semantic matching
                # ====================================================
                metric="cosine",

                spec=ServerlessSpec(
                    cloud="aws",
                    region=self.environment
                )
            )

            logger.info(
                f"Index '{self.index_name}' created successfully"
            )

        else:

            logger.info(
                f"Connected to existing Pinecone index: "
                f"{self.index_name}"
            )

        return self.pc.Index(self.index_name)

    # ============================================================
    # Generate embedding vector from text using
    # sentence-transformers
    #
    # Returns a 384-dimensional float list
    # ============================================================
    def generate_embedding(self, text: str) -> list[float]:

        # ====================================================
        # ORIGINAL IMPLEMENTATION (COMMENTED)
        # ----------------------------------------------------
        # embedding = self.embedding_model.encode(
        #     text,
        #     normalize_embeddings=True
        # )
        # ====================================================

        # ====================================================
        # NEW IMPLEMENTATION
        # ----------------------------------------------------
        # Ensure model is lazy-loaded only when needed.
        # ====================================================
        model = self._get_embedding_model()

        # ====================================================
        # Encode text and normalize embeddings
        # ====================================================
        embedding = model.encode(
            text,
            normalize_embeddings=True
        )

        return embedding.tolist()

    # ============================================================
    # Build a text representation of the job for embedding
    # Concatenates key fields to create a rich semantic
    # representation
    # ============================================================
    def build_job_embedding_text(self, job_data: dict) -> str:

        parts = []

        if job_data.get("title"):
            parts.append(
                f"Job Title: {job_data['title']}"
            )

        if job_data.get("department"):
            parts.append(
                f"Department: {job_data['department']}"
            )

        if job_data.get("description"):
            parts.append(
                f"Description: {job_data['description']}"
            )

        if job_data.get("required_skills"):
            parts.append(
                f"Required Skills: "
                f"{job_data['required_skills']}"
            )

        if job_data.get("experience"):
            parts.append(
                f"Experience: {job_data['experience']}"
            )

        if job_data.get("education"):
            parts.append(
                f"Education: {job_data['education']}"
            )

        return " | ".join(parts)

    # ============================================================
    # Upsert a vector into Pinecone (insert or update)
    #
    # vector_id:
    # unique string identifier (e.g. "job-42")
    #
    # text:
    # the text to embed
    #
    # metadata:
    # additional data stored alongside the vector
    # ============================================================
    def upsert_vector(
        self,
        vector_id: str,
        text: str,
        metadata: dict = None
    ) -> str:

        # ====================================================
        # Generate embedding from text
        # ====================================================
        embedding = self.generate_embedding(text)

        # ====================================================
        # Build the upsert payload
        # ====================================================
        vector = {
            "id": vector_id,
            "values": embedding,
            "metadata": metadata or {}
        }

        # ====================================================
        # Upsert into Pinecone index
        # ====================================================
        self.index.upsert(vectors=[vector])

        logger.info(
            f"Upserted vector '{vector_id}' to Pinecone"
        )

        return vector_id

    # ============================================================
    # Update an existing vector with new text
    #
    # Used for incremental sync after job updates
    # ============================================================
    def update_vector(
        self,
        vector_id: str,
        new_text: str,
        metadata: dict = None
    ) -> str:

        # ====================================================
        # In Pinecone:
        # update = upsert with same ID
        # ====================================================
        return self.upsert_vector(
            vector_id,
            new_text,
            metadata
        )

    # ============================================================
    # Delete vector by ID
    #
    # Called when a job is deleted to keep Pinecone
    # synchronized with SQLite
    # ============================================================
    def delete_vector(self, vector_id: str) -> bool:

        self.index.delete(ids=[vector_id])

        logger.info(
            f"Deleted vector '{vector_id}' from Pinecone"
        )

        return True

    # ============================================================
    # Fetch vector by ID
    #
    # Used to inspect stored vector values and metadata
    # ============================================================
    def fetch_vector(self, vector_id: str) -> dict:

        result = self.index.fetch(ids=[vector_id])

        vectors = result.get("vectors", {})

        if vector_id in vectors:
            return vectors[vector_id]

        logger.warning(
            f"Vector '{vector_id}' not found in Pinecone"
        )

        return {}

    # ============================================================
    # Query Pinecone for top-K most similar vectors
    #
    # Used for semantic skill matching
    # candidate ↔ jobs
    # ============================================================
    def query_similar(
        self,
        text: str,
        top_k: int = 10,
        filter_dict: dict = None
    ) -> list:

        # ====================================================
        # Generate query embedding
        # ====================================================
        query_embedding = self.generate_embedding(text)

        # ====================================================
        # Run similarity query
        # ====================================================
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter=filter_dict
        )

        return results.get("matches", [])

    # ============================================================
    # Get index statistics
    # ============================================================
    def get_index_stats(self) -> dict:
        return self.index.describe_index_stats()


# ============================================================
# ORIGINAL SINGLETON IMPLEMENTATION (COMMENTED)
# ------------------------------------------------------------
# This initialized PineconeService during startup.
#
# Since PineconeService previously loaded
# SentenceTransformer immediately, Render crashed.
#
# pinecone_service = PineconeService()
# ============================================================


# ============================================================
# NEW LAZY SINGLETON IMPLEMENTATION
# ------------------------------------------------------------
# Service is initialized only when first needed.
#
# BENEFITS:
# ------------------------------------------------------------
#  Lower startup RAM
#  Faster deployment
#  Prevent Render crashes
#  Same functionality
# ============================================================
pinecone_service = None


def get_pinecone_service():

    global pinecone_service

    if pinecone_service is None:

        logger.info(
            "Initializing PineconeService lazily..."
        )

        pinecone_service = PineconeService()

    return pinecone_service