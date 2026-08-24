"""Autonomous Feedback Loop Service for Historical Administrator Review Memory."""

import logging
from typing import Iterable, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.database import Base, SessionLocal, engine
from src.models.feedback import Feedback
from src.schemas.feedback import FeedbackCreate

logger = logging.getLogger(__name__)


def init_feedback_db() -> None:
    """Ensure feedback table exists in local database."""
    Base.metadata.create_all(bind=engine)


def record_feedback(
    feedback: FeedbackCreate,
    db: Optional[Session] = None,
) -> Feedback:
    """Record administrator feedback for an incident in the local database."""
    init_feedback_db()
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        record = Feedback(
            incident_id=feedback.incident_id,
            is_false_positive=feedback.is_false_positive,
            admin_notes=feedback.admin_notes,
            source_ip=feedback.source_ip,
            target_user=feedback.target_user,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    finally:
        if should_close:
            db.close()


def get_feedback_for_ips_or_users(
    ips: Optional[Iterable[str]] = None,
    users: Optional[Iterable[str]] = None,
    db: Optional[Session] = None,
) -> List[Feedback]:
    """
    Retrieve historical feedback matching any of the given source IPs or target users.
    Only returns false positive annotations by default to suppress recurring false alarms.
    """
    init_feedback_db()
    clean_ips = [ip.strip() for ip in ips or [] if ip and ip.strip()]
    clean_users = [u.strip() for u in users or [] if u and u.strip()]

    if not clean_ips and not clean_users:
        return []

    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        clauses = []
        if clean_ips:
            clauses.append(Feedback.source_ip.in_(clean_ips))
        if clean_users:
            clauses.append(Feedback.target_user.in_(clean_users))

        records = (
            db.query(Feedback)
            .filter(Feedback.is_false_positive.is_(True))
            .filter(or_(*clauses))
            .order_by(Feedback.created_at.desc())
            .all()
        )
        return records
    except Exception as e:
        logger.warning(f"Error querying feedback database: {e}")
        return []
    finally:
        if should_close:
            db.close()


def get_all_feedback(limit: int = 50, db: Optional[Session] = None) -> List[Feedback]:
    """Retrieve all historical administrator feedback."""
    init_feedback_db()
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        return (
            db.query(Feedback)
            .order_by(Feedback.created_at.desc())
            .limit(limit)
            .all()
        )
    finally:
        if should_close:
            db.close()


def build_feedback_context_note(feedback_list: List[Feedback]) -> str:
    """
    Format historical administrator feedback notes for dynamic system prompt injection.
    """
    if not feedback_list:
        return ""

    notes: List[str] = []
    seen: set[str] = set()

    for fb in feedback_list:
        if fb.source_ip and fb.source_ip not in seen:
            notes.append(
                f"Note: The administrator previously marked similar activity from IP {fb.source_ip} "
                f"as a False Positive because: {fb.admin_notes}. Take this into account."
            )
            seen.add(fb.source_ip)
        elif fb.target_user and fb.target_user not in seen:
            notes.append(
                f"Note: The administrator previously marked similar activity targeting user {fb.target_user} "
                f"as a False Positive because: {fb.admin_notes}. Take this into account."
            )
            seen.add(fb.target_user)
        elif fb.incident_id and fb.incident_id not in seen:
            notes.append(
                f"Note: The administrator previously marked incident {fb.incident_id} "
                f"as a False Positive because: {fb.admin_notes}. Take this into account."
            )
            seen.add(fb.incident_id)

    return "\n".join(notes)
