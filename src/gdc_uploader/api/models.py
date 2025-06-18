"""Pydantic models for GDC API requests and responses.

This module defines type-safe models for all API interactions,
providing validation and serialization for GDC data structures.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
from pathlib import Path
import re

from pydantic import BaseModel, Field, validator, root_validator


class FileState(str, Enum):
    """Possible states for a file in GDC."""
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    VALIDATED = "validated"
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    PROCESSED = "processed"
    RELEASED = "released"
    ERROR = "error"
    DELETED = "deleted"


class UploadStatus(str, Enum):
    """Status of an upload operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RESUMED = "resumed"


class ProjectState(str, Enum):
    """Possible states for a GDC project."""
    OPEN = "open"
    REVIEW = "review"
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    CLOSED = "closed"


class FileUploadRequest(BaseModel):
    """Request model for file upload."""
    
    file_id: str = Field(
        ...,
        description="GDC file UUID",
        regex="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    )
    project_id: str = Field(
        ...,
        description="GDC project ID",
        min_length=1,
        max_length=50
    )
    file_path: Union[str, Path] = Field(
        ...,
        description="Path to the file to upload"
    )
    file_size: int = Field(
        ...,
        gt=0,
        description="File size in bytes"
    )
    md5sum: Optional[str] = Field(
        None,
        regex="^[a-f0-9]{32}$",
        description="MD5 checksum of the file"
    )
    chunk_size: int = Field(
        default=10485760,  # 10MB
        gt=0,
        le=104857600,  # 100MB max
        description="Size of upload chunks in bytes"
    )
    resume_from: int = Field(
        default=0,
        ge=0,
        description="Byte offset to resume upload from"
    )
    
    @validator('file_id')
    def validate_uuid(cls, v):
        """Validate UUID format."""
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        if not uuid_pattern.match(v):
            raise ValueError(f"Invalid UUID format: {v}")
        return v.lower()
    
    @validator('file_path')
    def validate_file_path(cls, v):
        """Convert to Path and validate existence."""
        path = Path(v) if isinstance(v, str) else v
        if not path.exists():
            raise ValueError(f"File not found: {path}")
        if not path.is_file():
            raise ValueError(f"Not a file: {path}")
        return path
    
    @root_validator
    def validate_resume_offset(cls, values):
        """Ensure resume offset is within file size."""
        resume_from = values.get('resume_from', 0)
        file_size = values.get('file_size')
        if file_size and resume_from >= file_size:
            raise ValueError(
                f"Resume offset ({resume_from}) must be less than file size ({file_size})"
            )
        return values
    
    class Config:
        json_encoders = {
            Path: str
        }


class FileUploadResponse(BaseModel):
    """Response model for file upload."""
    
    file_id: str = Field(..., description="GDC file UUID")
    status: Union[UploadStatus, str] = Field(..., description="Upload status")
    uploaded_size: int = Field(..., ge=0, description="Bytes uploaded so far")
    timestamp: datetime = Field(..., description="Timestamp of this response")
    warnings: List[str] = Field(default_factory=list, description="Any warnings from the upload")
    errors: List[str] = Field(default_factory=list, description="Any errors from the upload")
    
    @property
    def is_complete(self) -> bool:
        """Check if upload is complete."""
        return self.status in (UploadStatus.COMPLETED, "completed")
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0


class FileStatus(BaseModel):
    """Current status of a file in GDC."""
    
    file_id: str = Field(..., description="GDC file UUID")
    project_id: str = Field(..., description="GDC project ID")
    state: Union[FileState, str] = Field(..., description="Current file state")
    uploaded_size: Optional[int] = Field(None, ge=0, description="Size of uploaded data")
    file_size: Optional[int] = Field(None, gt=0, description="Expected file size")
    md5sum: Optional[str] = Field(None, description="File MD5 checksum")
    created_datetime: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_datetime: Optional[datetime] = Field(None, description="Last update timestamp")
    error_message: Optional[str] = Field(None, description="Error message if state is ERROR")
    
    @property
    def upload_progress(self) -> Optional[float]:
        """Calculate upload progress as percentage."""
        if self.uploaded_size is not None and self.file_size:
            return (self.uploaded_size / self.file_size) * 100
        return None
    
    @property
    def is_uploaded(self) -> bool:
        """Check if file is fully uploaded."""
        return self.state in (
            FileState.UPLOADED,
            FileState.VALIDATED,
            FileState.SUBMITTED,
            FileState.PROCESSED,
            FileState.RELEASED
        )


class ProjectInfo(BaseModel):
    """Information about a GDC project."""
    
    project_id: str = Field(..., description="GDC project ID")
    name: str = Field(..., description="Project name")
    program: str = Field(..., description="Program name")
    state: Union[ProjectState, str] = Field(..., description="Project state")
    primary_site: Optional[str] = Field(None, description="Primary site")
    disease_type: Optional[str] = Field(None, description="Disease type")
    created_datetime: Optional[datetime] = Field(None, description="Creation timestamp")
    
    @property
    def is_open(self) -> bool:
        """Check if project is open for uploads."""
        return self.state == ProjectState.OPEN


class TokenValidationResponse(BaseModel):
    """Response from token validation."""
    
    is_valid: bool = Field(..., description="Whether token is valid")
    username: Optional[str] = Field(None, description="Username associated with token")
    projects: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Projects and permissions"
    )
    expires_at: Optional[datetime] = Field(None, description="Token expiration time")
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    def has_project_access(self, project_id: str, permission: str = "read") -> bool:
        """Check if token has access to a specific project."""
        project_perms = self.projects.get(project_id, [])
        return permission in project_perms


