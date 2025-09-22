from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
