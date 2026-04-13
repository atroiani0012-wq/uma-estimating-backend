from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from database import get_db
from models import User, Project, AuditLog, GoogleDriveConnection, GoogleDriveFile, GoogleDriveSyncLog, AuditLogCategory
from schemas import (
    UserCreate, UserLogin, Token, UserResponse,
    ProjectCreate, ProjectResponse, ProjectList,
    GoogleDriveConnectionResponse, GoogleDriveSyncStatusResponse,
    FolderListResponse, SelectFolderRequest
)
from auth import hash_password, verify_password, create_access_token, get_current_user
from config import settings
import os

router = APIRouter()


# ============= AUTH ROUTES =============

@router.post("/auth/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    hashed_pwd = hash_password(user.password)
    new_user = User(
        email=user.email,
        hashed_password=hashed_pwd,
        full_name=user.full_name
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Log action
    audit = AuditLog(
        user_id=new_user.id,
        action="USER_REGISTERED",
        description=f"User registered: {new_user.email}"
    )
    db.add(audit)
    db.commit()

    return new_user


@router.post("/auth/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user and return JWT token"""
    user = db.query(User).filter(User.email == credentials.email).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=access_token_expires
    )

    # Log action
    audit = AuditLog(
        user_id=user.id,
        action="USER_LOGIN",
        description=f"User logged in: {user.email}"
    )
    db.add(audit)
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.get("/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


# ============= PROJECT ROUTES =============

@router.post("/projects", response_model=ProjectResponse)
def create_project(
    project: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new project"""
    new_project = Project(
        user_id=current_user.id,
        name=project.name,
        description=project.description
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    # Log action
    audit = AuditLog(
        user_id=current_user.id,
        project_id=new_project.id,
        action="PROJECT_CREATED",
        description=f"Project created: {new_project.name}"
    )
    db.add(audit)
    db.commit()

    return new_project


@router.get("/projects", response_model=ProjectList)
def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50
):
    """List all projects for current user"""
    projects = db.query(Project).filter(
        Project.user_id == current_user.id
    ).offset(skip).limit(limit).all()

    total = db.query(Project).filter(
        Project.user_id == current_user.id
    ).count()

    return {
        "projects": projects,
        "total": total
    }


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific project"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return project


@router.put("/projects/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_update: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a project"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    if project_update.name:
        project.name = project_update.name
    if project_update.description is not None:
        project.description = project_update.description

    db.commit()
    db.refresh(project)

    # Log action
    audit = AuditLog(
        user_id=current_user.id,
        project_id=project.id,
        action="PROJECT_UPDATED",
        description=f"Project updated: {project.name}"
    )
    db.add(audit)
    db.commit()

    return project


# ============= GOOGLE DRIVE ROUTES =============

@router.get("/google/oauth-url")
def get_oauth_url(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate Google OAuth login URL"""
    # Check if already connected
    existing_connection = db.query(GoogleDriveConnection).filter(
        GoogleDriveConnection.user_id == current_user.id
    ).first()

    if existing_connection and existing_connection.is_active:
        return {
            "status": "already_connected",
            "message": "User already has active Google Drive connection"
        }

    # Generate OAuth state for security
    oauth_state = os.urandom(16).hex()

    # In production, would construct proper Google OAuth URL
    # For now, return structure for frontend
    google_client_id = settings.google_client_id
    redirect_uri = settings.google_redirect_uri

    auth_url = (
        f"https://accounts.google.com/o/oauth2/auth?"
        f"client_id={google_client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope=https://www.googleapis.com/auth/drive.readonly&"
        f"state={oauth_state}&"
        f"access_type=offline&"
        f"prompt=consent"
    )

    # Store state in session/cache for validation
    # (In production, would use Redis or session storage)

    return {
        "auth_url": auth_url,
        "state": oauth_state
    }


@router.post("/google/oauth-callback")
def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback"""
    # Verify state parameter (CSRF protection)
    # In production, would validate against stored state

    # Exchange code for tokens
    # This is where actual Google API call would happen
    # For now, return structure

    return {
        "success": True,
        "message": "OAuth connection established",
        "next_step": "select_folder"
    }


@router.get("/google/connection-status", response_model=GoogleDriveConnectionResponse)
def get_connection_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check current Google Drive connection status"""
    connection = db.query(GoogleDriveConnection).filter(
        GoogleDriveConnection.user_id == current_user.id
    ).first()

    if not connection or not connection.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Google Drive connection"
        )

    # Get last sync info
    last_sync = db.query(GoogleDriveSyncLog).filter(
        GoogleDriveSyncLog.connection_id == connection.id
    ).order_by(GoogleDriveSyncLog.sync_completed_at.desc()).first()

    return {
        "is_connected": True,
        "connected_at": connection.connected_at.isoformat(),
        "selected_folder_id": connection.selected_folder_id,
        "selected_folder_name": connection.selected_folder_name,
        "selected_folder_path": connection.selected_folder_path,
        "last_sync_at": last_sync.sync_completed_at.isoformat() if last_sync else None,
        "is_active": connection.is_active
    }


@router.post("/google/sync-now")
def sync_now(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trigger manual Google Drive sync"""
    connection = db.query(GoogleDriveConnection).filter(
        GoogleDriveConnection.user_id == current_user.id,
        GoogleDriveConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Google Drive connection"
        )

    if not connection.selected_folder_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No folder selected for sync"
        )

    # Create sync log entry
    sync_log = GoogleDriveSyncLog(
        user_id=current_user.id,
        connection_id=connection.id,
        sync_type="manual_sync"
    )
    db.add(sync_log)
    db.commit()

    # Log audit entry
    audit = AuditLog(
        user_id=current_user.id,
        action="manual_sync_triggered",
        action_category=AuditLogCategory.GOOGLE_DRIVE,
        description="User manually triggered Google Drive sync"
    )
    db.add(audit)
    db.commit()

    return {
        "sync_id": sync_log.id,
        "sync_started_at": sync_log.sync_started_at.isoformat(),
        "status": "in_progress"
    }


@router.get("/google/sync-status", response_model=GoogleDriveSyncStatusResponse)
def get_sync_status(
    sync_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check status of a sync operation"""
    sync_log = db.query(GoogleDriveSyncLog).filter(
        GoogleDriveSyncLog.id == sync_id,
        GoogleDriveSyncLog.user_id == current_user.id
    ).first()

    if not sync_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sync log not found"
        )

    status_str = "in_progress" if not sync_log.sync_completed_at else "completed"

    return {
        "sync_id": sync_log.id,
        "status": status_str,
        "started_at": sync_log.sync_started_at.isoformat(),
        "completed_at": sync_log.sync_completed_at.isoformat() if sync_log.sync_completed_at else None,
        "duration_seconds": int((sync_log.sync_completed_at - sync_log.sync_started_at).total_seconds()) if sync_log.sync_completed_at else None,
        "files_found": sync_log.files_processed,
        "files_synced": sync_log.files_successful,
        "files_failed": sync_log.files_failed,
        "error_summary": sync_log.error_summary
    }


@router.get("/google/folders", response_model=FolderListResponse)
def get_folders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List available Google Drive folders (stubbed for Phase 1A-1)"""
    connection = db.query(GoogleDriveConnection).filter(
        GoogleDriveConnection.user_id == current_user.id,
        GoogleDriveConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Google Drive connection"
        )

    # In Phase 1A-2, this will call actual Google Drive API
    # For Phase 1A-1, return stub structure with test folder ID
    # In production, would use: google_drive_service.files().list()

    return {
        "folders": [
            {
                "id": "1RVEm93B4524fUgypEmEfH44FKdHpyhlJ",
                "name": "UMA Estimating",
                "path": "My Drive > UMA Estimating",
                "file_count": 0
            }
        ]
    }


@router.post("/google/select-folder")
def select_folder(
    folder_data: SelectFolderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """User selects which Google Drive folder to monitor"""
    connection = db.query(GoogleDriveConnection).filter(
        GoogleDriveConnection.user_id == current_user.id,
        GoogleDriveConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Google Drive connection"
        )

    # Update folder selection
    connection.selected_folder_id = folder_data.folder_id
    connection.selected_folder_name = folder_data.folder_name
    connection.selected_folder_path = folder_data.folder_path or folder_data.folder_name
    db.commit()

    # Log action
    audit = AuditLog(
        user_id=current_user.id,
        action="folder_selected",
        action_category=AuditLogCategory.GOOGLE_DRIVE,
        description=f"Selected Google Drive folder: {folder_data.folder_name}",
        after_state={
            "selected_folder_id": folder_data.folder_id,
            "selected_folder_name": folder_data.folder_name,
            "selected_folder_path": folder_data.folder_path
        }
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "folder_selected": folder_data.folder_name,
        "message": "Folder selected. Ready to sync."
    }


@router.post("/google/disconnect")
def disconnect_google(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect Google Drive and revoke access"""
    connection = db.query(GoogleDriveConnection).filter(
        GoogleDriveConnection.user_id == current_user.id
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Google Drive connection found"
        )

    # Mark as inactive (keep tokens for potential reconnection)
    connection.is_active = False
    db.commit()

    # Log action
    audit = AuditLog(
        user_id=current_user.id,
        action="google_drive_disconnected",
        action_category=AuditLogCategory.GOOGLE_DRIVE,
        description="User disconnected Google Drive integration"
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "message": "Google Drive connection disabled"
    }
