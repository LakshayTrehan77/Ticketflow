from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Ticket, User
from app.schemas import TicketCreate, TicketUpdate
from app.services.classifier import TicketClassifier

STATS_CACHE_KEY = "ticket_stats"


def create_ticket(
    db: Session, user: User, data: TicketCreate, classifier: TicketClassifier
) -> Ticket:
    # classify on title + description together, the title alone is often too short
    prediction = classifier.predict(f"{data.title}. {data.description}")

    ticket = Ticket(
        title=data.title,
        description=data.description,
        category=prediction.category,
        priority=prediction.priority,
        confidence=prediction.confidence,
        created_by=user.id,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def list_tickets(
    db: Session,
    user: User,
    status: str | None,
    category: str | None,
    priority: str | None,
    page: int,
    size: int,
) -> tuple[list[Ticket], int]:
    query = select(Ticket)
    if user.role != "agent":
        query = query.where(Ticket.created_by == user.id)
    if status:
        query = query.where(Ticket.status == status)
    if category:
        query = query.where(Ticket.category == category)
    if priority:
        query = query.where(Ticket.priority == priority)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(Ticket.created_at.desc(), Ticket.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return list(items), total


def get_ticket(db: Session, user: User, ticket_id: int) -> Ticket | None:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        return None
    if user.role != "agent" and ticket.created_by != user.id:
        return None
    return ticket


def update_ticket(db: Session, ticket: Ticket, changes: TicketUpdate) -> Ticket:
    for field, value in changes.model_dump(exclude_unset=True).items():
        # enums are stored as plain strings
        setattr(ticket, field, value.value if hasattr(value, "value") else value)
    db.commit()
    db.refresh(ticket)
    return ticket


def ticket_stats(db: Session) -> dict:
    def count_by(column) -> dict[str, int]:
        rows = db.execute(select(column, func.count()).group_by(column)).all()
        return {key: count for key, count in rows}

    return {
        "total": db.scalar(select(func.count()).select_from(Ticket)) or 0,
        "by_status": count_by(Ticket.status),
        "by_category": count_by(Ticket.category),
        "by_priority": count_by(Ticket.priority),
    }
