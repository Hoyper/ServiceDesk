from email import message_from_bytes
from email.header import decode_header
from email.mime.text import MIMEText
from imaplib import IMAP4_SSL
from smtplib import SMTP

from celery import Celery
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Message, Ticket, TicketStatus, User
from app.db.session import get_db

celery_app = Celery("tasks", broker="redis://localhost:6379/0")


def decode_mime_header(header_value):
    decoded_parts = decode_header(header_value)
    result = ""
    for part, encoding in decoded_parts:
        try:
            if isinstance(part, bytes):
                result += part.decode(encoding or "utf-8", errors="replace")
            else:
                result += part
        except (LookupError, UnicodeDecodeError):
            result += (
                part.decode("utf-8", errors="replace")
                if isinstance(part, bytes)
                else part
            )
    return result


@celery_app.task
def send_email(
    to_email: str,
    subject: str,
    body: str,
    smt_server: str,
    smt_port: int,
    smt_user: str,
    smt_password: str,
):
    with SMTP(smt_server, smt_port) as server:
        server.starttls()
        server.login(smt_user, smt_password)
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = smt_user
        msg["To"] = to_email
        server.sendmail(smt_user, to_email, msg.as_string())


def user_send_email(to_email: str, subject: str, body: str):
    smt_server = settings.SMTP_SERVER
    smt_port = settings.SMTP_PORT
    smt_user = settings.SMTP_USER
    smt_password = settings.SMTP_USER_PASSWORD
    send_email.delay(
        to_email, subject, body, smt_server, smt_port, smt_user, smt_password
    )


def operator_send_email(to_email: str, subject: str, body: str):
    smt_server = settings.SMTP_SERVER
    smt_port = settings.SMTP_PORT
    smt_user = settings.SMTP_OPERATOR
    smt_password = settings.SMTP_OPERATOR_PASSWORD
    send_email.delay(
        to_email, subject, body, smt_server, smt_port, smt_user, smt_password
    )

    with next(get_db()) as db:
        ticket = get_ticket(user_email=to_email, subject=subject, db=db)

        if ticket:
            add_message_to_ticket(
                ticket_id=ticket.id, sender=smt_user, content=body, db=db
            )
            operator = get_operator_by_email(email=smt_user, db=db)
            if operator:
                put_ticket(ticket_id=ticket.id, operator_id=operator.id, db=db)


@celery_app.task
def check_operator_email():
    with IMAP4_SSL(settings.IMAP_SERVER) as mail:
        mail.login(settings.SMTP_OPERATOR, settings.SMTP_OPERATOR_PASSWORD)
        mail.select("inbox")
        status, messages = mail.search(None, "UNSEEN")
        for num in reversed(messages[0].split()):
            _, msg_data = mail.fetch(num, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    email_message = message_from_bytes(response_part[1])
                    raw_sender = email_message.get("From")
                    sender = decode_mime_header(raw_sender)
                    raw_subject = email_message.get("Subject")
                    subject = decode_mime_header(raw_subject)
                    body = email_message.get_payload(decode=True).decode(
                        email_message.get_content_charset()
                    )

                    with next(get_db()) as db:
                        existing_ticket = get_ticket(
                            user_email=sender, subject=subject, db=db
                        )

                        if not existing_ticket:
                            new_ticket = add_ticket(
                                user_email=sender, subject=subject, db=db
                            )
                            add_message_to_ticket(
                                ticket_id=new_ticket.id,
                                sender=sender,
                                content=body,
                                db=db,
                            )

                            operator_send_email(
                                to_email=sender,
                                subject=subject,
                                body="Здравствуйте! Ваше обращение принято в работу. Мы скоро с вами свяжемся.",
                            )
                        else:
                            add_message_to_ticket(
                                ticket_id=existing_ticket.id,
                                sender=sender,
                                content=body,
                                db=db,
                            )


def get_ticket(user_email: str, subject: str, db: Session):
    result = db.execute(
        select(Ticket).filter(
            Ticket.user_email == user_email, Ticket.subject == subject
        )
    )
    ticket = result.scalars().first()
    if ticket is None or ticket.status == TicketStatus.CLOSED:
        return None

    return ticket


def put_ticket(ticket_id: int, operator_id: int, db: Session):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    ticket.operator_id = operator_id
    db.commit()
    db.refresh(ticket)

    return ticket


def get_operator_by_email(email: str, db: Session):
    operator = db.query(User).filter(User.email == email).first()

    if not operator:
        return None

    return operator


def operator_close_ticket(ticket_id: int, db: Session):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        return {"Error": "Ticket not found"}
    ticket.status = TicketStatus.CLOSED
    db.commit()
    db.refresh(ticket)
    smt_server = settings.SMTP_SERVER
    smt_port = settings.SMTP_PORT
    smt_user = settings.SMTP_OPERATOR
    smt_password = settings.SMTP_OPERATOR_PASSWORD
    body = "Ваша проблема была решена"
    send_email.delay(
        ticket.user_email,
        ticket.subject,
        body,
        smt_server,
        smt_port,
        smt_user,
        smt_password,
    )
    return ticket


def add_ticket(user_email: str, subject: str, db: Session):
    new_ticket = Ticket(
        user_email=user_email, subject=subject, status=TicketStatus.OPEN
    )
    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)

    return new_ticket


def add_message_to_ticket(ticket_id: int, sender: str, content: str, db: Session):
    new_message = Message(ticket_id=ticket_id, sender=sender, content=content)
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return new_message


def get_all_tickets(
    db: Session, status: str | None = None, order_by: str | None = None
):
    query = select(Ticket)

    if status:
        query = query.where(Ticket.status == status)

    if order_by == "desc":
        query = query.order_by(Ticket.created_at.desc())
    else:
        query = query.order_by(Ticket.created_at.asc())

    result = db.execute(query)
    tickets = result.scalars().all()

    return tickets


def add_operator(db: Session, email: str, name: str):
    result = db.execute(select(User).filter(User.email == email))
    existing_user = result.scalars().first()

    if existing_user:
        return {"error": "User with this email already exists"}

    new_user = User(email=email, name=name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
