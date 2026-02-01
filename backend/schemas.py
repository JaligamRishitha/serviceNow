from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List
from models import UserRole, IncidentPriority, IncidentStatus, TicketType, TicketStatus, ApprovalStatus

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.user

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class IncidentBase(BaseModel):
    title: str
    description: str
    priority: IncidentPriority = IncidentPriority.medium

class IncidentCreate(IncidentBase):
    pass

class IncidentResponse(IncidentBase):
    id: int
    status: IncidentStatus
    reporter_id: int
    assigned_to_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ServiceCatalogItemResponse(BaseModel):
    id: int
    name: str
    description: str
    category: str
    created_at: datetime

    class Config:
        from_attributes = True

class KnowledgeArticleBase(BaseModel):
    title: str
    content: str
    summary: str
    category: str
    tags: str

class KnowledgeArticleCreate(KnowledgeArticleBase):
    pass

class KnowledgeArticleResponse(KnowledgeArticleBase):
    id: int
    author_id: int
    views: int
    helpful_votes: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TicketBase(BaseModel):
    title: str
    description: str
    ticket_type: TicketType = TicketType.service_request
    priority: IncidentPriority = IncidentPriority.medium
    category: Optional[str] = None
    subcategory: Optional[str] = None
    contact_number: Optional[str] = None
    preferred_contact: str = "email"
    urgency: str = "medium"
    business_justification: Optional[str] = None
    estimated_cost: Optional[str] = None

class TicketCreate(TicketBase):
    pass

class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TicketStatus] = None
    priority: Optional[IncidentPriority] = None
    assigned_to_id: Optional[int] = None
    resolution_notes: Optional[str] = None

class TicketResponse(TicketBase):
    id: int
    ticket_number: str
    status: TicketStatus
    requester_id: int
    assigned_to_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    due_date: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    requester_name: Optional[str] = None
    assigned_to_name: Optional[str] = None
    # ServiceNow integration fields
    servicenow_sys_id: Optional[str] = None
    servicenow_number: Optional[str] = None

    class Config:
        from_attributes = True

class ApprovalBase(BaseModel):
    comments: Optional[str] = None

class ApprovalCreate(ApprovalBase):
    ticket_id: int
    approver_id: int

class ApprovalUpdate(BaseModel):
    status: ApprovalStatus
    comments: Optional[str] = None

class ApprovalResponse(ApprovalBase):
    id: int
    ticket_id: int
    approver_id: int
    status: ApprovalStatus
    approved_at: Optional[datetime] = None
    created_at: datetime               
    ticket_number: Optional[str] = None                  
    ticket_title: Optional[str] = None
    requester_name: Optional[str] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str