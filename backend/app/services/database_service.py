"""
Database service layer for Supabase integration
Provides CRUD operations for all models
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlmodel import Session, select, and_, or_
from sqlalchemy.exc import IntegrityError

from app.core.supabase import get_db_session, get_supabase_client
from app.models.container import (
    User, Project, ProjectFile, TerminalSession, TerminalCommand,
    Submission, SubmissionFile, SubmissionReview,
    ContainerStatus, SubmissionStatus
)

logger = logging.getLogger(__name__)


class DatabaseService:
    """Database service for all CRUD operations"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    # User operations
    async def create_or_update_user(self, user_id: str, email: str, 
                                  full_name: Optional[str] = None,
                                  avatar_url: Optional[str] = None) -> User:
        """Create or update a user record (optimized to avoid unnecessary updates)"""
        with get_db_session() as session:
            # Check if user exists
            existing_user = session.get(User, user_id)
            
            if existing_user:
                # Only update if data has actually changed
                needs_update = False
                
                if existing_user.email != email:
                    existing_user.email = email
                    needs_update = True
                    
                if full_name and existing_user.full_name != full_name:
                    existing_user.full_name = full_name
                    needs_update = True
                    
                if avatar_url and existing_user.avatar_url != avatar_url:
                    existing_user.avatar_url = avatar_url
                    needs_update = True
                
                # Only commit if something actually changed
                if needs_update:
                    existing_user.updated_at = datetime.utcnow()
                    session.add(existing_user)
                    session.commit()
                    session.refresh(existing_user)
                    logger.debug(f"Updated user data for {email}")
                else:
                    logger.debug(f"No changes needed for user {email}")
                
                return existing_user
            else:
                # Create new user
                user = User(
                    id=user_id,
                    email=email,
                    full_name=full_name,
                    avatar_url=avatar_url
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                logger.info(f"Created new user: {email}")
                return user
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID"""
        with get_db_session() as session:
            return session.get(User, user_id)
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email"""
        with get_db_session() as session:
            statement = select(User).where(User.email == email)
            return session.exec(statement).first()
    
    # Project operations
    async def create_project(self, name: str, owner_id: str, 
                           description: Optional[str] = None,
                           is_public: bool = False) -> Project:
        """Create a new project"""
        with get_db_session() as session:
            project = Project(
                name=name,
                description=description,
                owner_id=owner_id,
                is_public=is_public
            )
            session.add(project)
            session.commit()
            session.refresh(project)
            return project
    
    async def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID"""
        with get_db_session() as session:
            return session.get(Project, project_id)
    
    async def get_user_projects(self, user_id: str) -> List[Project]:
        """Get all projects for a user"""
        with get_db_session() as session:
            statement = select(Project).where(Project.owner_id == user_id)
            return list(session.exec(statement).all())
    
    async def update_project(self, project_id: str, **updates) -> Optional[Project]:
        """Update a project"""
        with get_db_session() as session:
            project = session.get(Project, project_id)
            if not project:
                return None
            
            for key, value in updates.items():
                if hasattr(project, key):
                    setattr(project, key, value)
            
            project.updated_at = datetime.utcnow()
            session.add(project)
            session.commit()
            session.refresh(project)
            return project
    
    async def delete_project(self, project_id: str) -> bool:
        """Delete a project"""
        with get_db_session() as session:
            project = session.get(Project, project_id)
            if not project:
                return False
            
            session.delete(project)
            session.commit()
            return True
    
    # Project file operations
    async def create_project_file(self, project_id: str, file_path: str, 
                                file_name: str, content: Optional[str] = None,
                                storage_path: Optional[str] = None,
                                file_size: Optional[int] = None,
                                mime_type: Optional[str] = None) -> ProjectFile:
        """Create a project file"""
        with get_db_session() as session:
            project_file = ProjectFile(
                project_id=project_id,
                file_path=file_path,
                file_name=file_name,
                content=content,
                storage_path=storage_path,
                file_size=file_size,
                mime_type=mime_type
            )
            session.add(project_file)
            session.commit()
            session.refresh(project_file)
            return project_file
    
    async def get_project_files(self, project_id: str) -> List[ProjectFile]:
        """Get all files for a project"""
        with get_db_session() as session:
            statement = select(ProjectFile).where(ProjectFile.project_id == project_id)
            return list(session.exec(statement).all())
    
    async def get_project_file(self, file_id: str) -> Optional[ProjectFile]:
        """Get a project file by ID"""
        with get_db_session() as session:
            return session.get(ProjectFile, file_id)
    
    async def update_project_file(self, file_id: str, **updates) -> Optional[ProjectFile]:
        """Update a project file"""
        with get_db_session() as session:
            project_file = session.get(ProjectFile, file_id)
            if not project_file:
                return None
            
            for key, value in updates.items():
                if hasattr(project_file, key):
                    setattr(project_file, key, value)
            
            project_file.updated_at = datetime.utcnow()
            session.add(project_file)
            session.commit()
            session.refresh(project_file)
            return project_file
    
    async def delete_project_file(self, file_id: str) -> bool:
        """Delete a project file"""
        with get_db_session() as session:
            project_file = session.get(ProjectFile, file_id)
            if not project_file:
                return False
            
            session.delete(project_file)
            session.commit()
            return True
    
    # Terminal session operations
    async def create_terminal_session(self, user_id: str, container_id: str,
                                    project_id: Optional[str] = None,
                                    container_image: str = "python-execution-sandbox:latest",
                                    cpu_limit: str = "1.0",
                                    memory_limit: str = "512m",
                                    environment_vars: Optional[Dict[str, str]] = None) -> TerminalSession:
        """Create a terminal session"""
        with get_db_session() as session:
            terminal_session = TerminalSession(
                user_id=user_id,
                project_id=project_id,
                container_id=container_id,
                status=ContainerStatus.CREATING.value,
                container_image=container_image,
                cpu_limit=cpu_limit,
                memory_limit=memory_limit,
                environment_vars=environment_vars
            )
            session.add(terminal_session)
            session.commit()
            session.refresh(terminal_session)
            return terminal_session
    
    async def get_terminal_session(self, session_id: str) -> Optional[TerminalSession]:
        """Get a terminal session by ID"""
        with get_db_session() as session:
            return session.get(TerminalSession, session_id)
    
    async def get_all_terminal_sessions(self) -> List[TerminalSession]:
        """Get all terminal sessions"""
        with get_db_session() as session:
            result = session.exec(select(TerminalSession))
            return result.all()
            
    async def get_terminal_session_by_container(self, container_id: str) -> Optional[TerminalSession]:
        """Get a terminal session by container ID"""
        with get_db_session() as session:
            statement = select(TerminalSession).where(TerminalSession.container_id == container_id)
            return session.exec(statement).first()
    
    async def get_user_terminal_sessions(self, user_id: str, active_only: bool = False) -> List[TerminalSession]:
        """Get all terminal sessions for a user"""
        with get_db_session() as session:
            statement = select(TerminalSession).where(TerminalSession.user_id == user_id)
            
            if active_only:
                statement = statement.where(
                    and_(
                        TerminalSession.status == ContainerStatus.RUNNING.value,
                        TerminalSession.terminated_at.is_(None)
                    )
                )
            
            return list(session.exec(statement).all())
    
    async def update_terminal_session(self, session_id: str, **updates) -> Optional[TerminalSession]:
        """Update a terminal session"""
        with get_db_session() as session:
            terminal_session = session.get(TerminalSession, session_id)
            if not terminal_session:
                return None
            
            for key, value in updates.items():
                if hasattr(terminal_session, key):
                    setattr(terminal_session, key, value)
            
            session.add(terminal_session)
            session.commit()
            session.refresh(terminal_session)
            return terminal_session
    
    async def terminate_terminal_session(self, session_id: str) -> bool:
        """Mark a terminal session as terminated"""
        with get_db_session() as session:
            terminal_session = session.get(TerminalSession, session_id)
            if not terminal_session:
                return False
            
            terminal_session.status = ContainerStatus.TERMINATED.value
            terminal_session.terminated_at = datetime.utcnow()
            session.add(terminal_session)
            session.commit()
            return True

    async def cleanup_old_sessions(self, days_old: int = 7) -> int:
        """Clean up old terminated sessions older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        with get_db_session() as session:
            # Find old terminated sessions
            statement = select(TerminalSession).where(
                and_(
                    or_(
                        TerminalSession.status == ContainerStatus.TERMINATED.value,
                        TerminalSession.status == 'error'
                    ),
                    TerminalSession.terminated_at < cutoff_date
                )
            )
            
            old_sessions = session.exec(statement).all()
            count = len(old_sessions)
            
            # Delete them
            for old_session in old_sessions:
                session.delete(old_session)
            
            session.commit()
            return count
    
    # Terminal command operations
    async def create_terminal_command(self, session_id: str, command: str,
                                    working_dir: str = "/workspace",
                                    exit_code: Optional[int] = None,
                                    output: Optional[str] = None,
                                    error_output: Optional[str] = None,
                                    duration_ms: Optional[int] = None) -> TerminalCommand:
        """Create a terminal command record"""
        with get_db_session() as session:
            terminal_command = TerminalCommand(
                session_id=session_id,
                command=command,
                working_dir=working_dir,
                exit_code=exit_code,
                output=output,
                error_output=error_output,
                duration_ms=duration_ms
            )
            session.add(terminal_command)
            session.commit()
            session.refresh(terminal_command)
            return terminal_command
    
    async def get_session_commands(self, session_id: str, limit: int = 100) -> List[TerminalCommand]:
        """Get commands for a terminal session"""
        with get_db_session() as session:
            statement = (
                select(TerminalCommand)
                .where(TerminalCommand.session_id == session_id)
                .order_by(TerminalCommand.executed_at.desc())
                .limit(limit)
            )
            return list(session.exec(statement).all())
    
    # Submission operations
    async def create_submission(self, user_id: str, project_id: str, 
                              title: str, description: Optional[str] = None) -> Submission:
        """Create a submission"""
        with get_db_session() as session:
            submission = Submission(
                owner_id=user_id,
                project_id=project_id,
                title=title,
                description=description,
                status=SubmissionStatus.DRAFT.value
            )
            session.add(submission)
            session.commit()
            session.refresh(submission)
            return submission
    
    async def get_submission(self, submission_id: str) -> Optional[Submission]:
        """Get a submission by ID"""
        with get_db_session() as session:
            return session.get(Submission, submission_id)
    
    async def get_user_submissions(self, user_id: str) -> List[Submission]:
        """Get all submissions for a user"""
        with get_db_session() as session:
            statement = select(Submission).where(Submission.owner_id == user_id)
            return list(session.exec(statement).all())
    
    async def update_submission(self, submission_id: str, **updates) -> Optional[Submission]:
        """Update a submission"""
        with get_db_session() as session:
            submission = session.get(Submission, submission_id)
            if not submission:
                return None
            
            for key, value in updates.items():
                if hasattr(submission, key):
                    setattr(submission, key, value)
            
            submission.updated_at = datetime.utcnow()
            session.add(submission)
            session.commit()
            session.refresh(submission)
            return submission
    
    async def submit_submission(self, submission_id: str) -> Optional[Submission]:
        """Submit a submission for review"""
        return await self.update_submission(
            submission_id,
            status=SubmissionStatus.SUBMITTED.value,
            submitted_at=datetime.utcnow()
        )
    
    # Submission file operations
    async def create_submission_file(self, submission_id: str, file_path: str,
                                   file_name: str, content: str,
                                   diff: Optional[str] = None) -> SubmissionFile:
        """Create a submission file"""
        with get_db_session() as session:
            submission_file = SubmissionFile(
                submission_id=submission_id,
                file_path=file_path,
                file_name=file_name,
                content=content,
                diff=diff
            )
            session.add(submission_file)
            session.commit()
            session.refresh(submission_file)
            return submission_file
    
    async def get_submission_files(self, submission_id: str) -> List[SubmissionFile]:
        """Get all files for a submission"""
        with get_db_session() as session:
            statement = select(SubmissionFile).where(SubmissionFile.submission_id == submission_id)
            return list(session.exec(statement).all())
    
    # Submission review operations
    async def create_submission_review(self, submission_id: str, reviewer_id: str,
                                     comment: str, file_path: Optional[str] = None,
                                     line_number: Optional[int] = None) -> SubmissionReview:
        """Create a submission review"""
        with get_db_session() as session:
            review = SubmissionReview(
                submission_id=submission_id,
                reviewer_id=reviewer_id,
                comment=comment,
                file_path=file_path,
                line_number=line_number
            )
            session.add(review)
            session.commit()
            session.refresh(review)
            return review
    
    async def get_submission_reviews(self, submission_id: str) -> List[SubmissionReview]:
        """Get all reviews for a submission"""
        with get_db_session() as session:
            statement = select(SubmissionReview).where(SubmissionReview.submission_id == submission_id)
            return list(session.exec(statement).all())
    
    # Cleanup operations
    async def cleanup_expired_sessions(self, timeout_seconds: int = 1800) -> int:
        """Clean up expired terminal sessions"""
        with get_db_session() as session:
            cutoff_time = datetime.utcnow().timestamp() - timeout_seconds
            
            statement = select(TerminalSession).where(
                and_(
                    TerminalSession.status == ContainerStatus.RUNNING.value,
                    TerminalSession.last_activity < datetime.fromtimestamp(cutoff_time)
                )
            )
            
            expired_sessions = session.exec(statement).all()
            count = 0
            
            for terminal_session in expired_sessions:
                terminal_session.status = ContainerStatus.TERMINATED.value
                terminal_session.terminated_at = datetime.utcnow()
                session.add(terminal_session)
                count += 1
            
            session.commit()
            return count


# Global database service instance
db_service = DatabaseService() 