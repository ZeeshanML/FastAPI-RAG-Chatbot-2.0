from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
import os
from pinecone_utils import vectorstore
from dotenv import load_dotenv
import asyncio
import logging

logger = logging.getLogger(__name__)

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")

retriever = vectorstore.as_retriever(search_kwargs = {"k": 2})
output_parser = StrOutputParser()

contextualize_q_system_prompt = (
    "Given a chat history and the latest user question "
    "which might reference context in the chat history, "
    "formulate a standalone question which can be understood "
    "without the chat history. Do NOT answer the question, "
    "just reformulate it if needed and otherwise return it as is."
)

contextualize_q_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}")
    ]
)

qa_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful AI assistant. Use the following context to answer the user's question."),
        ("system", "Context: {context}"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}")
    ]
)

async def get_rag_chain(model = "gpt-4o-mini"):
    """Create and return an async RAG chain"""
    try:
        logger.info(f"Initializing RAG chain with model: {model}")
        llm = ChatOpenAI(
            api_key=openai_api_key, 
            model=model,
        )
        
        logger.info("Creating history-aware retriever")
        history_aware_retriever = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: create_history_aware_retriever(llm, retriever, contextualize_q_prompt)
        )

        logger.info("Creating QA chain")
        qa_chain = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: create_stuff_documents_chain(llm, qa_prompt)
        )

        logger.info("Creating final RAG chain")
        rag_chain = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: create_retrieval_chain(history_aware_retriever, qa_chain)
        )
        
        logger.info("Successfully created RAG chain")
        return rag_chain
    except Exception as e:
        logger.error(f"Error creating RAG chain: {str(e)}", exc_info=True)
        raise
