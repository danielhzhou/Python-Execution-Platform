"""
Container and Terminal models for Supabase integration
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from sqlmodel import SQLModel, Field, Column, JSON, Relationship, Text
from sqlalchemy import String, DateTime, ForeignKey


class ContainerStatus(str, Enum):
    """Container status enumeration"""
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    TERMINATED = "terminated"


class SubmissionStatus(str, Enum):
    """Submission status enumeration"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


# Database Models (SQLModel with table=True)

class User(SQLModel, table=True):
    """User profile information (extends Supabase auth.users)"""
    __tablename__ = "users"
    
    id: str = Field(primary_key=True)  # Matches Supabase auth.users.id
    email: str = Field(index=True)
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))
    
    # Relationships
    projects: List["Project"] = Relationship(back_populates="owner")
    terminal_sessions: List["TerminalSession"] = Relationship(back_populates="user")
    # submissions: List["Submission"] = Relationship(back_populates="user")  # Temporarily disabled due to foreign key ambiguity


class Project(SQLModel, table=True):
    """Project model for organizing user work"""
    __tablename__ = "projects"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    owner_id: str = Field(foreign_key="users.id", index=True)
    is_public: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))
    
    # Relationships
    owner: User = Relationship(back_populates="projects")
    terminal_sessions: List["TerminalSession"] = Relationship(back_populates="project")
    project_files: List["ProjectFile"] = Relationship(back_populates="project")
    submissions: List["Submission"] = Relationship(back_populates="project")


class ProjectFile(SQLModel, table=True):
    """Project files stored in Supabase Storage"""
    __tablename__ = "project_files"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    project_id: str = Field(foreign_key="projects.id", index=True)
    file_path: str = Field(index=True)  # Path within the project
    file_name: str
    content: Optional[str] = Field(sa_column=Column(Text))  # For text files
    storage_path: Optional[str] = None  # Supabase Storage path for binary files
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))
    
    # Relationships
    project: Project = Relationship(back_populates="project_files")


class TerminalSession(SQLModel, table=True):
    """Terminal session database model"""
    __tablename__ = "terminal_sessions"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    project_id: Optional[str] = Field(foreign_key="projects.id", index=True, default=None)
    container_id: str = Field(unique=True, index=True)
    status: str = Field(default=ContainerStatus.CREATING.value, sa_column=Column(String))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))
    last_activity: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))
    terminated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    
    # Container configuration
    container_image: str = Field(default="python-execution-sandbox:latest")
    cpu_limit: str = Field(default="1.0")
    memory_limit: str = Field(default="512m")
    environment_vars: Optional[Dict[str, str]] = Field(default=None, sa_column=Column(JSON))
    
    # Relationships
    user: User = Relationship(back_populates="terminal_sessions")
    project: Optional[Project] = Relationship(back_populates="terminal_sessions")
    commands: List["TerminalCommand"] = Relationship(back_populates="session")


class TerminalCommand(SQLModel, table=True):
    """Terminal command history"""
    __tablename__ = "terminal_commands"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(foreign_key="terminal_sessions.id", index=True)
    command: str = Field(sa_column=Column(Text))
    working_dir: str = Field(default="/workspace")
    exit_code: Optional[int] = None
    output: Optional[str] = Field(sa_column=Column(Text))
    error_output: Optional[str] = Field(sa_column=Column(Text))
    executed_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))
    duration_ms: Optional[int] = None  # Command execution time in milliseconds
    
    # Relationships
    session: TerminalSession = Relationship(back_populates="commands")


class Submission(SQLModel, table=True):
    """Code submission for review"""
    __tablename__ = "submissions"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    owner_id: str = Field(foreign_key="users.id", index=True)
    project_id: str = Field(foreign_key="projects.id", index=True)
    title: str
    description: Optional[str] = Field(sa_column=Column(Text))
    status: str = Field(default=SubmissionStatus.DRAFT.value, sa_column=Column(String, index=True))
    submitted_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    reviewed_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    reviewer_id: Optional[str] = Field(foreign_key="users.id", default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))
    
    # Relationships
    # user: User = Relationship(back_populates="submissions")  # Temporarily disabled due to foreign key ambiguity
    project: Project = Relationship(back_populates="submissions")
    files: List["SubmissionFile"] = Relationship(back_populates="submission")
    reviews: List["SubmissionReview"] = Relationship(back_populates="submission")


class SubmissionFile(SQLModel, table=True):
    """Files included in a submission"""
    __tablename__ = "submission_files"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    submission_id: str = Field(foreign_key="submissions.id", index=True)
    file_path: str
    file_name: str
    content: str = Field(sa_column=Column(Text))
    diff: Optional[str] = Field(sa_column=Column(Text))  # Git-style diff
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))
    
    # Relationships
    submission: Submission = Relationship(back_populates="files")


class SubmissionReview(SQLModel, table=True):
    """Reviews and comments on submissions"""
    __tablename__ = "submission_reviews"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    submission_id: str = Field(foreign_key="submissions.id", index=True)
    reviewer_id: str = Field(foreign_key="users.id", index=True)
    comment: str = Field(sa_column=Column(Text))
    file_path: Optional[str] = None  # Specific file being commented on
    line_number: Optional[int] = None  # Specific line being commented on
    is_resolved: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))
    
    # Relationships
    submission: Submission = Relationship(back_populates="reviews")


# API Response Models (Pydantic BaseModel)

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


class TerminalOutput(BaseModel):
    """Terminal output schema"""
    data: str
    timestamp: datetime
    stream: str = "stdout"  # stdout, stderr, or system


class ContainerCreateRequest(BaseModel):
    """Request to create a new container"""
    model_config = {"extra": "forbid"}  # Forbid extra fields
    
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    initial_files: Optional[Dict[str, str]] = None
    environment_vars: Optional[Dict[str, str]] = None


class ContainerResponse(BaseModel):
    """Container creation response"""
    session_id: str
    container_id: str
    status: str  # Changed from ContainerStatus to str for frontend compatibility
    websocket_url: str
    user_id: Optional[str] = None  # Add for frontend compatibility


class ProjectCreateRequest(BaseModel):
    """Request to create a new project"""
    name: str
    description: Optional[str] = None
    is_public: bool = False


class ProjectResponse(BaseModel):
    """Project response"""
    id: str
    name: str
    description: Optional[str] = None
    owner_id: str
    is_public: bool
    created_at: datetime
    updated_at: datetime


class SubmissionCreateRequest(BaseModel):
    """Request to create a new submission"""
    project_id: str
    title: str
    description: Optional[str] = None
    file_paths: List[str]  # List of files to include in submission


class SubmissionResponse(BaseModel):
    """Submission response"""
    id: str
    user_id: str
    project_id: str
    title: str
    description: Optional[str] = None
    status: SubmissionStatus
    created_at: datetime
    submitted_at: Optional[datetime] = None 