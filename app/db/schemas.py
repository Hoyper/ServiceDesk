from pydantic import BaseModel, EmailStr


class SendMailRequest(BaseModel):
    to_email: EmailStr
    subject: str
    body: str


class MailResponse(BaseModel):
    message: str


class TicketCreate(BaseModel):
    user_email: EmailStr
    subject: str


class OperatorCreate(BaseModel):
    email: EmailStr
    name: str
