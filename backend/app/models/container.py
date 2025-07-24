"""
Container and Terminal models
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import String


class ContainerStatus(str, Enum):
    """Container status enumeration"""
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    TERMINATED = "terminated"


class TerminalSession(SQLModel, table=True):
    """Terminal session database model"""
    id: Optional[str] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    container_id: str = Field(unique=True, index=True)
    status: str = Field(default=ContainerStatus.CREATING.value, sa_column=Column(String))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    project_files: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    environment_vars: Optional[Dict[str, str]] = Field(default=None, sa_column=Column(JSON))


class ContainerInfo(BaseModel):
    """Container information schema"""
    id: str
    status: ContainerStatus
    image: str
    created_at: datetime
    last_activity: datetime
    cpu_usage: Optional[float] = None
    memory_usage: Optional[int] = None
    network_enabled: bool = False


class TerminalCommand(BaseModel):
    """Terminal command schema"""
    command: str
    working_dir: Optional[str] = None
    environment: Optional[Dict[str, str]] = None


class TerminalOutput(BaseModel):
    """Terminal output schema"""
    data: str
    timestamp: datetime
    stream: str = "stdout"  # stdout, stderr, or system


class ContainerCreateRequest(BaseModel):
    """Request to create a new container"""
    project_name: Optional[str] = None
    initial_files: Optional[Dict[str, str]] = None
    environment_vars: Optional[Dict[str, str]] = None


class ContainerResponse(BaseModel):
    """Container creation response"""
    session_id: str
    container_id: str
    status: ContainerStatus
    websocket_url: str 