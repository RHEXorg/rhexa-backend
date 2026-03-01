# app/services/database_service.py
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from typing import List, Dict, Any, Optional
import urllib.parse
from app.services.encryption import encryption_service
from app.models.database_connection import DatabaseConnection

class DatabaseService:
    @staticmethod
    def get_connection_url(db_conn: DatabaseConnection) -> str:
        """Constructs a SQLAlchemy connection URL from the DatabaseConnection model."""
        # Decrypt password
        password = encryption_service.decrypt(db_conn.password)
        # URL encode password for safety in connection string
        safe_password = urllib.parse.quote_plus(password)
        
        if db_conn.db_type == "postgresql":
            return f"postgresql://{db_conn.username}:{safe_password}@{db_conn.host}:{db_conn.port}/{db_conn.database_name}"
        elif db_conn.db_type == "mysql":
            return f"mysql+pymysql://{db_conn.username}:{safe_password}@{db_conn.host}:{db_conn.port}/{db_conn.database_name}"
        else:
            raise ValueError(f"Unsupported database type: {db_conn.db_type}")

    @staticmethod
    def test_connection(db_conn: DatabaseConnection) -> bool:
        """Tests if the connection to the database is successful."""
        try:
            url = DatabaseService.get_connection_url(db_conn)
            engine = create_engine(url, connect_args={"connect_timeout": 5})
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False

    @staticmethod
    def get_schema(db_conn: DatabaseConnection) -> List[Dict[str, Any]]:
        """Discovers the schema (tables and columns) of the database."""
        try:
            url = DatabaseService.get_connection_url(db_conn)
            engine = create_engine(url)
            inspector = inspect(engine)
            
            schema_info = []
            for table_name in inspector.get_table_names():
                columns = []
                for column in inspector.get_columns(table_name):
                    columns.append({
                        "name": column["name"],
                        "type": str(column["type"]),
                        "nullable": column.get("nullable", True)
                    })
                schema_info.append({
                    "table": table_name,
                    "columns": columns
                })
            return schema_info
        except Exception as e:
            print(f"Failed to get schema: {e}")
            return []

    @staticmethod
    def execute_query(db_conn: DatabaseConnection, query: str) -> List[Dict[str, Any]]:
        """Executes a SQL query and returns the results as a list of dictionaries."""
        # Security: In a real production app, we would use a read-only database user.
        # For now, we'll just check if the query starts with SELECT.
        clean_query = query.strip().upper()
        if not clean_query.startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed for security reasons.")
            
        try:
            url = DatabaseService.get_connection_url(db_conn)
            engine = create_engine(url)
            with engine.connect() as connection:
                result = connection.execute(text(query))
                # Convert results to list of dicts
                return [dict(row._mapping) for row in result]
        except Exception as e:
            print(f"Query execution failed: {e}")
            raise e

database_service = DatabaseService()
