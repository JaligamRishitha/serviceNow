from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from database import Base

class UserRole(str, enum.Enum):
    admin = "admin"
    agent = "agent"
    user = "user"

class IncidentPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class IncidentStatus(str, enum.Enum):
    new = "new"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"

class TicketType(str, enum.Enum):
    incident = "incident"
    service_request = "service_request"
    change_request = "change_request"
    problem = "problem"

class TicketStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"
    cancelled = "cancelled"

class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    role = Column(Enum(UserRole), default=UserRole.user)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    reported_incidents = relationship("Incident", back_populates="reporter", foreign_keys="Incident.reporter_id")
    assigned_incidents = relationship("Incident", back_populates="assigned_to", foreign_keys="Incident.assigned_to_id")
    submitted_tickets = relationship("Ticket", back_populates="requester", foreign_keys="Ticket.requester_id")
    assigned_tickets = relationship("Ticket", back_populates="assigned_to", foreign_keys="Ticket.assigned_to_id")
    pending_approvals = relationship("Approval", back_populates="approver", foreign_keys="Approval.approver_id")

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    priority = Column(Enum(IncidentPriority), default=IncidentPriority.medium)
    status = Column(Enum(IncidentStatus), default=IncidentStatus.new)
    reporter_id = Column(Integer, ForeignKey("users.id"))
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reporter = relationship("User", back_populates="reported_incidents", foreign_keys=[reporter_id])
    assigned_to = relationship("User", back_populates="assigned_incidents", foreign_keys=[assigned_to_id])

class ServiceCatalogItem(Base):
    __tablename__ = "service_catalog_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text)
    category = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class KnowledgeArticle(Base):
    __tablename__ = "knowledge_articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text)
    summary = Column(Text)
    category = Column(String, index=True)
    tags = Column(String)  # Comma-separated tags
    author_id = Column(Integer, ForeignKey("users.id"))
    views = Column(Integer, default=0)
    helpful_votes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author = relationship("User", foreign_keys=[author_id])

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String, unique=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    ticket_type = Column(Enum(TicketType), default=TicketType.service_request)
    status = Column(Enum(TicketStatus), default=TicketStatus.submitted)
    priority = Column(Enum(IncidentPriority), default=IncidentPriority.medium)
    category = Column(String)
    subcategory = Column(String)
    requester_id = Column(Integer, ForeignKey("users.id"))
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    contact_number = Column(String, nullable=True)
    preferred_contact = Column(String, default="email")
    urgency = Column(String, default="medium")
    business_justification = Column(Text, nullable=True)
    estimated_cost = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    requester = relationship("User", back_populates="submitted_tickets", foreign_keys=[requester_id])
    assigned_to = relationship("User", back_populates="assigned_tickets", foreign_keys=[assigned_to_id])
    approvals = relationship("Approval", back_populates="ticket")

class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    approver_id = Column(Integer, ForeignKey("users.id"))
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.pending)
    comments = Column(Text, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="approvals")
    approver = relationship("User", back_populates="pending_approvals", foreign_keys=[approver_id])