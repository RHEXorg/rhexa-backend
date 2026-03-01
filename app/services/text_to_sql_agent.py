# app/services/text_to_sql_agent.py
"""
Text-to-SQL Agent Service.
Uses LangChain SQL Agent to convert natural language queries into SQL,
execute them against a target database, and return human-readable answers.
"""
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from app.core.config import settings
from app.models.database_connection import DatabaseConnection
from app.services.database_service import database_service

class TextToSQLAgent:
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        from app.core.ai_models import get_llm
        self.llm = get_llm()

    def ask_database(self, db_conn: DatabaseConnection, question: str) -> dict:
        """
        Connects to the database and uses an AI agent to answer the question.
        Returns both the answer and the success status.
        """
        if not self.llm:
            return {
                "answer": "OpenAI API Key is not configured in the backend.",
                "success": False
            }

        try:
            # Get the connection URL (decrypted)
            url = database_service.get_connection_url(db_conn)
            
            # Create LangChain SQL database wrapper
            db = SQLDatabase.from_uri(url)
            
            # Create the agent executor
            # 'openai-functions' type is generally more reliable for tool use
            agent_executor = create_sql_agent(
                self.llm, 
                db=db, 
                agent_type="openai-functions", 
                verbose=True,
                handle_parsing_errors=True,
                top_k=50  # Allow larger analysis chunks instead of default 10
            )
            
            # Invoke the agent
            response = agent_executor.invoke({"input": question})
            
            return {
                "answer": response.get("output", "I processed the query but couldn't formulate a text answer."),
                "success": True
            }
            
        except Exception as e:
            print(f"Text-to-SQL error: {e}")
            return {
                "answer": f"I encountered an error while querying the database: {str(e)}",
                "success": False
            }

# Instantiate the singleton agent
sql_agent = TextToSQLAgent()
