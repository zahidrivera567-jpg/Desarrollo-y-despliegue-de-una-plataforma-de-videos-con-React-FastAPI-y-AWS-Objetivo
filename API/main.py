from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 1. Base de datos SQLite (se guarda en un archivo local automático)
SQLALCHEMY_DATABASE_URL = "sqlite:///./videos.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 2. Modelos Simplificados
class Video(Base):
    __tablename__ = "videos"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    video_url = Column(String(255), nullable=False)
    comments = relationship("Comment", back_populates="video", cascade="all, delete-orphan")

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    video = relationship("Video", back_populates="comments")

Base.metadata.create_all(bind=engine)

# 3. Esquemas Pydantic (para recibir/responder datos)
class CommentCreate(BaseModel):
    content: str

class CommentResponse(BaseModel):
    id: int
    content: str
    video_id: int
    class Config:
        from_attributes = True

class VideoCreate(BaseModel):
    title: str
    description: Optional[str] = None
    video_url: str

class VideoResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    video_url: str
    comments: List[CommentResponse] = []
    class Config:
        from_attributes = True

# 4. API FastAPI
app = FastAPI(title="API de Videos Sencilla")

# --- VIDEOS ---
@app.post("/videos", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
def create_video(video: VideoCreate, db: Session = Depends(get_db)):
    new_video = Video(**video.model_dump())
    db.add(new_video)
    db.commit()
    db.refresh(new_video)
    return new_video

@app.get("/videos", response_model=List[VideoResponse])
def get_videos(db: Session = Depends(get_db)):
    return db.query(Video).all()

@app.get("/videos/{video_id}", response_model=VideoResponse)
def get_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video no encontrado")
    return video

@app.delete("/videos/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video no encontrado")
    db.delete(video)
    db.commit()

# --- COMENTARIOS ---
@app.post("/videos/{video_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(video_id: int, comment: CommentCreate, db: Session = Depends(get_db)):
    if not db.query(Video).filter(Video.id == video_id).first():
        raise HTTPException(status_code=404, detail="Video no encontrado")
    
    new_comment = Comment(content=comment.content, video_id=video_id)
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    return new_comment

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción puedes restringirlo a la URL de tu S3 Frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)