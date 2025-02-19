from fastapi import FastAPI, UploadFile, HTTPException, File
import aiofiles
import asyncio
from pydantic_models import QueryInput, QueryResponse, DocumentInfo, DeleteFileRequest
from langchain_utils import get_rag_chain
from s3_utils import S3Client
from db_utils import insert_application_logs, get_chat_history, insert_document_record, get_all_documents, get_document_by_id, delete_document_record
from pinecone_utils import index_document_to_pinecone, delete_doc_from_pinecone
import os
import uuid
import logging
import shutil

logging.basicConfig(filename="app.log", level=logging.INFO)

s3_client = S3Client()

app = FastAPI()

@app.get("/")
async def hello_world():
    return {"message": "Hello World!!"}


@app.post("/chat", response_model=QueryResponse)
async def chat(query_input: QueryInput):
    session_id = query_input.session_id or str(uuid.uuid4())
    logging.info(f"Session ID: {session_id}, User Query: {query_input.question}, Model: {query_input.model.value}")

    chat_history = await get_chat_history(session_id)
    rag_chain = await get_rag_chain(model=query_input.model.value)
    result = await rag_chain.ainvoke({
            "input": query_input.question,
            "chat_history": chat_history
        })
    answer = result["answer"]

    await insert_application_logs(session_id, query_input.question, answer, query_input.model.value)
    logging.info(f"Session ID: {session_id}, AI Response: {answer}")

    return QueryResponse(answer=answer, session_id=session_id, model=query_input.model)


@app.post("/upload-doc")
async def upload_and_index_document(file: UploadFile = File(...)):
    allowed_extensions = [".pdf", ".docx", ".html"]
    file_extension = os.path.splitext(file.filename)[1].lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed types are: {', '.join(allowed_extensions)}")
    
    # Generate a unique filename to prevent collisions in S3
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    temp_file_path = f"temp_{unique_filename}"

    try:
        # Save uploaded file temporarily
        async with aiofiles.open(temp_file_path, "wb") as buffer:
            content = await file.read()
            await buffer.write(content)

        s3_url = await s3_client.upload_file(temp_file_path, unique_filename)
        file_id = await insert_document_record(file.filename, s3_url)

        if not file_id:
            # If database insert fails, delete from S3
            await s3_client.delete_file(unique_filename)
            raise HTTPException(status_code=500, detail="Failed to store document metadata")
        
        pinecone_indexing_success = await index_document_to_pinecone(temp_file_path, file_id)

        if pinecone_indexing_success:
            return {
                "message": f"File {file.filename} has been successfully uploaded and indexed.",
                "file_id": file_id,
                "s3_url": s3_url
            }
        else:
            # If indexing fails, clean up S3 and database
            await s3_client.delete_file(unique_filename)
            await delete_document_record(file_id)
            raise HTTPException(status_code=500, detail="Failed to index document")
    except Exception as e:
        logging.error(f"Error uploading and indexing document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@app.get("/list-docs", response_model=list[DocumentInfo])
async def list_documents():
    return await get_all_documents()


@app.post("/delete-doc")
async def delete_document(request: DeleteFileRequest):
    try:
        # Get document info from Supabase first
        document = await get_document_by_id(request.file_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Extract S3 key from URL
        s3_key = document["s3_url"].split("/")[-1]

        # Delete form Pinecone
        pinecone_delete_success = await delete_doc_from_pinecone(request.file_id)
        if not pinecone_delete_success:
            raise HTTPException(status_code=500, detail="Failed to delete document vectors from Pinecone")
        
        # Delete from S3
        s3_delete_success = await s3_client.delete_file(s3_key)
        if not s3_delete_success:
            raise HTTPException(status_code=500, detail="Failed to delete document from S3")
        
        # Delete from Supabase
        db_delete_success = await delete_document_record(request.file_id)
        if not db_delete_success:
            raise HTTPException(status_code=500, detail="Failed to delete document record from database")
        
        return {"message": f"Successfully deleted document with file_id {request.file_id}"}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in delete_document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

        