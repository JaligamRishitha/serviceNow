from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
import hashlib

from database import SessionLocal, engine, Base
from models import User, Incident, ServiceCatalogItem, KnowledgeArticle, Ticket, Approval, IncidentStatus, IncidentPriority, TicketStatus, ApprovalStatus
from schemas import (
    UserCreate, UserResponse, IncidentCreate, IncidentResponse, 
    ServiceCatalogItemResponse, KnowledgeArticleCreate, KnowledgeArticleResponse, 
    TicketCreate, TicketUpdate, TicketResponse, ApprovalCreate, ApprovalUpdate, ApprovalResponse,
    Token
)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ServiceNow Clone API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3003"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")[:72]  # Truncate to 72 bytes for bcrypt
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Use a simpler password context to avoid bcrypt version issues
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == username).first()
    if user is None:
        raise credentials_exception
    return user

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/incidents/", response_model=list[IncidentResponse])
def read_incidents(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    incidents = db.query(Incident).offset(skip).limit(limit).all()
    return incidents

@app.post("/incidents/", response_model=IncidentResponse)
def create_incident(incident: IncidentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_incident = Incident(**incident.dict(), reporter_id=current_user.id)
    db.add(db_incident)
    db.commit()
    db.refresh(db_incident)
    return db_incident

@app.get("/debug/users")
def debug_users(db: Session = Depends(get_db)):
    """Debug endpoint to check users in database"""
    users = db.query(User).all()
    return [{"id": u.id, "email": u.email, "role": u.role} for u in users]

@app.get("/debug/tickets")
def debug_tickets(db: Session = Depends(get_db)):
    """Debug endpoint to check tickets in database"""
    tickets = db.query(Ticket).all()
    return [{"id": t.id, "ticket_number": t.ticket_number, "title": t.title, "status": t.status, "requester_id": t.requester_id} for t in tickets]

@app.get("/debug/approvals")
def debug_approvals(db: Session = Depends(get_db)):
    """Debug endpoint to check approvals in database"""
    approvals = db.query(Approval).all()
    return [{"id": a.id, "ticket_id": a.ticket_id, "approver_id": a.approver_id, "status": a.status} for a in approvals]

@app.get("/service-catalog/", response_model=list[ServiceCatalogItemResponse])
def read_service_catalog(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    items = db.query(ServiceCatalogItem).all()
    return items

# Knowledge Base endpoints
@app.get("/knowledge-base/", response_model=list[KnowledgeArticleResponse])
def read_knowledge_articles(
    skip: int = 0, 
    limit: int = 100, 
    category: str = None,
    search: str = None,
    db: Session = Depends(get_db)
):
    """Get knowledge base articles with optional filtering"""
    query = db.query(KnowledgeArticle)
    
    if category:
        query = query.filter(KnowledgeArticle.category == category)
    
    if search:
        query = query.filter(
            KnowledgeArticle.title.contains(search) | 
            KnowledgeArticle.content.contains(search) |
            KnowledgeArticle.tags.contains(search)
        )
    
    articles = query.offset(skip).limit(limit).all()
    return articles

@app.get("/knowledge-base/{article_id}", response_model=KnowledgeArticleResponse)
def read_knowledge_article(article_id: int, db: Session = Depends(get_db)):
    """Get a specific knowledge article and increment view count"""
    article = db.query(KnowledgeArticle).filter(KnowledgeArticle.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Increment view count
    article.views += 1
    db.commit()
    db.refresh(article)
    
    return article

@app.post("/knowledge-base/{article_id}/helpful")
def mark_article_helpful(article_id: int, db: Session = Depends(get_db)):
    """Mark an article as helpful"""
    article = db.query(KnowledgeArticle).filter(KnowledgeArticle.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    article.helpful_votes += 1
    db.commit()
    
    return {"message": "Thank you for your feedback!"}

@app.get("/knowledge-base/categories/")
def get_knowledge_categories(db: Session = Depends(get_db)):
    """Get all knowledge base categories"""
    categories = db.query(KnowledgeArticle.category).distinct().all()
    return [{"name": cat[0]} for cat in categories if cat[0]]

# Ticket Management endpoints
@app.post("/tickets/", response_model=TicketResponse)
def create_ticket(ticket: TicketCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create a new ticket"""
    import random
    import string
    
    # Generate unique ticket number
    ticket_number = f"TKT{random.randint(100000, 999999)}"
    
    db_ticket = Ticket(
        ticket_number=ticket_number,
        title=ticket.title,
        description=ticket.description,
        ticket_type=ticket.ticket_type,
        priority=ticket.priority,
        category=ticket.category,
        subcategory=ticket.subcategory,
        contact_number=ticket.contact_number,
        preferred_contact=ticket.preferred_contact,
        urgency=ticket.urgency,
        business_justification=ticket.business_justification,
        estimated_cost=ticket.estimated_cost,
        requester_id=current_user.id
    )
    
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    
    # Create approval if needed (for service requests over certain cost)
    if ticket.ticket_type == "service_request" and ticket.estimated_cost:
        try:
            cost_value = float(ticket.estimated_cost.replace('$', '').replace(',', ''))
            if cost_value > 500:  # Require approval for requests over $500
                # Find an admin user to approve
                admin_user = db.query(User).filter(User.role == "admin").first()
                if admin_user:
                    approval = Approval(
                        ticket_id=db_ticket.id,
                        approver_id=admin_user.id
                    )
                    db.add(approval)
                    db_ticket.status = "pending_approval"
                    db.commit()
        except:
            pass  # If cost parsing fails, continue without approval
    
    return db_ticket

@app.get("/tickets/", response_model=list[TicketResponse])
def read_tickets(
    skip: int = 0, 
    limit: int = 100, 
    status: str = None,
    ticket_type: str = None,
    my_tickets: bool = False,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Get tickets with optional filtering"""
    query = db.query(Ticket)
    
    if my_tickets:
        query = query.filter(Ticket.requester_id == current_user.id)
    
    if status:
        query = query.filter(Ticket.status == status)
    
    if ticket_type:
        query = query.filter(Ticket.ticket_type == ticket_type)
    
    tickets = query.offset(skip).limit(limit).all()
    
    # Add requester and assigned user names
    for ticket in tickets:
        if ticket.requester:
            ticket.requester_name = ticket.requester.full_name
        if ticket.assigned_to:
            ticket.assigned_to_name = ticket.assigned_to.full_name
    
    return tickets

@app.get("/tickets/{ticket_id}", response_model=TicketResponse)
def read_ticket(ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get a specific ticket"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Check if user can access this ticket
    if current_user.role == "user" and ticket.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Add names
    if ticket.requester:
        ticket.requester_name = ticket.requester.full_name
    if ticket.assigned_to:
        ticket.assigned_to_name = ticket.assigned_to.full_name
    
    return ticket

@app.put("/tickets/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: int, 
    ticket_update: TicketUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Update a ticket"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Check permissions
    if current_user.role == "user" and ticket.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update fields
    for field, value in ticket_update.dict(exclude_unset=True).items():
        setattr(ticket, field, value)
    
    db.commit()
    db.refresh(ticket)
    
    return ticket

# Approval endpoints
@app.get("/approvals/", response_model=list[ApprovalResponse])
def read_approvals(
    skip: int = 0, 
    limit: int = 100, 
    status: str = None,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Get approvals for current user"""
    query = db.query(Approval).filter(Approval.approver_id == current_user.id)
    
    if status:
        query = query.filter(Approval.status == status)
    
    approvals = query.offset(skip).limit(limit).all()
    
    # Add ticket and requester information
    for approval in approvals:
        if approval.ticket:
            approval.ticket_title = approval.ticket.title
            if approval.ticket.requester:
                approval.requester_name = approval.ticket.requester.full_name
    
    return approvals

@app.put("/approvals/{approval_id}", response_model=ApprovalResponse)
def update_approval(
    approval_id: int, 
    approval_update: ApprovalUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Approve or reject an approval request"""
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    # Check if current user is the approver
    if approval.approver_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update approval
    approval.status = approval_update.status
    approval.comments = approval_update.comments
    if approval_update.status in ["approved", "rejected"]:
        approval.approved_at = datetime.utcnow()
    
    # Update ticket status based on approval
    if approval.ticket:
        if approval_update.status == "approved":
            approval.ticket.status = "approved"
        elif approval_update.status == "rejected":
            approval.ticket.status = "rejected"
    
    db.commit()
    db.refresh(approval)
    
    return approval

@app.get("/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get optimized dashboard statistics in a single call"""
    try:
        # Get counts efficiently using database queries
        total_incidents = db.query(Incident).count()
        new_incidents = db.query(Incident).filter(Incident.status == IncidentStatus.new).count()
        in_progress_incidents = db.query(Incident).filter(Incident.status == IncidentStatus.in_progress).count()
        resolved_incidents = db.query(Incident).filter(Incident.status == IncidentStatus.resolved).count()
        
        total_tickets = db.query(Ticket).filter(Ticket.requester_id == current_user.id).count()
        open_tickets = db.query(Ticket).filter(
            Ticket.requester_id == current_user.id,
            Ticket.status.in_([TicketStatus.submitted, TicketStatus.pending_approval, TicketStatus.approved, TicketStatus.in_progress])
        ).count()
        resolved_tickets = db.query(Ticket).filter(
            Ticket.requester_id == current_user.id,
            Ticket.status.in_([TicketStatus.resolved, TicketStatus.closed])
        ).count()
        pending_approvals = db.query(Approval).filter(Approval.approver_id == current_user.id, Approval.status == ApprovalStatus.pending).count()
        
        # Get ticket status distribution
        ticket_status_counts = db.query(Ticket.status, func.count(Ticket.id)).filter(
            Ticket.requester_id == current_user.id
        ).group_by(Ticket.status).all()
        
        # Get priority distribution for both tickets and incidents
        ticket_priority_counts = db.query(Ticket.priority, func.count(Ticket.id)).group_by(Ticket.priority).all()
        incident_priority_counts = db.query(Incident.priority, func.count(Incident.id)).group_by(Incident.priority).all()
        
        # Combine priority counts
        priority_totals = {}
        for priority, count in ticket_priority_counts + incident_priority_counts:
            priority_totals[priority.value] = priority_totals.get(priority.value, 0) + count
        
        return {
            "stats": {
                "totalIncidents": total_incidents,
                "newIncidents": new_incidents,
                "inProgressIncidents": in_progress_incidents,
                "resolvedIncidents": resolved_incidents,
                "totalTickets": total_tickets,
                "openTickets": open_tickets,
                "pendingApprovals": pending_approvals,
                "resolvedTickets": resolved_tickets
            },
            "ticketTrends": [
                {"name": "New", "value": next((count for status, count in ticket_status_counts if status == TicketStatus.submitted), 0)},
                {"name": "Pending Approval", "value": next((count for status, count in ticket_status_counts if status == TicketStatus.pending_approval), 0)},
                {"name": "Approved", "value": next((count for status, count in ticket_status_counts if status == TicketStatus.approved), 0)},
                {"name": "In Progress", "value": next((count for status, count in ticket_status_counts if status == TicketStatus.in_progress), 0)},
                {"name": "Resolved", "value": next((count for status, count in ticket_status_counts if status == TicketStatus.resolved), 0)}
            ],
            "priorityDistribution": [
                {"name": "Critical", "value": priority_totals.get("critical", 0), "color": "#f44336"},
                {"name": "High", "value": priority_totals.get("high", 0), "color": "#ff9800"},
                {"name": "Medium", "value": priority_totals.get("medium", 0), "color": "#2196f3"},
                {"name": "Low", "value": priority_totals.get("low", 0), "color": "#4caf50"}
            ]
        }
    except Exception as e:
        print(f"Dashboard stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard statistics")

@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    try:
        # Create default admin user if not exists
        admin_user = db.query(User).filter(User.email == "admin@company.com").first()
        if not admin_user:
            admin_password = "admin123"
            hashed_password = get_password_hash(admin_password)
            admin_user = User(
                email="admin@company.com",
                full_name="System Administrator",
                role="admin",
                hashed_password=hashed_password
            )
            db.add(admin_user)
            db.commit()
            print(f"Created admin user: admin@company.com")
        
        # Create sample service catalog items
        if not db.query(ServiceCatalogItem).first():
            sample_items = [
                ServiceCatalogItem(name="New Laptop Request", description="Request a new laptop for employee", category="Hardware"),
                ServiceCatalogItem(name="Software Installation", description="Install new software on workstation", category="Software"),
                ServiceCatalogItem(name="Access Request", description="Request access to systems or applications", category="Access"),
            ]
            for item in sample_items:
                db.add(item)
            db.commit()
            print("Created sample service catalog items")
        
        # Create sample knowledge base articles
        if not db.query(KnowledgeArticle).first():
            sample_articles = [
                KnowledgeArticle(
                    title="How to Reset Your Password",
                    summary="Step-by-step guide to reset your password when you're locked out of your account.",
                    content="""# How to Reset Your Password

## Overview
If you've forgotten your password or are locked out of your account, follow these steps to reset it.

## Steps to Reset Password

### Method 1: Self-Service Password Reset
1. Go to the login page
2. Click "Forgot Password?" link
3. Enter your email address
4. Check your email for reset instructions
5. Click the reset link in the email
6. Create a new strong password

### Method 2: Contact IT Support
If self-service doesn't work:
1. Call IT Support: 02036602010 - Option 1
2. Provide your employee ID and full name
3. Answer security questions for verification
4. IT will reset your password temporarily
5. You'll be required to change it on first login

## Password Requirements
- Minimum 8 characters
- Must include uppercase and lowercase letters
- Must include at least one number
- Must include at least one special character
- Cannot be the same as your last 5 passwords

## Tips for Strong Passwords
- Use a passphrase with numbers and symbols
- Don't use personal information
- Consider using a password manager
- Enable two-factor authentication when available

## Need Help?
If you continue to have issues, contact the IT Service Desk at 02036602010 or submit a ticket through the portal.""",
                    category="Account Management",
                    tags="password,reset,login,account,security",
                    author_id=admin_user.id
                ),
                KnowledgeArticle(
                    title="Troubleshooting Slow Computer Performance",
                    summary="Common solutions for when your computer is running slowly or freezing.",
                    content="""# Troubleshooting Slow Computer Performance

## Overview
Is your computer running slowly? Here are the most common causes and solutions.

## Quick Fixes (Try These First)

### 1. Restart Your Computer
- Close all applications
- Click Start > Power > Restart
- Wait for complete restart
- This clears memory and temporary files

### 2. Check Available Storage
- Open File Explorer
- Click "This PC"
- Check if C: drive is more than 85% full
- If full, delete unnecessary files or contact IT

### 3. Close Unnecessary Programs
- Press Ctrl + Shift + Esc to open Task Manager
- Click "More details" if needed
- Look for programs using high CPU or Memory
- Right-click and "End task" for unnecessary programs

## Advanced Solutions

### Check for Malware
1. Run Windows Defender full scan
2. Go to Settings > Update & Security > Windows Security
3. Click "Virus & threat protection"
4. Run "Quick scan" or "Scan options" > "Full scan"

### Update Windows
1. Go to Settings > Update & Security
2. Click "Check for updates"
3. Install any available updates
4. Restart when prompted

### Disable Startup Programs
1. Press Ctrl + Shift + Esc for Task Manager
2. Click "Startup" tab
3. Right-click programs you don't need at startup
4. Select "Disable"

## When to Contact IT
Contact IT Support if:
- Computer is still slow after trying above steps
- You get error messages
- Programs crash frequently
- Computer takes more than 5 minutes to start

## Prevention Tips
- Restart your computer at least once a week
- Keep desktop clean (fewer than 20 icons)
- Don't install unauthorized software
- Run Windows updates regularly
- Use cloud storage for large files

## Contact Information
- IT Service Desk: 02036602010
- Email: itsupport@company.com
- Submit ticket through ServiceNow portal""",
                    category="Hardware & Performance",
                    tags="slow,performance,computer,troubleshooting,speed,memory",
                    author_id=admin_user.id
                ),
                KnowledgeArticle(
                    title="Microsoft Outlook Email Issues",
                    summary="Solutions for common Outlook problems including connection issues, missing emails, and sync problems.",
                    content="""# Microsoft Outlook Email Issues

## Overview
Common Outlook problems and their solutions.

## Connection Issues

### Outlook Won't Connect to Server
1. Check internet connection
2. Restart Outlook completely
3. Check if other Office apps work
4. Try Outlook Web App (OWA) in browser
5. If OWA works but Outlook doesn't, contact IT

### "Cannot Connect to Server" Error
1. Go to File > Account Settings > Account Settings
2. Select your email account
3. Click "Test Account Settings"
4. If test fails, contact IT for server settings

## Missing Emails

### Emails Not Appearing in Inbox
1. Check Junk/Spam folder
2. Check other folders (Sent, Drafts, etc.)
3. Use Search function (Ctrl + E)
4. Check if rules are moving emails automatically
5. Go to File > Options > Mail > Rules to review

### Sent Emails Not in Sent Folder
1. Go to File > Options > Mail
2. Check "Save copies of messages in Sent Items folder"
3. Click OK and restart Outlook

## Sync Issues

### Calendar/Contacts Not Syncing
1. Go to Send/Receive tab
2. Click "Send/Receive All Folders"
3. Check File > Account Settings for sync settings
4. If using mobile, check mobile sync settings

### Outlook Freezing or Crashing
1. Start Outlook in Safe Mode:
   - Press Windows + R
   - Type: outlook /safe
   - Press Enter
2. If it works in Safe Mode, disable add-ins:
   - Go to File > Options > Add-ins
   - Disable all add-ins
   - Restart normally

## Large Mailbox Issues

### Mailbox Full Warning
1. Delete old emails (older than 1 year)
2. Empty Deleted Items folder
3. Archive important emails to PST file
4. Contact IT if you need more storage

### Slow Outlook Performance
1. Compact your mailbox
2. Reduce number of folders
3. Archive old emails
4. Disable unnecessary add-ins

## Mobile Device Setup

### Setting Up Email on Phone/Tablet
1. Use Outlook mobile app (recommended)
2. Or use built-in email app with these settings:
   - Server: outlook.office365.com
   - Port: 993 (IMAP) or 995 (POP)
   - Security: SSL/TLS
3. Contact IT if you need specific server settings

## When to Contact IT
- Cannot access email for more than 30 minutes
- Getting authentication errors
- Need to set up email on new device
- Mailbox corruption errors
- Need email forwarding or distribution lists

## Quick Reference
- **Restart Outlook**: Close completely, wait 30 seconds, reopen
- **Safe Mode**: Windows + R, type "outlook /safe"
- **Test Connection**: File > Account Settings > Test Account Settings
- **Search All Folders**: Ctrl + E
- **IT Support**: 02036602010""",
                    category="Email & Communication",
                    tags="outlook,email,connection,sync,missing,mobile,setup",
                    author_id=admin_user.id
                ),
                KnowledgeArticle(
                    title="VPN Connection Problems",
                    summary="How to troubleshoot and fix VPN connection issues for remote work.",
                    content="""# VPN Connection Problems

## Overview
Virtual Private Network (VPN) allows secure remote access to company resources. Here's how to fix common issues.

## Cannot Connect to VPN

### Check Internet Connection First
1. Ensure you have stable internet
2. Try browsing to any website
3. If no internet, fix that first before VPN

### VPN Client Won't Start
1. Right-click VPN client icon
2. Select "Run as Administrator"
3. If still fails, restart computer
4. Try connecting again

### Authentication Failures
1. Double-check username and password
2. Ensure Caps Lock is OFF
3. Try typing password in notepad first, then copy/paste
4. If using token/2FA, ensure code is current
5. Contact IT if credentials are correct but still failing

## Slow VPN Performance

### Speed Issues
1. Try different VPN server location (if available)
2. Close unnecessary applications
3. Pause cloud backups (OneDrive, Google Drive)
4. Use wired connection instead of WiFi if possible

### Frequent Disconnections
1. Check power settings - disable "USB selective suspend"
2. Update VPN client software
3. Try different network (mobile hotspot test)
4. Contact IT if problem persists

## Specific Error Messages

### "The remote connection was denied"
- Check if your account is enabled for VPN access
- Contact IT to verify VPN permissions

### "Error 800: Unable to establish connection"
- Firewall or router blocking VPN
- Try from different network location
- Contact IT for firewall configuration

### "Error 691: Access denied"
- Username/password incorrect
- Account may be locked or expired
- Contact IT for account status

## Mobile VPN Setup

### iPhone/iPad
1. Go to Settings > General > VPN
2. Add VPN Configuration
3. Enter server details provided by IT
4. Test connection

### Android
1. Go to Settings > Network & Internet > VPN
2. Add VPN profile
3. Enter server details provided by IT
4. Test connection

## Best Practices

### Security Tips
- Always disconnect VPN when not needed
- Don't share VPN credentials
- Use company-approved VPN client only
- Report suspicious activity immediately

### Performance Tips
- Connect to nearest server location
- Close streaming services while on VPN
- Use VPN only when accessing company resources
- Restart VPN connection if slow

## Troubleshooting Steps

### Basic Troubleshooting
1. Disconnect and reconnect VPN
2. Restart VPN client application
3. Restart computer
4. Try different network connection
5. Update VPN client software

### Advanced Troubleshooting
1. Flush DNS: Open Command Prompt as admin, type "ipconfig /flushdns"
2. Reset network settings
3. Temporarily disable antivirus/firewall
4. Check Windows updates

## When to Contact IT
- Cannot connect after trying basic steps
- Need VPN access for new employee
- Frequent disconnections affecting work
- Need VPN on new device
- Suspicious VPN activity

## Contact Information
- **IT Helpdesk**: 02036602010
- **Emergency After Hours**: 02036602010 - Option 1
- **Email**: itsupport@company.com

## Quick Commands
- **Windows**: Windows + R, type "ncpa.cpl" to see network connections
- **Check IP**: Open Command Prompt, type "ipconfig"
- **Test Connection**: ping google.com""",
                    category="Network & Connectivity",
                    tags="vpn,remote,connection,network,authentication,slow,disconnection",
                    author_id=admin_user.id
                ),
                KnowledgeArticle(
                    title="Printer Setup and Troubleshooting",
                    summary="How to set up printers and resolve common printing issues.",
                    content="""# Printer Setup and Troubleshooting

## Overview
Guide for setting up network printers and solving common printing problems.

## Setting Up Network Printers

### Windows 10/11 Setup
1. Go to Settings > Devices > Printers & scanners
2. Click "Add a printer or scanner"
3. Wait for Windows to find network printers
4. Select your printer from the list
5. Follow installation prompts
6. Print test page to verify

### Manual Network Printer Setup
If printer not found automatically:
1. Click "The printer that I want isn't listed"
2. Select "Add a printer using TCP/IP address"
3. Enter printer IP address (get from IT)
4. Follow driver installation prompts

## Common Printing Problems

### Printer Not Responding
1. Check if printer is powered on
2. Verify network cable connections
3. Try printing from another computer
4. Restart print spooler service:
   - Press Windows + R
   - Type "services.msc"
   - Find "Print Spooler"
   - Right-click > Restart

### Print Jobs Stuck in Queue
1. Open Settings > Devices > Printers & scanners
2. Click on your printer
3. Click "Open queue"
4. Select stuck jobs and delete them
5. Try printing again

### Poor Print Quality

#### Faded or Light Printing
- Check toner/ink levels
- Run printer cleaning cycle
- Replace toner cartridge if low
- Contact IT for maintenance

#### Streaks or Lines on Paper
- Clean printer heads (use printer utility)
- Check for damaged toner cartridge
- Clean paper path
- Contact IT if problem persists

#### Paper Jams
1. Turn off printer
2. Open all printer doors/trays
3. Gently remove jammed paper (don't tear)
4. Check for small paper pieces
5. Close all doors and turn on printer
6. Try printing again

## Mobile Printing

### Print from iPhone/iPad
1. Ensure device on same WiFi as printer
2. Open document/photo to print
3. Tap Share button
4. Select Print
5. Choose printer and settings
6. Tap Print

### Print from Android
1. Install printer manufacturer's app
2. Or use Google Cloud Print (if supported)
3. Open document to print
4. Tap menu > Print
5. Select printer and print

## Printer Driver Issues

### Driver Not Found
1. Go to printer manufacturer's website
2. Download latest driver for your model
3. Run installer as administrator
4. Restart computer after installation

### Driver Conflicts
1. Uninstall old printer drivers
2. Go to Device Manager
3. Find printer under "Printers"
4. Right-click > Uninstall device
5. Reinstall with latest driver

## Network Printer Locations

### Common Office Printers
- **Reception Area**: HP LaserJet Pro (IP: 192.168.1.101)
- **Marketing Floor**: Canon ImageRunner (IP: 192.168.1.102)
- **Finance Department**: Brother MFC (IP: 192.168.1.103)
- **IT Department**: Xerox WorkCentre (IP: 192.168.1.104)

*Note: Contact IT for current printer locations and IP addresses*

## Printing Policies

### Color Printing
- Color printing requires manager approval
- Use color only for client presentations
- Default to black and white for internal documents

### Large Print Jobs
- Jobs over 50 pages require IT approval
- Consider digital alternatives first
- Use duplex (double-sided) printing when possible

## Troubleshooting Checklist

### Before Calling IT
- [ ] Printer powered on and connected
- [ ] Computer connected to network
- [ ] Tried printing from another application
- [ ] Checked printer queue for stuck jobs
- [ ] Restarted computer
- [ ] Checked toner/ink levels

### Information to Provide IT
- Printer model and location
- Error messages (exact text)
- What you were trying to print
- When the problem started
- If others have same issue

## Maintenance Tips

### Regular Maintenance
- Keep printer area clean and dust-free
- Don't touch toner cartridges unnecessarily
- Use recommended paper types
- Report low toner levels promptly

### Paper Guidelines
- Use standard 20lb copy paper
- Don't overfill paper trays
- Store paper in dry location
- Remove paper clips and staples

## When to Contact IT
- Printer completely unresponsive
- Network connectivity issues
- Need new printer installation
- Toner replacement needed
- Hardware malfunctions
- Print quality issues persist

## Contact Information
- **IT Support**: 02036602010
- **Printer Supplies**: ext. 1234
- **Maintenance Requests**: Submit ServiceNow ticket""",
                    category="Hardware & Peripherals",
                    tags="printer,printing,setup,network,driver,paper,jam,quality,mobile",
                    author_id=admin_user.id
                ),
                KnowledgeArticle(
                    title="Microsoft Teams Meeting Issues",
                    summary="Troubleshooting guide for Microsoft Teams audio, video, and connection problems.",
                    content="""# Microsoft Teams Meeting Issues

## Overview
Solutions for common Microsoft Teams problems during meetings and calls.

## Audio Issues

### Can't Hear Others
1. Check computer volume (not muted)
2. In Teams, click device settings (gear icon)
3. Test speaker under "Audio devices"
4. Try different audio device if available
5. Leave and rejoin meeting

### Others Can't Hear You
1. Check if microphone is muted in Teams
2. Click microphone icon to unmute
3. Check Windows microphone permissions:
   - Settings > Privacy > Microphone
   - Allow Teams access
4. Test microphone in Teams settings
5. Try different microphone if available

### Echo or Feedback
1. Use headphones instead of speakers
2. Ask others to mute when not speaking
3. Move away from speakers
4. Check for multiple devices connected
5. Use "Reduce background noise" in Teams settings

## Video Issues

### Camera Not Working
1. Check if camera is enabled in Teams
2. Click camera icon to turn on video
3. Check Windows camera permissions:
   - Settings > Privacy > Camera
   - Allow Teams access
4. Close other apps using camera (Skype, Zoom)
5. Restart Teams application

### Poor Video Quality
1. Check internet connection speed
2. Close unnecessary applications
3. Move closer to WiFi router
4. Turn off video of other participants
5. Use "Optimize for video" in meeting options

### Camera Shows Wrong Image
1. Check camera settings in Teams
2. Go to Settings > Devices > Camera
3. Select correct camera device
4. Test camera preview
5. Restart Teams if needed

## Connection Issues

### Can't Join Meeting
1. Check internet connection
2. Try joining via web browser instead of app
3. Use phone dial-in option as backup
4. Clear Teams cache:
   - Close Teams completely
   - Press Windows + R
   - Type: %appdata%\\Microsoft\\Teams
   - Delete contents of folder
   - Restart Teams

### Meeting Keeps Disconnecting
1. Check WiFi signal strength
2. Close bandwidth-heavy applications
3. Use ethernet cable instead of WiFi
4. Restart router/modem
5. Contact IT if problem persists

### Screen Sharing Not Working
1. Update Teams to latest version
2. Try sharing specific application instead of desktop
3. Check if admin permissions required
4. Close unnecessary applications
5. Restart Teams

## Mobile Teams Issues

### Teams App Problems on Phone
1. Update Teams app from app store
2. Check mobile data/WiFi connection
3. Restart Teams app
4. Restart phone if needed
5. Reinstall Teams app if problems persist

### Can't Access Files on Mobile
1. Ensure signed in with company account
2. Check internet connection
3. Try accessing via web browser
4. Sync files in desktop app first
5. Contact IT for file permissions

## Meeting Best Practices

### Before the Meeting
- Test audio/video 5 minutes early
- Join from quiet location
- Have phone backup ready
- Close unnecessary applications
- Charge device or plug in power

### During the Meeting
- Mute when not speaking
- Use "Raise hand" feature for questions
- Share specific applications, not entire screen
- Use chat for questions if audio issues
- Take notes in Teams or OneNote

## Performance Optimization

### Improve Teams Performance
1. Close other video applications
2. Update Teams regularly
3. Restart Teams daily
4. Clear Teams cache weekly
5. Use desktop app instead of web browser

### Bandwidth Management
- Turn off video when not needed
- Limit other internet usage during calls
- Use phone audio for large meetings
- Close cloud sync applications
- Ask others to mute video if connection poor

## Troubleshooting Steps

### Quick Fixes
1. Mute/unmute microphone
2. Turn video off and on
3. Leave and rejoin meeting
4. Restart Teams application
5. Check device settings

### Advanced Troubleshooting
1. Update Teams application
2. Clear Teams cache
3. Reset network settings
4. Update audio/video drivers
5. Contact IT support

## Common Error Messages

### "We're sorry - we've run into an issue"
- Clear Teams cache
- Restart application
- Try web version
- Contact IT if persists

### "Couldn't connect to media"
- Check firewall settings
- Try different network
- Use phone dial-in
- Contact IT for network configuration

## When to Contact IT
- Persistent audio/video issues
- Cannot join any meetings
- Teams won't start or crashes
- Need Teams installation on new device
- Network connectivity problems
- Account access issues

## Alternative Solutions
- Use phone dial-in for audio
- Join via web browser
- Use mobile Teams app as backup
- Switch to different meeting platform if approved
- Record meeting for those who can't join

## Contact Information
- **IT Helpdesk**: 02036602010
- **Teams Support**: Submit ServiceNow ticket
- **Emergency Meeting Support**: Call IT during business hours

## Quick Reference
- **Mute/Unmute**: Ctrl + Shift + M
- **Video On/Off**: Ctrl + Shift + O
- **Share Screen**: Ctrl + Shift + E
- **Raise Hand**: Ctrl + Shift + K
- **Leave Meeting**: Ctrl + Shift + H""",
                    category="Software & Applications",
                    tags="teams,meeting,audio,video,microphone,camera,connection,screen sharing",
                    author_id=admin_user.id
                )
            ]
            
            for article in sample_articles:
                db.add(article)
            db.commit()
            print("Created sample knowledge base articles")
        
        # Create sample tickets
        if not db.query(Ticket).first():
            import random
            sample_tickets = [
                Ticket(
                    ticket_number=f"TKT{random.randint(100000, 999999)}",
                    title="Password Reset Request",
                    description="I forgot my password and cannot access my email account. Please help me reset it.",
                    ticket_type="incident",
                    status="submitted",
                    priority="medium",
                    category="Account Management",
                    subcategory="Password Reset",
                    requester_id=admin_user.id,
                    contact_number="555-0123",
                    preferred_contact="email"
                ),
                Ticket(
                    ticket_number=f"TKT{random.randint(100000, 999999)}",
                    title="New Laptop Request",
                    description="I need a new laptop for my work. My current one is very slow and affecting productivity.",
                    ticket_type="service_request",
                    status="pending_approval",
                    priority="medium",
                    category="Hardware",
                    subcategory="New Equipment",
                    requester_id=admin_user.id,
                    business_justification="Current laptop is 5 years old and cannot run required software efficiently",
                    estimated_cost="$1200"
                ),
                Ticket(
                    ticket_number=f"TKT{random.randint(100000, 999999)}",
                    title="Printer Not Working",
                    description="The printer on the 3rd floor is not responding. It shows an error message and won't print anything.",
                    ticket_type="incident",
                    status="in_progress",
                    priority="high",
                    category="Hardware",
                    subcategory="Printer Issues",
                    requester_id=admin_user.id,
                    contact_number="555-0124"
                ),
                Ticket(
                    ticket_number=f"TKT{random.randint(100000, 999999)}",
                    title="Software Installation - Adobe Creative Suite",
                    description="I need Adobe Creative Suite installed on my workstation for design work.",
                    ticket_type="service_request",
                    status="approved",
                    priority="low",
                    category="Software",
                    subcategory="Installation",
                    requester_id=admin_user.id,
                    business_justification="Required for marketing materials creation",
                    estimated_cost="$600"
                ),
                Ticket(
                    ticket_number=f"TKT{random.randint(100000, 999999)}",
                    title="VPN Connection Issues",
                    description="I cannot connect to the company VPN from home. Getting authentication errors.",
                    ticket_type="incident",
                    status="resolved",
                    priority="medium",
                    category="Network",
                    subcategory="VPN",
                    requester_id=admin_user.id,
                    resolution_notes="Reset VPN credentials and updated client software. Issue resolved."
                )
            ]
            
            for ticket in sample_tickets:
                db.add(ticket)
            db.commit()
            
            # Create sample approvals for tickets that need approval
            approval_tickets = [t for t in sample_tickets if t.status == "pending_approval"]
            for ticket in approval_tickets:
                approval = Approval(
                    ticket_id=ticket.id,
                    approver_id=admin_user.id,
                    status="pending"
                )
                db.add(approval)
            
            db.commit()
            print("Created sample tickets and approvals")
    except Exception as e:
        print(f"Startup error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)