import fastapi
from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.schemas import TicketCreate
from app.db.session import get_db
from app.services.main_service import add_ticket, get_all_tickets

router = fastapi.APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("/add_ticket")
def send_message(request: TicketCreate, db: Session = Depends(get_db)):
    result = add_ticket(request.user_email, request.subject, db)
    return result


@router.get("/get_tickets")
def get_tickets(
    db: Session = Depends(get_db),
    status: str | None = None,
    order_by: str | None = None,
):
    result = get_all_tickets(db, status, order_by)
    return result
