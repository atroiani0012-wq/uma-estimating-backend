from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Enum, JSON, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    projects = relationship("Project", back_populates="owner")
    audit_logs = relationship("AuditLog", back_populates="user")


class ProjectStatus(str, enum.Enum):
    CREATED = "created"
    ANALYZING = "analyzing"
    INFO_SHEET_READY = "info_sheet_ready"
    APPROVED = "approved"
    COMPLETED = "completed"


class ProjectPhase(str, enum.Enum):
    RAW_DOCUMENTS = "raw_documents"
    EXTRACTED_DATA = "extracted_data"
    INTERPRETED_SCOPE = "interpreted_scope"
    APPROVED_SCOPE = "approved_scope"
    ESTIMATE_DEVELOPMENT = "estimate_development"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Basic info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.CREATED)

    # Estimating workflow fields
    project_name = Column(String(255), nullable=True)
    project_number = Column(String(50), unique=True, nullable=True, index=True)
    location = Column(String(255), nullable=True)
    client_name = Column(String(255), nullable=True)
    bid_date = Column(DateTime, nullable=True)
    version_number = Column(Integer, default=1)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Phase progression
    current_phase = Column(Enum(ProjectPhase), default=ProjectPhase.RAW_DOCUMENTS)
    phase_data = Column(JSON, default={})  # Structured data per phase

    # Approval gates
    scope_interpretation_approved = Column(Boolean, default=False)
    scope_assumptions_locked = Column(Boolean, default=False)
    estimate_version_approved = Column(Boolean, default=False)

    # Tracking complexity
    document_count = Column(Integer, default=0)
    assumption_count = Column(Integer, default=0)
    revision_count = Column(Integer, default=0)

    # Learning system hooks
    linked_update_log_entries = Column(JSON, default=[])
    linked_journal_entries = Column(JSON, default=[])

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    phase_changed_at = Column(DateTime, nullable=True)
    last_user_action_at = Column(DateTime, nullable=True)

    # Relationships
    owner = relationship("User", back_populates="projects")
    documents = relationship("Document", back_populates="project")
    audit_logs = relationship("AuditLog", back_populates="project")
    google_drive_files = relationship("GoogleDriveFile", back_populates="project")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_type = Column(String(50), nullable=False)  # pdf, docx, etc.
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="documents")


class AuditLogCategory(str, enum.Enum):
    AUTH = "auth"
    PROJECT_LIFECYCLE = "project_lifecycle"
    DOCUMENT_INGESTION = "document_ingestion"
    SCOPE_INTERPRETATION = "scope_interpretation"
    ASSUMPTION_ENTRY = "assumption_entry"
    APPROVAL_GATE = "approval_gate"
    ESTIMATE_GENERATION = "estimate_generation"
    REVISION = "revision"
    LEARNING_FEEDBACK = "learning_feedback"
    JOURNAL_ENTRY = "journal_entry"
    GOOGLE_DRIVE = "google_drive"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)

    # Action tracking
    action = Column(String(255), nullable=False)
    action_category = Column(Enum(AuditLogCategory), nullable=True)
    description = Column(Text, nullable=True)

    # State change tracking
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    what_changed = Column(String(255), nullable=True)
    why_changed = Column(Text, nullable=True)
    affected_modules = Column(JSON, default=[])

    # Learning system fields
    decision_confidence = Column(Integer, nullable=True)  # 0-100
    learning_signal_value = Column(Integer, nullable=True)  # 0-10
    was_corrected_later = Column(Boolean, default=False)
    correction_entry_id = Column(Integer, nullable=True)

    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
    project = relationship("Project", back_populates="audit_logs")


class GoogleDriveConnection(Base):
    __tablename__ = "google_drive_connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)

    # OAuth tokens (encrypted at rest)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_expires_at = Column(DateTime, nullable=False)

    # Folder selection
    selected_folder_id = Column(String(255), nullable=True)
    selected_folder_name = Column(String(255), nullable=True)
    selected_folder_path = Column(String(512), nullable=True)

    # Connection status
    is_active = Column(Boolean, default=True)
    connected_at = Column(DateTime, default=datetime.utcnow)
    last_verified_at = Column(DateTime, nullable=True)

    # OAuth security
    oauth_state = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    sync_logs = relationship("GoogleDriveSyncLog", back_populates="connection")


class GoogleDriveSyncStatus(str, enum.Enum):
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"
    PARTIAL = "partial"
    STUCK_UPLOAD = "stuck_upload"
    DELETED = "deleted"


class GoogleDriveProcessingStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    EXTRACTING = "extracting"
    COMPLETE = "complete"
    FAILED = "failed"


class GoogleDriveFile(Base):
    __tablename__ = "google_drive_files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)

    # Google Drive identifiers
    google_file_id = Column(String(255), unique=True, nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # pdf, docx, xlsx, image, zip, google_doc, etc.
    mimetype = Column(String(100), nullable=True)

    # File location
    folder_path = Column(String(512), nullable=True)

    # Sync status
    sync_status = Column(Enum(GoogleDriveSyncStatus), default=GoogleDriveSyncStatus.PENDING)
    downloaded_at = Column(DateTime, nullable=True)
    last_sync_error = Column(Text, nullable=True)
    sync_attempt_count = Column(Integer, default=0)

    # Stability tracking (for partial uploads)
    upload_in_progress = Column(Boolean, default=False)
    last_size_check = Column(DateTime, nullable=True)
    stability_check_count = Column(Integer, default=0)
    first_detected_at = Column(DateTime, default=datetime.utcnow)
    last_detected_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # File tracking
    file_size_bytes = Column(BigInteger, nullable=True)
    google_last_modified_at = Column(DateTime, nullable=True)

    # Processing status
    processing_status = Column(Enum(GoogleDriveProcessingStatus), default=GoogleDriveProcessingStatus.NOT_STARTED)
    local_cache_path = Column(String(512), nullable=True)

    # Project association
    association_method = Column(String(50), nullable=True)  # auto_folder, auto_filename, manual, shared, unassociated
    association_confidence = Column(Integer, nullable=True)  # 0-100
    association_confirmed_by_user = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="google_drive_files")


class GoogleDriveSyncLog(Base):
    __tablename__ = "google_drive_sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    connection_id = Column(Integer, ForeignKey("google_drive_connections.id"), nullable=False)

    # Sync tracking
    sync_type = Column(String(50), nullable=False)  # full_sync, manual_sync, file_check
    sync_started_at = Column(DateTime, default=datetime.utcnow)
    sync_completed_at = Column(DateTime, nullable=True)

    # Results
    files_processed = Column(Integer, default=0)
    files_successful = Column(Integer, default=0)
    files_failed = Column(Integer, default=0)
    error_summary = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    connection = relationship("GoogleDriveConnection", back_populates="sync_logs")
