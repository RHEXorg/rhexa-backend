# app/services/rag_service.py
"""
RAG Service Orchestrator.

Handles the high-level logic for:
1. Processing document text (Chunking)
2. Indexing into Vector DB
3. Searching/Retrieval
"""

import logging
from sqlalchemy.orm import Session
from app.models.document import Document
from app.rag.chunking import split_text
from app.rag.vector_store import vector_store_manager

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings
from app.schemas.chat import Citation

import re
import logging
import warnings

# Suppress specific warnings
warnings.filterwarnings('ignore', message='.*You are sending unauthenticated requests.*')
warnings.filterwarnings('ignore', message='.*UNEXPECTED.*')

logger = logging.getLogger(__name__)


def clean_ai_response(answer: str) -> str:
    """
    Clean up AI response to remove markdown formatting and make it more professional.
    Removes: **bold**, *italic*, numbered lists, bullet points
    Keeps: Simple headings, flowing prose
    """
    # Remove **bold** markers
    answer = re.sub(r'\*\*(.+?)\*\*', r'\1', answer)
    
    # Remove *italic* markers  
    answer = re.sub(r'\*(.+?)\*', r'\1', answer)
    
    # Remove numbered lists like "1. Item" or "1) Item" - convert to flowing text
    answer = re.sub(r'^\s*\d+[\.\)]\s+', '', answer, flags=re.MULTILINE)
    
    # Remove bullet points like "- Item" or "* Item"
    answer = re.sub(r'^\s*[-*]\s+', '', answer, flags=re.MULTILINE)
    
    # Clean up multiple empty lines
    answer = re.sub(r'\n{3,}', '\n\n', answer)
    
    # Clean up any remaining **
    answer = answer.replace('**', '')
    
    # Clean up headings - keep them but make them cleaner
    # Remove colons from headings if they're followed by newlines with lists
    answer = re.sub(r':\s*\n+', ': ', answer)
    
    return answer.strip()

def generate_answer(
    organization_id: int,
    query: str,
    conversation_history: list = None,
    limit: int = 15,
    document_ids: list = None,
    database_ids: list = None
) -> dict:
    """
    RAG Generation Flow:
    1. Search vector DB for context
    2. Build conversation-aware prompt
    3. Generate answer via LLM with full chat history
    """
    if conversation_history is None:
        conversation_history = []

    # 1. Retrieve Context
    logger.info(f"[generate_answer] Org={organization_id} | doc_ids={document_ids} | db_ids={database_ids}")
    results = search_similar(organization_id, query, limit, document_ids)
    logger.info(f"[generate_answer] search_similar returned {len(results)} results")
    
    # 2. Format Context & Citations
    context_text = ""
    citations = []
    
    for i, (doc, score) in enumerate(results):
        snippet = doc.page_content.replace("\n", " ")
        context_text += f"Source {i+1}:\n{snippet}\n\n"
        
        citations.append(Citation(
            document_id=doc.metadata.get("document_id", 0),
            filename=doc.metadata.get("filename", "unknown"),
            text_snippet=snippet[:200] + "...",
            score=float(score)
        ))
    from app.db.session import SessionLocal
    from app.models.database_connection import DatabaseConnection
    from app.services.text_to_sql_agent import sql_agent
    
    # 2. Extract Database Context (if any databases selected/connected)
    db_context_text = ""
    if database_ids:
        try:
            db = SessionLocal()
            for db_id in database_ids:
                db_conn = db.query(DatabaseConnection).filter(DatabaseConnection.id == db_id, DatabaseConnection.organization_id == organization_id).first()
                if db_conn:
                    sql_res = sql_agent.ask_database(db_conn, query)
                    if sql_res.get("success"):
                        db_context_text += f"\nDatabase Info ({db_conn.name}): {sql_res['answer']}\n"
                        citations.append(Citation(
                            document_id=db_conn.id,
                            filename=f"DB: {db_conn.name}",
                            text_snippet=sql_res['answer'][:200],
                            score=1.0
                        ))
        except Exception as e:
            logger.error(f"Error querying databases in generate_answer: {e}")
        finally:
            db.close()
            
    if db_context_text:
        context_text += f"\n\n--- DATABASE RESULTS ---\n{db_context_text}\n"
    
    logger.info(f"[generate_answer] context_text length: {len(context_text)} chars")
    
    if not context_text.strip():
        logger.warning(f"[generate_answer] No context found for org {organization_id}. Returning fallback.")
        return {
            "answer": "I could not find the answer to your question in the uploaded documents or databases. Please try asking differently.",
            "citations": []
        }
    
    logger.info(f"[generate_answer] Sending {len(results)} chunks to LLM for synthesis.")

    # 3. LLM Generation with conversation context
    system_prompt = """You are RheXa, a professional AI business partner and strategic advisor.
    Your mission is to provide clear, accurate, and insightful guidance based ONLY on the provided data.
    
    RESPONSE STYLE - VERY IMPORTANT:
    - NEVER use **stars** or bold formatting for anything.
    - NEVER use bullet points with dashes or asterisks.
    - Use simple headings like "Key Insights:" or "What This Means:"
    - Write in flowing paragraphs, not lists. Combine related points into sentences.
    - Use just 1-2 emojis per response when they add value (like 📊 for data, 💡 for ideas, ✅ for confirmations).
    - Easy English: clear and simple, but professional.
    
    TONE - VERY IMPORTANT:
    - Speak as a trusted business partner. Use "we," "our," and "let's" to show we're in this together.
    - Be warm, friendly, and approachable while staying professional.
    - Avoid robotic phrases like "Based on the provided data" or "According to the documents."
    - Just deliver insights naturally as if you're explaining to a colleague.
    
    WHAT TO DO:
    - Focus on the most important insights from the data.
    - Explain what the numbers mean for our business.
    - If something is unclear or missing, politely say so.
    - Never mention filenames, IDs, or internal references.
    """

    # Build the message list for the LLM
    from app.core.ai_models import get_llm
    llm = get_llm()
    
    if llm:
        from langchain_core.messages import AIMessage
        
        llm_messages = [SystemMessage(content=system_prompt)]
        
        # Add conversation history (excluding the current user message which is the last one)
        # This gives the LLM full context of the conversation so far
        for msg in conversation_history[:-1]:  # exclude last because we add it with context below
            if msg["role"] == "user":
                llm_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                llm_messages.append(AIMessage(content=msg["content"]))
        
        # Add the current question with the retrieved document context
        user_prompt = f"""Context Sources:
{context_text}

Question: {query}"""
        llm_messages.append(HumanMessage(content=user_prompt))
        
        response = llm.invoke(llm_messages)
        answer = response.content
        # Clean up the response to remove markdown formatting
        answer = clean_ai_response(answer)
    else:
        # No AI model configured yet
        answer = "Server busy, sorry. Please try again."

    return {
        "answer": answer,
        "citations": citations
    }


