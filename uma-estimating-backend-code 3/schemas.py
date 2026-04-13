from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

# User Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Token Schema
class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# Project Schemas
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class ProjectResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProjectList(BaseModel):
    projects: List[ProjectResponse]
    total: int


# Google Drive Schemas
class GoogleDriveConnectionResponse(BaseModel):
    is_connected: bool
    connected_at: Optional[str]
    selected_folder_id: Optional[str]
    selected_folder_name: Optional[str]
    selected_folder_path: Optional[str]
    last_sync_at: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class GoogleDriveSyncStatusResponse(BaseModel):
    sync_id: int
    status: str  # in_progress, completed
    started_at: str
    completed_at: Optional[str]
    duration_seconds: Optional[int]
    files_found: int
    files_synced: int
    files_failed: int
    error_summary: Optional[str]

    class Config:
        from_attributes = True


class FolderResponse(BaseModel):
    id: str
    name: str
    path: str
    file_count: int


class FolderListResponse(BaseModel):
    folders: List[FolderResponse]


class SelectFolderRequest(BaseModel):
    folder_id: str
    folder_name: str
    folder_path: Optional[str] = None
