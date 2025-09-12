from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select, insert
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from app.models.user import User
from app.models.role import Role
from app.schemas import CreateUser
from app.db_depends import get_db
from fastapi import Body

# from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

# для JWT
from datetime import datetime, timedelta, timezone
import jwt



SECRET_KEY = 'a21679097c1ba42e9bd06eea239cdc5bf19b249e87698625cba5e3572f005544'
ALGORITHM = 'HS256' # Алгоритм шифрования

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

#oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token") # Схема OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login") # Схема OAuth2


router = APIRouter(prefix='/auth', tags=['Auth'])
#router = APIRouter(prefix='', tags=['Auth'])
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto') # Для хеширования паролей



# create_access_token() - создаёт access token:
# -Содержит данные пользователя (username, id, role_id)
# -Время жизни: 30 минут
# -Подписывается секретным ключом
async def create_access_token(username: str, user_id: int, role_id: int, expires_delta: timedelta):
    payload = {
        'sub': username,
        #фикс ниже(Нужно перед сохранением в payload привести UUID к строке:)
        'id': str(user_id),
        'role_id': role_id,
        'exp': datetime.now(timezone.utc) + expires_delta
    }

    # Преобразование datetime в timestamp (количество секунд с начала эпохи)
    payload['exp'] = int(payload['exp'].timestamp())
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)



# create_refresh_token() - создаёт refresh token:
# -Время жизни: 7 дней
# -Используется для обновления access token
def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})

    # Преобразование datetime в timestamp (как в create_access_token)
    to_encode['exp'] = int(to_encode['exp'].timestamp())

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)



# authenticate_user() - проверяет логин/пароль:
# -Ищет пользователя в базе по имени
# -Сравнивает хеш пароля с помощью bcrypt
# -Возвращает пользователя или вызывает исключение
# Если юзер сщуествует и пороли совпадают, возвращает объект user из БД.
async def authenticate_user(db: Annotated[AsyncSession, Depends(get_db)], username: str, password: str):
    user = await db.scalar(select(User).where(User.name == username))
    if not user or not bcrypt_context.verify(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# get_current_user() - валидирует JWT токен:
# -Декодирует и проверяет токен
# -Извлекает данные пользователя из payload
# -Обрабатывает истечение срока действия токена
# Метод для доступа через JWT к защищёным эндпоинтам
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get('sub')
        user_id: int | None = payload.get('id')
        role_id: int | None = payload.get('role_id')
        expire: int | None = payload.get('exp')

        if username is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Could not validate user'
            )

        return {
            'name': username,
            'id': user_id,
            'role_id': role_id,
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired!"
        )
    except jwt.exceptions:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Could not validate user'
        )



# /auth/ (POST) - регистрация нового пользователя:
# -Создаёт пользователя с ролью "user"
# -Хеширует пароль перед сохранением
@router.post('/register', status_code=status.HTTP_201_CREATED)
async def sign_up(db: Annotated[AsyncSession, Depends(get_db)], create_user: CreateUser):
    # ищем роль "user"
    result = await db.execute(select(Role).where(Role.name == "user"))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=527, detail="Роль 'user' не найдена")

    # создаём пользователя с этой ролью
    await db.execute(insert(User).values(name=create_user.name,
                                         email=create_user.email,
                                         password_hash=bcrypt_context.hash(create_user.password),
                                         role_id=role.id
                                         ))
    await db.commit()
    return {
        'status_code': status.HTTP_201_CREATED,
        'transaction': 'Successful'
    }



# /auth/token (POST) - получение токенов:
# -Принимает логин/пароль через OAuth2 форму
# -Возвращает access и refresh токены
@router.post('/login')
async def sign_in(db: Annotated[AsyncSession, Depends(get_db)], form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = await authenticate_user(db, form_data.username, form_data.password)

    # Создаем access token
    token = await create_access_token(
        user.name,
        user.id,
        user.role_id,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # Создаем refresh token
    refresh_token = create_refresh_token(
        data={"sub": user.name, "role_id": user.role_id, "id": str(user.id)}
    )

    return {
        'access_token': token,
        'refresh_token': refresh_token,
        'token_type': 'bearer'
    }



# /auth/read_current_user (GET) - получение данных текущего пользователя:
# -Требует валидный access token
# -Возвращает информацию о пользователе
# Эта штука добавляет замочек Authorize сверху и Эндпоинт ручку с замочком.
@router.get('/me')
async def read_current_user(user: dict = Depends(get_current_user)):
    return user



# /auth/refresh (POST) - обновление токенов:
# -Принимает refresh token
# -Возвращает новые access и refresh токены
@router.post("/refresh")
async def refresh_token(
        refresh_token: str = Body(..., embed=True),
        db: AsyncSession = Depends(get_db)
):
    """
    Обновляет access token и refresh token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub')
        user_id: str = payload.get('id')
        role_id: int = payload.get('role_id')

        if not username or not user_id:
            raise credentials_exception

        # Проверяем существование пользователя в БД
        result = await db.execute(select(User).where(User.name == username))
        user = result.scalar_one_or_none()

        if user is None:
            raise credentials_exception

        # Создаем новый access token
        access_token = await create_access_token(
            username,
            user_id,
            role_id,
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        # Создаем НОВЫЙ refresh token (важно обновлять и его!)
        new_refresh_token = create_refresh_token(
            data={"sub": username, "id": user_id, "role_id": role_id}
        )

        return {
            'access_token': access_token,
            'refresh_token': new_refresh_token,  # Возвращаем новый refresh token
            'token_type': 'bearer'
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )
    except jwt.InvalidTokenError:
        raise credentials_exception