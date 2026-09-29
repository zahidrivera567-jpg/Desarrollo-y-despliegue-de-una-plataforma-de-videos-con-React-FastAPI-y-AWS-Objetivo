import os
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

import boto3
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship

# ==========================================
# 1. CONFIGURACIÓN Y VARIABLES DE ENTORNO
# ==========================================
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "videodb")

SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

SECRET_KEY = os.getenv("SECRET_KEY", "secreto_super_seguro_para_desarrollo")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_VIDEOS = os.getenv("S3_BUCKET_VIDEOS", "mi-bucket-videos")
S3_BUCKET_THUMBNAILS = os.getenv("S3_BUCKET_THUMBNAILS", "mi-bucket-miniaturas")

# ==========================================
# 2. CONEXIÓN A BASE DE DATOS (SQLAlchemy)
# ==========================================
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 3. MODELOS DE BASE DE DATOS
# ==========================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    videos = relationship("Video", back_populates="owner", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="owner", cascade="all, delete-orphan")

class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    video_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=False)
    views = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="videos")
    comments = relationship("Comment", back_populates="video", cascade="all, delete-orphan")

class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="comments")
    video = relationship("Video", back_populates="comments")

# Crear tablas en BD al arrancar
Base.metadata.create_all(bind=engine)

# ==========================================
# 4. ESQUEMAS PYDANTIC (Validación de datos)
# ==========================================
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True

class UserDetailResponse(UserResponse):
    video_count: int

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int

class CommentCreate(BaseModel):
    content: str

class CommentResponse(BaseModel):
    id: int
    content: str
    user_id: int
    video_id: int
    created_at: datetime
    owner: UserResponse

    class Config:
        from_attributes = True

class VideoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

class VideoResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    video_url: str
    thumbnail_url: str
    views: int
    user_id: int
    created_at: datetime
    owner: UserResponse

    class Config:
        from_attributes = True

# ==========================================
# 5. SEGURIDAD Y AUTENTICACIÓN (JWT / Hashing)
# ==========================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o sesión expirada.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user

# ==========================================
# 6. INTEGRACIÓN AWS S3
# ==========================================
s3_client = boto3.client("s3", region_name=AWS_REGION)

async def upload_to_s3(file: UploadFile, bucket_name: str) -> str:
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    
    try:
        s3_client.upload_fileobj(
            file.file,
            bucket_name,
            unique_filename,
            ExtraArgs={"ContentType": file.content_type}
        )
        return f"https://{bucket_name}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir a S3: {str(e)}")

def delete_from_s3(file_url: str, bucket_name: str):
    try:
        key = file_url.split("/")[-1]
        s3_client.delete_object(Bucket=bucket_name, Key=key)
    except Exception as e:
        print(f"Error borrando de S3: {e}")

# ==========================================
# 7. INICIALIZACIÓN FASTAPI Y RUTAS
# ==========================================
app = FastAPI(
    title="Plataforma de Videos API",
    description="API para gestión de usuarios, videos y comentarios",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- RUTAS DE USUARIOS ---

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")
    
    new_user = User(
        name=user.name,
        email=user.email,
        password_hash=hash_password(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas.")
    
    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user_id": user.id}

@app.get("/users/{user_id}", response_model=UserDetailResponse)
def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    
    count = db.query(Video).filter(Video.user_id == user_id).count()
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "video_count": count
    }

# --- RUTAS DE VIDEOS ---

@app.post("/videos", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    title: str = Form(...),
    description: str = Form(...),
    video_file: UploadFile = File(...),
    thumbnail_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not video_file.filename.lower().endswith(".mp4"):
        raise HTTPException(status_code=400, detail="El video debe ser en formato MP4.")
    
    ext = thumbnail_file.filename.split(".")[-1].lower()
    if ext not in ["jpg", "jpeg", "png"]:
        raise HTTPException(status_code=400, detail="La miniatura debe ser JPG, JPEG o PNG.")

    video_url = await upload_to_s3(video_file, S3_BUCKET_VIDEOS)
    thumbnail_url = await upload_to_s3(thumbnail_file, S3_BUCKET_THUMBNAILS)

    new_video = Video(
        title=title,
        description=description,
        video_url=video_url,
        thumbnail_url=thumbnail_url,
        user_id=current_user.id
    )
    db.add(new_video)
    db.commit()
    db.refresh(new_video)
    return new_video

@app.get("/videos", response_model=List[VideoResponse])
def get_videos(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Video)
    if user_id:
        query = query.filter(Video.user_id == user_id)
    return query.order_by(Video.created_at.desc()).all()

@app.get("/videos/{video_id}", response_model=VideoResponse)
def get_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video no encontrado.")
    
    video.views += 1
    db.commit()
    db.refresh(video)
    return video

@app.put("/videos/{video_id}", response_model=VideoResponse)
def update_video(
    video_id: int, 
    data: VideoUpdate, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video no encontrado.")
    if video.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permisos para modificar este video.")

    if data.title:
        video.title = data.title
    if data.description:
        video.description = data.description

    db.commit()
    db.refresh(video)
    return video

@app.delete("/videos/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(
    video_id: int, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video no encontrado.")
    if video.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permisos para eliminar este video.")

    delete_from_s3(video.video_url, S3_BUCKET_VIDEOS)
    delete_from_s3(video.thumbnail_url, S3_BUCKET_THUMBNAILS)

    db.delete(video)
    db.commit()
    return None

# --- RUTAS DE COMENTARIOS ---

@app.post("/videos/{video_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(
    video_id: int, 
    comment: CommentCreate, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not db.query(Video).filter(Video.id == video_id).first():
        raise HTTPException(status_code=404, detail="Video no encontrado.")

    new_comment = Comment(
        content=comment.content,
        video_id=video_id,
        user_id=current_user.id
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    return new_comment

@app.get("/videos/{video_id}/comments", response_model=List[CommentResponse])
def get_comments(video_id: int, db: Session = Depends(get_db)):
    return db.query(Comment).filter(Comment.video_id == video_id).order_by(Comment.created_at.desc()).all()