def index_document(
    db: Session,
    document: Document,
    extracted_text: str
):
    """
    Process a document and index it into the vector store.
    """
    from app.db.session import SessionLocal
    
    # We create a new local session for background work to ensure the DB connection stays open
    bg_db = SessionLocal()
    try:
        # Refresh the document object in the new session to avoid detachment
        bg_doc = bg_db.query(Document).filter(Document.id == document.id).first()
        if not bg_doc:
            logger.error(f"Background task could not find document {document.id}")
            return

        logger.info(f"Indexing document {bg_doc.id} for org {bg_doc.organization_id}...")
        
        # 1. Chunking
        metadata = {
            "document_id": bg_doc.id,
            "filename": bg_doc.filename,
            "source": bg_doc.file_path,
            "organization_id": bg_doc.organization_id
        }
        
        chunks = split_text(extracted_text, metadata)
        logger.info(f"Created {len(chunks)} chunks for document {bg_doc.id}")
        
        if not chunks:
            logger.warning("No text extracted to chunk.")
            return

        # 2. Indexing
        logger.info(f"Indexing {len(chunks)} chunks to FAISS for org {bg_doc.organization_id}...")
        vector_store_manager.add_documents(bg_doc.organization_id, chunks)
        logger.info(f"Successfully indexed document {bg_doc.id} (Org: {bg_doc.organization_id}) to vector store.")
        
    except Exception as e:
        logger.error(f"Background Indexing failed for document {document.id}: {e}")
    finally:
        bg_db.close()


def search_similar(
    organization_id: int,
    query: str,
    limit: int = 15,
    document_ids: list = None
):
    """
    Search for relevant context using MMR (Maximal Marginal Relevance).
    This ensures we don't just get 15 identical paragraphs, but a diverse set
    of context chunks crossing different topics related to the query.
    """
    # Use the new MMR search implemented in vector_store.py
    results = vector_store_manager.search_mmr(
        organization_id=organization_id,
        query=query,
        k=limit,
        fetch_k=limit * 5,
        document_ids=document_ids
    )
    
    return results
