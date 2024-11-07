# api/utils/dependencies.py
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from models.user import User as UserModel
from database import get_db
from security import get_current_user

def get_user_with_role(required_role: str):
    def role_checker(current_user: UserModel = Depends(get_current_user)):
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {required_role} role required"
            )
        return current_user
    return role_checker
