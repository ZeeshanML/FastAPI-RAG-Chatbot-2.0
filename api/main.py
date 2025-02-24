from fastapi import FastAPI, UploadFile, HTTPException, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
import aiofiles
from pydantic_models import QueryInput, QueryResponse, DocumentInfo, DeleteFileRequest
from langchain_utils import get_rag_chain
from s3_utils import S3Client
from db_utils import insert_application_logs, get_chat_history, insert_document_record, get_all_documents, get_document_by_id, delete_document_record
from pinecone_utils import index_document_to_pinecone, delete_doc_from_pinecone
import os
import uuid
from logger_config import setup_logger
from mangum import Mangum
from datetime import datetime


# logging.basicConfig(filename="app.log", level=logging.INFO)

logger = setup_logger()

s3_client = S3Client()

app = FastAPI(
    title="FastAPI RAG Chatbot",
    description="A RAG-based chatbot API with document management",
    version="2.0",
    docs_url=None,
    redoc_url=None,
    root_path="/Prod" 
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
    expose_headers=["Content-Range", "Range"],
    max_age=600,
)

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="./openapi.json",
        title="FastAPI RAG Chatbot API Documentation",
        swagger_favicon_url="",
        swagger_ui_parameters={"defaultModelsExpandDepth": -1}
    )

@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_endpoint():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="FastAPI RAG Chatbot",
        version="2.0",
        description="A RAG-based chatbot API with document management",
        routes=app.routes,
        servers=[{"url": "/Prod"}] 
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

@app.get("/")
async def hello_world():
    return {"message": "Hello World!!"}


@app.post("/chat", response_model=QueryResponse)
async def chat(query_input: QueryInput):
    session_id = query_input.session_id or str(uuid.uuid4())
    logger.info(f"Session ID: {session_id}, User Query: {query_input.question}, Model: {query_input.model.value}")

    chat_history = await get_chat_history(session_id)
    rag_chain = await get_rag_chain(model=query_input.model.value)
    result = await rag_chain.ainvoke({
            "input": query_input.question,
            "chat_history": chat_history
        })
    answer = result["answer"]

    await insert_application_logs(session_id, query_input.question, answer, query_input.model.value)
    logger.info(f"Session ID: {session_id}, AI Response: {answer}")

    return QueryResponse(answer=answer, session_id=session_id, model=query_input.model)


@app.post("/upload-doc")
async def upload_and_index_document(file: UploadFile = File(...)):
    logger.info(f"Starting document upload for file: {file.filename}")
    allowed_extensions = [".pdf", ".docx", ".html"]
    file_extension = os.path.splitext(file.filename)[1].lower()

    if file_extension not in allowed_extensions:
        logger.warning(f"Unsupported file type attempted: {file_extension}")
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Allowed types are: {', '.join(allowed_extensions)}"
        )
    
    # Generate a unique filename to prevent collisions in S3
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    temp_file_path = f"/tmp/{unique_filename}"

    try:
        # Save uploaded file temporarily
        logger.info(f"Saving file temporarily to: {temp_file_path}")
        async with aiofiles.open(temp_file_path, "wb") as buffer:
            content = await file.read()
            await buffer.write(content)

        logger.info("Uploading file to S3")
        s3_url = await s3_client.upload_file(temp_file_path, unique_filename)

        logger.info("Inserting document record to database")
        file_id = await insert_document_record(file.filename, s3_url)

        if not file_id:
            # If database insert fails, delete from S3
            logger.error("Failed to insert document record")
            await s3_client.delete_file(unique_filename)
            raise HTTPException(status_code=500, detail="Failed to store document metadata")
        
        logger.info(f"Indexing document to Pinecone with file_id: {file_id}")
        pinecone_indexing_success = await index_document_to_pinecone(temp_file_path, file_id)

        if pinecone_indexing_success:
            logger.info(f"Successfully processed document: {file.filename}")
            return {
                "message": f"File {file.filename} has been successfully uploaded and indexed.",
                "file_id": file_id,
                "s3_url": s3_url
            }
        else:
            # If indexing fails, clean up S3 and database
            logger.error(f"Failed to index document: {file.filename}")
            await s3_client.delete_file(unique_filename)
            await delete_document_record(file_id)
            raise HTTPException(status_code=500, detail="Failed to index document")
    except Exception as e:
        logger.error(f"Error uploading and indexing document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temporary file: {str(e)}")


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
        logger.error(f"Error in delete_document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

        
handler = Mangum(app)