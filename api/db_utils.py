from supabase import create_client, Client
from datetime import datetime, timezone
from typing import Dict, List
import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

async def get_all_documents() -> List[Dict]:
    try:
        logger.info("Fetching all documents from database")
        response = supabase.table("document_store").select("*")\
            .order("upload_timestamp", desc=True)\
            .execute()
        logger.info(f"Successfully retrieved {len(response.data)} documents")
        return response.data
    except Exception as e:
        logger.error(f"Error fetching documents: {str(e)}", exc_info=True)
        return []
    

async def insert_application_logs(session_id: str, user_query: str, gpt_response: str, model: str):
    try:
        logger.info(f"Inserting application log for session: {session_id}")
        supabase.table("application_logs").insert({
            "session_id": session_id,
            "user_query": user_query,
            "gpt_response": gpt_response,
            "model": model,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        logger.info("Successfully inserted application log")
    except Exception as e:
        logger.error(f"Error inserting application logs: {str(e)}", exc_info=True)


async def get_chat_history(session_id: str) -> List[Dict]:
    try:
        response = supabase.table("application_logs")\
            .select("user_query, gpt_response")\
            .eq("session_id", session_id)\
            .order("created_at")\
            .execute()
        
        messages = []
        for row in response.data:
            messages.extend([
                {"role": "human", "content": row['user_query']},
                {"role": "ai", "content": row['gpt_response']}
            ])
        return messages
    except Exception as e:
        print(f"Error fetching chat history: {e}")
        return []
    

async def insert_document_record(filename: str, s3_url: str) -> int:
    try:
        response = supabase.table("document_store").insert({
            "filename": filename,
            "s3_url": s3_url,
            "upload_timestamp": datetime.now(timezone.utc).isoformat()
        }).execute()
        return response.data[0]['id']
    except Exception as e:
        print(f"Error inserting document record: {e}")
        return None
    

async def get_document_by_id(file_id: int) -> Dict:
    try:
        response = supabase.table("document_store")\
            .select("*")\
            .eq("id", file_id)\
            .execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error fetching document by ID: {e}")
        return None
    

async def delete_document_record(file_id: int) -> bool:
    try:
        supabase.table("document_store")\
            .delete()\
            .eq("id", file_id)\
            .execute()
        return True
    except Exception as e:
        print(f"Error deleting document record: {e}")
        return False