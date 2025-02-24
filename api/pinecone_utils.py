from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, UnstructuredHTMLLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from pinecone import Pinecone, ServerlessSpec
from typing import List
import asyncio
import os
from dotenv import load_dotenv
import time
import logging

logger = logging.getLogger(__name__)

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = "fastapi-rag-chatbot"
BATCH_SIZE = 100

pc = Pinecone(api_key=PINECONE_API_KEY)

existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]

if INDEX_NAME not in existing_indexes:
    pc.create_index(name = INDEX_NAME,
                    dimension = 1536,
                    metric = "cosine",
                    spec = ServerlessSpec(cloud = "aws", region = "us-east-1"))
    while not pc.describe_index(INDEX_NAME).status["ready"]:
        time.sleep(1)

index = pc.Index(INDEX_NAME)

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

vectorstore = PineconeVectorStore(index=index, embedding=embeddings)

async def load_and_split_document(file_path: str) -> List[Document]:
    try:
        logger.info(f"Loading document: {file_path}")
        if file_path.endswith(".pdf"):
            loader = PyPDFLoader(file_path)
        elif file_path.endswith(".docx"):
            loader = Docx2txtLoader(file_path)
        elif file_path.endswith(".html"):
            loader = UnstructuredHTMLLoader(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")
        
        # Use synchronous operations
        documents = loader.load()
        split_docs = text_splitter.split_documents(documents)
        logger.info(f"Document split into {len(split_docs)} chunks")
        return split_docs
    except Exception as e:
        logger.error(f"Error loading document: {str(e)}", exc_info=True)
        raise

async def index_document_to_pinecone(file_path: str, file_id: int) -> bool:
    try:
        logger.info(f"Starting document indexing for file_id: {file_id}")
        documents = await load_and_split_document(file_path)
        logger.info(f"Split document into {len(documents)} chunks")
        
        # Process in batches
        for i in range(0, len(documents), BATCH_SIZE):
            batch = documents[i:i + BATCH_SIZE]
            texts = [doc.page_content for doc in batch]
            # Add text content to metadata
            metadatas = [{
                "file_id": file_id,
                "text": doc.page_content,  # Add the text content
                "source": os.path.basename(file_path),  # Add source filename
                **doc.metadata
            } for doc in batch]
            
            # Generate embeddings
            logger.info(f"Generating embeddings for batch {i//BATCH_SIZE + 1}")
            embs = embeddings.embed_documents(texts)

            # Prepare vectors for upsert
            vectors = []
            for j, (text, metadata, emb) in enumerate(zip(texts, metadatas, embs)):
                vectors.append({
                    'id': f"{file_id}-{i+j}",
                    'values': emb,
                    'metadata': metadata
                })
            
            # Upsert to Pinecone
            logger.info(f"Upserting batch {i//BATCH_SIZE + 1} to Pinecone")
            index.upsert(vectors=vectors)
            
        logger.info(f"Successfully indexed document {file_id}")
        return True
    except Exception as e:
        logger.error(f"Indexing error for file {file_id}: {str(e)}", exc_info=True)
        return False
    
async def delete_doc_from_pinecone(file_id: int) -> bool:
    try:
        # First, get the vector IDs associated with the file_id
        logger.info(f"Deleting document with file_id: {file_id}")
        # Use synchronous operations
        results = index.query(
            vector=[0] * 1536,
            top_k=10000,
            filter={"file_id": file_id},
            include_metadata=True
        )
        
        # Extract vector IDs to delete
        vector_ids = [match.id for match in results.matches]
        
        if vector_ids:
            # Delete the vectors by their IDs
            index.delete(ids=vector_ids)
            logger.info(f"Successfully deleted {len(vector_ids)} document chunks with file_id {file_id}")
            return True
        else:
            logger.warning(f"No documents found with file_id {file_id}")
            return False
        
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}", exc_info=True)
        return False