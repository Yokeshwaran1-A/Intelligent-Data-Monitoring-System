"""
Database module for Social Media Monitor
Provides SQLite database functionality with SQLAlchemy ORM
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# Database configuration
DATABASE_URL = "sqlite:///./social_media_monitor.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class Brand(Base):
    __tablename__ = "brands"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    profiles = relationship("Profile", back_populates="brand", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="brand", cascade="all, delete-orphan")

class Profile(Base):
    __tablename__ = "profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"))
    platform = Column(String, index=True)
    username = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    brand = relationship("Brand", back_populates="profiles")

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"))
    platform = Column(String, index=True)
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    summary = Column(Text)
    sentiment = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    brand = relationship("Brand", back_populates="posts")

class EmailConfig(Base):
    __tablename__ = "email_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Database functions
def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_database():
    """Initialize database with tables"""
    create_tables()
    print("Database initialized successfully")

# Database operations
class DatabaseManager:
    def __init__(self):
        self.SessionLocal = SessionLocal
    
    def get_session(self):
        return self.SessionLocal()
    
    def add_brand(self, name: str):
        """Add a new brand to the database"""
        db = self.get_session()
        try:
            # Check if brand already exists
            existing_brand = db.query(Brand).filter(Brand.name == name).first()
            if existing_brand:
                return existing_brand
            
            # Create new brand
            brand = Brand(name=name)
            db.add(brand)
            db.commit()
            db.refresh(brand)
            
            # Add default profiles
            platforms = [
                {"platform": "twitter", "username": name.lower()},
                {"platform": "instagram", "username": name.lower()},
                {"platform": "youtube", "username": f"{name.capitalize()}Official"}
            ]
            
            for platform_data in platforms:
                profile = Profile(
                    brand_id=brand.id,
                    platform=platform_data["platform"],
                    username=platform_data["username"]
                )
                db.add(profile)
            
            db.commit()
            return brand
        finally:
            db.close()
    
    def get_brands(self):
        """Get all brands with their profiles"""
        db = self.get_session()
        try:
            brands = db.query(Brand).all()
            result = []
            for brand in brands:
                profiles = [{"platform": p.platform, "name": p.username} for p in brand.profiles]
                result.append({
                    "id": brand.id,
                    "name": brand.name,
                    "profiles": profiles
                })
            return result
        finally:
            db.close()
    
    def delete_brand(self, brand_id: int):
        """Delete a brand and all associated data"""
        db = self.get_session()
        try:
            brand = db.query(Brand).filter(Brand.id == brand_id).first()
            if brand:
                db.delete(brand)
                db.commit()
                return True
            return False
        finally:
            db.close()
    
    def add_post(self, brand_id: int, platform: str, content: str, likes: int, 
                 comments: int, shares: int, summary: str, sentiment: str, timestamp: datetime):
        """Add a new post to the database"""
        db = self.get_session()
        try:
            post = Post(
                brand_id=brand_id,
                platform=platform,
                content=content,
                likes=likes,
                comments=comments,
                shares=shares,
                summary=summary,
                sentiment=sentiment,
                timestamp=timestamp
            )
            db.add(post)
            db.commit()
            db.refresh(post)
            return post
        finally:
            db.close()
    
    def get_posts(self, brand_id: int = None, limit: int = 50):
        """Get posts, optionally filtered by brand"""
        db = self.get_session()
        try:
            query = db.query(Post)
            if brand_id:
                query = query.filter(Post.brand_id == brand_id)
            
            posts = query.order_by(Post.timestamp.desc()).limit(limit).all()
            return [{
                "id": post.id,
                "brand_id": post.brand_id,
                "platform": post.platform,
                "content": post.content,
                "timestamp": post.timestamp,
                "likes": post.likes,
                "comments": post.comments,
                "shares": post.shares,
                "summary": post.summary,
                "sentiment": post.sentiment
            } for post in posts]
        finally:
            db.close()
    
    def get_analytics(self, brand_id: int):
        """Get analytics data for a brand"""
        db = self.get_session()
        try:
            posts = db.query(Post).filter(Post.brand_id == brand_id).all()
            
            if not posts:
                return {
                    "engagement": {"labels": [], "data": []},
                    "sentiment": {"labels": [], "data": []}
                }
            
            # Calculate engagement metrics
            total_likes = sum(post.likes for post in posts)
            total_comments = sum(post.comments for post in posts)
            total_shares = sum(post.shares for post in posts)
            
            # Calculate sentiment distribution
            sentiment_counts = {"Positive": 0, "Negative": 0, "Neutral": 0}
            for post in posts:
                if post.sentiment in sentiment_counts:
                    sentiment_counts[post.sentiment] += 1
            
            return {
                "engagement": {
                    "labels": ["Likes", "Comments", "Shares"],
                    "data": [total_likes, total_comments, total_shares]
                },
                "sentiment": {
                    "labels": list(sentiment_counts.keys()),
                    "data": list(sentiment_counts.values())
                }
            }
        finally:
            db.close()
    
    def set_email_config(self, email: str):
        """Set or update email configuration"""
        db = self.get_session()
        try:
            # Check if email config exists
            config = db.query(EmailConfig).first()
            if config:
                config.email = email
                config.updated_at = datetime.utcnow()
            else:
                config = EmailConfig(email=email)
                db.add(config)
            
            db.commit()
            return config
        finally:
            db.close()
    
    def get_email_config(self):
        """Get current email configuration"""
        db = self.get_session()
        try:
            config = db.query(EmailConfig).first()
            return config.email if config else None
        finally:
            db.close()

# Global database manager instance
db_manager = DatabaseManager()