class GDCError(BaseModel):
    """Error response from GDC API."""
    
    error_type: str = Field(..., description="Type of error")
    message: str = Field(..., description="Error message")
    code: Optional[int] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class BatchUploadRequest(BaseModel):
    """Request for batch file upload."""
    
    project_id: str = Field(..., description="GDC project ID")
    files: List[FileUploadRequest] = Field(..., description="List of files to upload")
    parallel_uploads: int = Field(
        default=4,
        ge=1,
        le=10,
        description="Number of parallel uploads"
    )
    
    @validator('files')
    def validate_files_list(cls, v):
        """Ensure files list is not empty."""
        if not v:
            raise ValueError("Files list cannot be empty")
        return v


class BatchUploadResponse(BaseModel):
    """Response from batch upload operation."""
    
    total_files: int = Field(..., description="Total number of files")
    successful: int = Field(default=0, description="Number of successful uploads")
    failed: int = Field(default=0, description="Number of failed uploads")
    results: List[FileUploadResponse] = Field(
        default_factory=list,
        description="Individual file results"
    )
    start_time: datetime = Field(..., description="Batch start time")
    end_time: Optional[datetime] = Field(None, description="Batch end time")
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate batch duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_files > 0:
            return (self.successful / self.total_files) * 100
        return 0.0


class FileMetadata(BaseModel):
    """Metadata for a file to be uploaded."""
    
    file_name: str = Field(..., description="Original file name")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    md5sum: str = Field(..., regex="^[a-f0-9]{32}$", description="MD5 checksum")
    file_format: Optional[str] = Field(None, description="File format (e.g., BAM, FASTQ)")
    data_category: Optional[str] = Field(None, description="Data category")
    data_type: Optional[str] = Field(None, description="Data type")
    experimental_strategy: Optional[str] = Field(None, description="Experimental strategy")
    
    @validator('md5sum')
    def normalize_md5sum(cls, v):
        """Ensure MD5 is lowercase."""
        return v.lower()


class UploadManifest(BaseModel):
    """Manifest for upload operations."""
    
    manifest_version: str = Field(default="1.0", description="Manifest version")
    project_id: str = Field(..., description="GDC project ID")
    submission_id: Optional[str] = Field(None, description="Submission ID")
    files: List[Dict[str, Any]] = Field(..., description="List of files with metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")
    
    @validator('files')
    def validate_files_structure(cls, v):
        """Validate each file has required fields."""
        required_fields = {'id', 'filename', 'size', 'md5'}
        for idx, file_info in enumerate(v):
            missing = required_fields - set(file_info.keys())
            if missing:
                raise ValueError(
                    f"File at index {idx} missing required fields: {missing}"
                )
        return v