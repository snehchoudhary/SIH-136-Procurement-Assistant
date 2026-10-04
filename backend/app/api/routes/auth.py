from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.core.security import create_access_token, verify_token, OIDCUserInfo
from app.api.deps import get_current_user
from app.core.passwords import verify_password
from app.core.permissions import require

router = APIRouter()

@router.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    email = form_data.username.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={
        "sub": str(user.id),
        "email": user.email,
        "name": user.full_name,
        "role": user.role,
        "org_id": str(user.organisation_id) if user.organisation_id else None
    })
    return {"access_token": access_token, "token_type": "bearer", "user": {"email": user.email, "role": user.role}}

@router.get("/me")
def read_users_me(current_user: OIDCUserInfo = Depends(get_current_user)):
    return current_user


@router.get('/demo-users')
def list_demo_approvers(db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('auth.demo_users'))):
    users = db.query(User).filter(User.role.in_(['officer', 'validator', 'finance'])).order_by(User.role, User.full_name).all()
    return [{'id': str(user.id), 'name': user.full_name, 'role': user.role} for user in users]
