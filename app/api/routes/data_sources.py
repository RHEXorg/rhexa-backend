# app/api/routes/data_sources.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any
from app.models.database_connection import DatabaseConnection
from app.models.user import User
from app.api.deps import get_db, get_current_active_user
from app.services.encryption import encryption_service
from app.services.database_service import database_service
from app.services.text_to_sql_agent import sql_agent
from app.services.billing_service import check_limit
from pydantic import BaseModel

router = APIRouter(prefix="/data-sources", tags=["Data Sources"])

class DatabaseQuestion(BaseModel):
    connection_id: int
    question: str

class DatabaseConnectionCreate(BaseModel):
    name: str
    db_type: str
    host: str
    port: int
    username: str
    password: str
    database_name: str

class DatabaseConnectionRead(BaseModel):
    id: int
    name: str
    db_type: str
    host: str
    port: int
    username: str
    database_name: str
    
    class Config:
        from_attributes = True

@router.post("/database", response_model=DatabaseConnectionRead)
def create_database_connection(
    obj_in: DatabaseConnectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add a new database connection."""
    # Check if organization exists (simple check via user)
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization")
        
    # Check subscription limits
    check_limit(db, current_user.organization_id, "databases")
        
    # Encrypt password
    encrypted_password = encryption_service.encrypt(obj_in.password)
    
    db_obj = DatabaseConnection(
        name=obj_in.name,
        db_type=obj_in.db_type,
        host=obj_in.host,
        port=obj_in.port,
        username=obj_in.username,
        password=encrypted_password,
        database_name=obj_in.database_name,
        organization_id=current_user.organization_id
    )
    
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

@router.get("/database", response_model=List[DatabaseConnectionRead])
def list_database_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all database connections for the organization."""
    return db.query(DatabaseConnection).filter(
        DatabaseConnection.organization_id == current_user.organization_id
    ).all()

@router.post("/database/test")
def test_db_connection(
    obj_in: DatabaseConnectionCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Test connection credentials without saving."""
    temp_conn = DatabaseConnection(
        db_type=obj_in.db_type,
        host=obj_in.host,
        port=obj_in.port,
        username=obj_in.username,
        password=encryption_service.encrypt(obj_in.password),
        database_name=obj_in.database_name
    )
    
    if database_service.test_connection(temp_conn):
        return {"success": True, "message": "Connection successful"}
    else:
        raise HTTPException(status_code=400, detail="Connection failed")

@router.get("/database/{id}/schema")
def get_db_schema(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get the schema information for a database connection."""
    db_conn = db.query(DatabaseConnection).filter(
        DatabaseConnection.id == id,
        DatabaseConnection.organization_id == current_user.organization_id
    ).first()
    
    if not db_conn:
        raise HTTPException(status_code=404, detail="Database connection not found")
        
    schema = database_service.get_schema(db_conn)
    return {"schema": schema}

@router.delete("/database/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_database_connection(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a database connection."""
    db_obj = db.query(DatabaseConnection).filter(
        DatabaseConnection.id == id,
        DatabaseConnection.organization_id == current_user.organization_id
    ).first()
    
    if not db_obj:
        raise HTTPException(status_code=404, detail="Database connection not found")
        
    db.delete(db_obj)
    db.commit()
    return None

@router.post("/database/chat")
def chat_with_database(
    query: DatabaseQuestion,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Ask a question to a specific database using AI."""
    db_conn = db.query(DatabaseConnection).filter(
        DatabaseConnection.id == query.connection_id,
        DatabaseConnection.organization_id == current_user.organization_id
    ).first()
    
    if not db_conn:
        raise HTTPException(status_code=404, detail="Database connection not found")
        
    result = sql_agent.ask_database(db_conn, query.question)
    return result
