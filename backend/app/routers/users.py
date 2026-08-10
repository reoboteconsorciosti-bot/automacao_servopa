from typing import List

from fastapi import APIRouter, Depends, status

from app.schemas.user_schema import UserCreate, UserOut, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=List[UserOut])
def list_users(service: UserService = Depends(UserService.inject)) -> List[UserOut]:
    return service.list_users()


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int, service: UserService = Depends(UserService.inject)
) -> UserOut:
    return service.get_user_or_404(user_id)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate, service: UserService = Depends(UserService.inject)
) -> UserOut:
    return service.create_user(payload)


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    service: UserService = Depends(UserService.inject),
) -> UserOut:
    return service.update_user(user_id, payload)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int, service: UserService = Depends(UserService.inject)
) -> None:
    service.delete_user(user_id)
