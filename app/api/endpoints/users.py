import fastapi
from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.schemas import MailResponse, OperatorCreate, SendMailRequest
from app.db.session import get_db
from app.services.main_service import (add_operator, operator_close_ticket,
                                       operator_send_email, user_send_email)

router = fastapi.APIRouter(prefix="/users", tags=["Users"])


@router.post("/send_message", response_model=MailResponse)
def send_message(request: SendMailRequest):
    user_send_email(request.to_email, request.subject, request.body)
    return MailResponse(message="Mail has been sent")


@router.post("/create_operator")
def create_operator(request: OperatorCreate, db: Session = Depends(get_db)):
    result = add_operator(db, request.email, request.name)
    return result


@router.post("/operator_send_message", response_model=MailResponse)
def operator_send_mail(request: SendMailRequest):
    operator_send_email(request.to_email, request.subject, request.body)
    return MailResponse(message="Operator has been sent")


@router.post("/close_ticket")
def close_ticket(ticket_id: int, db: Session = Depends(get_db)):
    result = operator_close_ticket(ticket_id, db)
    return result
