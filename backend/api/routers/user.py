# api/routers/user.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Union
from database import get_db
from models.user import User as UserModel
from schemas.user import UserCreate, User, UserUpdate, Token
from datetime import datetime
from security import get_password_hash, verify_password, create_access_token
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from security import get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
from utils.dependencies import get_user_with_role

'''
|-----------------------------------------------------------------------------------------------------------------------------------|
| API Router: Users             |
|-------------------------------|
'''
router = APIRouter(
    prefix="/users",
    tags=["users"]
)
'''
|-----------------------------------------------------------------------------------------------------------------------------------|
| Route /users/register         |
| Method: POST                  |
| Function: create_user         |
| Return: User                  |
|-------------------------------|
'''
@router.post("/register", response_model=User)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # Vérifier si l'utilisateur existe déjà
    db_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Créer un nouvel utilisateur avec le mot de passe haché
    hashed_password = get_password_hash(user.password)
    db_user = UserModel(
        email=user.email,
        firstname=user.firstname,
        lastname=user.lastname,
        hashed_password=hashed_password,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

'''
|-----------------------------------------------------------------------------------------------------------------------------------|
| Route /users/login            |
| Method: POST                  |
| Function: login               |
| Return: Token                 |
|-------------------------------|
'''
@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Rechercher l'utilisateur par email
    user = db.query(UserModel).filter(UserModel.email == form_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email"
        )
    
    # Vérifier le mot de passe
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    
    # Créer le token d'accès
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

'''
|-----------------------------------------------------------------------------------------------------------------------------------|
| Route /users                  |
| Method: GET                   |
| Function: read_users          |
| Admin Return Users            |
| Non-Admin Return Current User |
|-------------------------------|
'''
@router.get("", response_model=Union[User, List[User]])
def read_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user)
):
    # Vérifier si l'utilisateur est admin
    if current_user.role == "admin":
        # Si admin, retourner tous les utilisateurs
        users = db.query(UserModel).offset(skip).limit(limit).all()
        return users
    else:
        # Si non-admin, retourner uniquement son propre profil
        return current_user

@router.get("/{user_id}", response_model=User)
def read_user(user_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_user_with_role("admin"))):
    db_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return db_user

'''
|-----------------------------------------------------------------------------------------------------------------------------------|
| Route /users/me               |
| Method: PUT                   |
| Function: update_user_profile |
| Return: User                  |
|-------------------------------|
'''
@router.put("/me", response_model=User)
def update_user_profile(
    user: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    # Récupérer l'utilisateur connecté
    db_user = db.query(UserModel).filter(UserModel.id == current_user.id).first()
    
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Extraire les données de mise à jour sans les champs non définis
    update_data = user.dict(exclude_unset=True)

    # Empêcher la modification du champ `role`
    if "role" in update_data:
        del update_data["role"]

    # Hacher le mot de passe si le champ `password` est mis à jour
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    # Appliquer les mises à jour sur l'utilisateur connecté
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    # Mettre à jour la date de modification
    db_user.updated_at = datetime.now()
    
    # Sauvegarder les changements
    db.commit()
    db.refresh(db_user)
    return db_user

'''
|-----------------------------------------------------------------------------------------------------------------------------------|
| Route /users/{user_id}        |
| Method: PUT                   |
| Function: admin_update_user   |
| Admin Update Role             |
| Return: User                  |
|-------------------------------|
'''
@router.put("/{user_id}", response_model=User)
def admin_update_user(
    user_id: int,
    user: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_user_with_role("admin"))
):
    # Vérifier si l'utilisateur cible existe
    db_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Extraire les données de mise à jour sans les champs non définis
    update_data = user.dict(exclude_unset=True)
    print("Données de mise à jour:", update_data)  # Debugging: vérifier si `role` est présent

    # Hacher le mot de passe si le champ `password` est mis à jour
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

    # Forcer la mise à jour du champ `role` si présent
    if "role" in update_data:
        db_user.role = update_data["role"]

    # Appliquer les autres mises à jour
    for field, value in update_data.items():
        if field != "role":  # Exclure `role` car il est déjà appliqué explicitement
            setattr(db_user, field, value)
    
    # Mettre à jour la date de modification
    db_user.updated_at = datetime.now()
    
    # Sauvegarder les changements
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    db_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully"}