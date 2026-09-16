from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException
from fastapi.responses import Response

from app.models.user import User
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings

class AuthService:
    @staticmethod
    def register(db: Session, payload):
        if db.query(User).filter(User.username == payload.username).first():
            raise HTTPException(status_code=400, detail="Username already registered")
        if db.query(User).filter(User.email == payload.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        user = User(
            username=payload.username,
            email=payload.email,
            password=hash_password(payload.password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def login(db: Session, payload, response: Response, lockout_check_fn):
        # We assume lockout check is done by router or passed in
        user = db.query(User).filter(User.username == payload.username).first()
        if not user or not user.password:
            raise HTTPException(status_code=400, detail="Incorrect username or password")
        
        if not verify_password(payload.password, user.password):
            raise HTTPException(status_code=400, detail="Incorrect username or password")

        if not user.is_verified:
            raise HTTPException(status_code=403, detail="Email not verified")

        token = create_access_token(data={"sub": str(user.id)})
        
        # Set cookie
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="none",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

        return {"access_token": token, "token_type": "bearer", "user": user}

    @staticmethod
    def update_profile(db: Session, current_user: User, payload):
        if payload.full_name is not None:
            current_user.full_name = payload.full_name
        if payload.phone_number is not None:
            current_user.phone_number = payload.phone_number
        if payload.date_of_birth is not None:
            current_user.date_of_birth = payload.date_of_birth
            
        db.commit()
        db.refresh(current_user)
        return current_user

    @staticmethod
    def delete_account(db: Session, current_user: User, payload):
        if current_user.password:
            if not payload.password:
                raise HTTPException(status_code=400, detail="Password confirmation is required to delete your account")
            if not verify_password(payload.password, current_user.password):
                raise HTTPException(status_code=400, detail="Incorrect password")

        from app.models.submission import Submission
        db.query(Submission).filter(Submission.user_id == current_user.id).delete()
        db.delete(current_user)
        db.commit()
        return {"message": "Account deleted successfully"}
