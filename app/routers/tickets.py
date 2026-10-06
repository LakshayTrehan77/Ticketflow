from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_agent
from app.metrics import TICKETS_CREATED
from app.models import Ticket, User
from app.schemas import (
    Category,
    Priority,
    Status,
    TicketCreate,
    TicketOut,
    TicketPage,
    TicketUpdate,
)
from app.services import ticket_service
from app.services.cache import Cache, get_cache
from app.services.classifier import TicketClassifier, get_classifier

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    classifier: TicketClassifier = Depends(get_classifier),
    cache: Cache = Depends(get_cache),
):
    ticket = ticket_service.create_ticket(db, user, payload, classifier)
    cache.delete(ticket_service.STATS_CACHE_KEY)
    TICKETS_CREATED.labels(category=ticket.category, priority=ticket.priority).inc()
    return ticket


@router.get("", response_model=TicketPage)
def list_tickets(
    status_filter: Status | None = Query(None, alias="status"),
    category: Category | None = None,
    priority: Priority | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    items, total = ticket_service.list_tickets(
        db,
        user,
        status=status_filter.value if status_filter else None,
        category=category.value if category else None,
        priority=priority.value if priority else None,
        page=page,
        size=size,
    )
    return TicketPage(items=items, total=total, page=page, size=size)


# this has to stay above /{ticket_id} or "stats" would be read as an id
@router.get("/stats")
def stats(
    db: Session = Depends(get_db),
    _: User = Depends(require_agent),
    cache: Cache = Depends(get_cache),
):
    cached = cache.get(ticket_service.STATS_CACHE_KEY)
    if cached is not None:
        return cached

    result = ticket_service.ticket_stats(db)
    cache.set(ticket_service.STATS_CACHE_KEY, result, ttl=30)
    return result


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = ticket_service.get_ticket(db, user, ticket_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    return ticket


@router.patch("/{ticket_id}", response_model=TicketOut)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_agent),
    cache: Cache = Depends(get_cache),
):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")

    if payload.assigned_to is not None:
        assignee = db.get(User, payload.assigned_to)
        if assignee is None or assignee.role != "agent":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "assigned_to must be an agent")

    updated = ticket_service.update_ticket(db, ticket, payload)
    cache.delete(ticket_service.STATS_CACHE_KEY)
    return updated
