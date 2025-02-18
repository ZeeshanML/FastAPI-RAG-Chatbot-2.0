from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, UnstructuredHTMLLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from pinecone import Pinecone, ServerlessSpec
from typing import List
import aiofiles
import asyncio
import os
from dotenv import load_dotenv
import time
import uuid

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = "fastapi-rag-chatbot"

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
    if file_path.endswith(".pdf"):
        loader = PyPDFLoader(file_path)
    elif file_path.endswith(".docx"):
        loader = Docx2txtLoader(file_path)
    elif file_path.endswith(".html"):
        loader = UnstructuredHTMLLoader(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_path}")
    
    documents = await asyncio.get_event_loop().run_in_executor(None, loader.load)

    return await asyncio.get_event_loop().run_in_executor(None, text_splitter.split_documents, documents)

async def index_document_to_pinecone(file_path: str, file_id: int) -> bool:
    try:
        splits = await load_and_split_document(file_path)
        for split in splits:
            split.metadata["file_id"] = file_id

        await asyncio.get_event_loop().run_in_executor(None, vectorstore.add_documents, splits)
        return True
    except Exception as e:
        print(f"Error indexing document: {e}")
        return False
    
async def delete_doc_from_pinecone(file_id: int) -> bool:
    try:
        # First, get the vector IDs associated with the file_id
        results = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: index.query(
                vector=[0] * 1536,  # We use a dummy vector (all zeros) since we only care about the metadata filter
                top_k=10000,
                filter={"file_id": file_id},
                include_metadata=True
            )
        )
        
        # Extract vector IDs to delete
        vector_ids = [match.id for match in results.matches]
        
        if vector_ids:
            # Delete the vectors by their IDs
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: index.delete(ids=vector_ids)
            )
            print(f"Deleted {len(vector_ids)} document chunks with file_id {file_id}")
            return True
        else:
            print(f"No documents found with file_id {file_id}")
            return False
        
    except Exception as e:
        print(f"Error deleting document with file_id {file_id} from Pinecone: {str(e)}")
        return False