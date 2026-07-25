# Enhanced backend/main.py
import asyncio
import smtplib
import sys
import httpx
import schedule
import time
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timedelta
import random
import os
from faker import Faker
import logging

# Import our new modules
from database import db_manager, init_database
from websocket_manager import websocket_manager
from email_templates import email_template_manager

# Fix for Uvicorn reloader on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Social Media Monitor - Enhanced V6", version="6.0.0")
fake = Faker()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Email Configuration ---
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "your_email@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "your_app_password")

# --- Pydantic Models ---
class BrandCreate(BaseModel):
    name: str

class EmailConfig(BaseModel):
    email: str

class NotificationRequest(BaseModel):
    title: str
    message: str
    notification_type: str = "info"

# --- Enhanced AI & Scraping Simulation ---
async def generate_ai_summary(content: str) -> dict:
    """Enhanced AI summary generation with more realistic analysis"""
    sentiments = ["Positive", "Negative", "Neutral"]
    
    # More sophisticated sentiment analysis simulation
    positive_keywords = ["great", "amazing", "love", "excellent", "fantastic", "awesome", "perfect"]
    negative_keywords = ["bad", "terrible", "hate", "awful", "worst", "disappointing", "horrible"]
    
    content_lower = content.lower()
    positive_score = sum(1 for word in positive_keywords if word in content_lower)
    negative_score = sum(1 for word in negative_keywords if word in content_lower)
    
    if positive_score > negative_score:
        sentiment = "Positive"
    elif negative_score > positive_score:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"
    
    # Generate more contextual summary
    words = content.split()
    if len(words) > 15:
        summary = " ".join(words[:15]) + "..."
    else:
        summary = content
    
    return {
        "summary": f"AI Analysis: {summary}",
        "sentiment": sentiment
    }

async def scrape_social_media_data(profile: dict) -> List[dict]:
    """Enhanced social media data scraping simulation"""
    logger.info(f"Starting enhanced data collection for {profile['name']} on {profile['platform']}")
    
    # Simulate realistic API delay
    await asyncio.sleep(random.uniform(1.5, 3.0))
    
    posts = []
    post_count = random.randint(3, 8)  # More posts for better analytics
    
    for i in range(post_count):
        # Generate more realistic content based on platform
        if profile['platform'] == 'youtube':
            content_templates = [
                f"New video: {fake.catch_phrase()} | {profile['name']} Official Channel",
                f"Behind the scenes: {fake.sentence()} | Subscribe for more!",
                f"Tutorial: {fake.bs()} | {profile['name']} explains everything",
                f"Live stream recap: {fake.sentence()} | Thanks for watching!"
            ]
        elif profile['platform'] == 'twitter':
            content_templates = [
                f"{fake.sentence(nb_words=20)} #{profile['name']} #{random.choice(['innovation', 'tech', 'news', 'update'])}",
                f"Excited to announce: {fake.sentence()} #announcement #{profile['name']}",
                f"Thread 🧵: {fake.sentence()} Let's discuss! #{profile['name']}",
                f"Quick update: {fake.sentence()} What do you think? #{profile['name']}"
            ]
        elif profile['platform'] == 'instagram':
            content_templates = [
                f"{fake.sentence(nb_words=12)} 📸 #photography #{profile['name']} #picoftheday",
                f"Story time: {fake.sentence()} ✨ #{profile['name']} #lifestyle",
                f"Behind the brand: {fake.sentence()} 💼 #{profile['name']} #business",
                f"Community love: {fake.sentence()} ❤️ #{profile['name']} #grateful"
            ]
        else:
            content_templates = [fake.paragraph(nb_sentences=2)]
        
        content = random.choice(content_templates)
        
        # Generate realistic engagement metrics
        base_likes = random.randint(500, 50000)
        posts.append({
            "content": content,
            "likes": base_likes,
            "comments": random.randint(int(base_likes * 0.02), int(base_likes * 0.1)),
            "shares": random.randint(int(base_likes * 0.01), int(base_likes * 0.05)),
            "timestamp": fake.date_time_between(start_date='-2d', end_date='now')
        })
    
    logger.info(f"Collected {len(posts)} posts for {profile['name']} on {profile['platform']}")
    return posts

async def process_and_store_posts(brand_id: int):
    """Enhanced post processing with database storage and real-time updates"""
    brands = db_manager.get_brands()
    brand_data = next((b for b in brands if b["id"] == brand_id), None)
    if not brand_data:
        return
    
    logger.info(f"Processing posts for brand: {brand_data['name']}")
    
    all_new_posts = []
    
    for profile in brand_data['profiles']:
        new_posts_data = await scrape_social_media_data(profile)
        for post_data in new_posts_data:
            analysis = await generate_ai_summary(post_data["content"])
            
            # Store in database
            post = db_manager.add_post(
                brand_id=brand_id,
                platform=profile['platform'],
                content=post_data["content"],
                likes=post_data["likes"],
                comments=post_data["comments"],
                shares=post_data["shares"],
                summary=analysis["summary"],
                sentiment=analysis["sentiment"],
                timestamp=post_data["timestamp"]
            )
            
            if post:
                all_new_posts.append({
                    "id": post.id,
                    "brand_id": brand_id,
                    "platform": profile['platform'],
                    "content": post_data["content"],
                    "likes": post_data["likes"],
                    "comments": post_data["comments"],
                    "shares": post_data["shares"],
                    "summary": analysis["summary"],
                    "sentiment": analysis["sentiment"],
                    "timestamp": post_data["timestamp"].isoformat()
                })
    
    # Broadcast real-time updates
    if all_new_posts:
        await websocket_manager.broadcast_post_update(all_new_posts)
        await websocket_manager.broadcast_notification(
            f"Found {len(all_new_posts)} new posts for {brand_data['name']}", 
            "success"
        )
    
    logger.info(f"Processed {len(all_new_posts)} posts for {brand_data['name']}")

# --- Enhanced Email & Reporting ---
async def generate_and_send_report(brand_id: int = None, email: str = None):
    """Enhanced report generation with rich templates"""
    if not email:
        email = db_manager.get_email_config()
    
    if not email:
        logger.warning("No email configured for reports")
        return
    
    logger.info(f"Generating enhanced report for email: {email}")
    
    # Get brands data
    if brand_id:
        brands = [next((b for b in db_manager.get_brands() if b["id"] == brand_id), None)]
        brands = [b for b in brands if b is not None]
    else:
        brands = db_manager.get_brands()
    
    if not brands:
        logger.warning("No brands found for report generation")
        return
    
    # Prepare data for email template
    brands_data = []
    for brand in brands:
        posts = db_manager.get_posts(brand_id=brand["id"], limit=20)
        brands_data.append({
            "name": brand["name"],
            "posts": posts
        })
    
    # Generate email content
    email_content = email_template_manager.generate_brand_report(brands_data, days=2)
    
    # Send email
    if EMAIL_SENDER == "your_email@gmail.com" or EMAIL_PASSWORD == "your_app_password":
        logger.info(f"EMAIL SIMULATION: Enhanced report would be sent to {email}")
        await websocket_manager.broadcast_notification(
            f"Report generated successfully (simulation mode)", 
            "info"
        )
        return
    
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = email
        msg['Subject'] = f"Social Media Monitor Report - {datetime.now().strftime('%B %d, %Y')}"
        msg.attach(MIMEText(email_content, 'html'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, email, msg.as_string())
        
        logger.info(f"Enhanced email report sent successfully to {email}")
        await websocket_manager.broadcast_notification(
            f"Report sent successfully to {email}", 
            "success"
        )
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        await websocket_manager.broadcast_notification(
            f"Failed to send report: {str(e)}", 
            "error"
        )

async def send_welcome_email(email: str):
    """Send welcome email to new users"""
    email_content = email_template_manager.generate_welcome_email(email)
    
    if EMAIL_SENDER == "your_email@gmail.com" or EMAIL_PASSWORD == "your_app_password":
        logger.info(f"WELCOME EMAIL SIMULATION: Would be sent to {email}")
        return
    
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = email
        msg['Subject'] = "Welcome to Social Media Monitor"
        msg.attach(MIMEText(email_content, 'html'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, email, msg.as_string())
        
        logger.info(f"Welcome email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send welcome email: {e}")

def send_all_reports():
    """Scheduled function to send all reports"""
    email = db_manager.get_email_config()
    if email and db_manager.get_brands():
        logger.info("Starting scheduled report cycle")
        asyncio.run(generate_and_send_report(email=email))
        logger.info("Scheduled report cycle complete")

def run_scheduler():
    """Run the background scheduler"""
    schedule.every(2).days.do(send_all_reports)
    while True:
        schedule.run_pending()
        time.sleep(3600)  # Check every hour

# --- WebSocket Endpoint ---
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming WebSocket messages if needed
            logger.info(f"Received WebSocket message from {client_id}: {data}")
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)

# --- Enhanced API Endpoints ---
@app.get("/")
def read_root():
    return {
        "message": "Social Media Monitor - Enhanced V6",
        "version": "6.0.0",
        "features": [
            "SQLite Database Storage",
            "Real-time WebSocket Updates",
            "Enhanced Email Templates",
            "Advanced Analytics",
            "Professional UI Theme"
        ]
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected",
        "websocket_connections": websocket_manager.get_connection_count()
    }

@app.post("/configure-email")
async def configure_email(config: EmailConfig, background_tasks: BackgroundTasks):
    """Configure email with welcome message"""
    db_manager.set_email_config(config.email)
    
    # Send welcome email
    background_tasks.add_task(send_welcome_email, config.email)
    
    await websocket_manager.broadcast_notification(
        f"Email configured: {config.email}", 
        "success"
    )
    
    return {"message": f"Email configured. Welcome email sent to {config.email}"}

@app.get("/brands")
def get_brands():
    """Get all brands with enhanced data"""
    return db_manager.get_brands()

@app.post("/brands", status_code=201)
async def add_brand(brand_data: BrandCreate, background_tasks: BackgroundTasks):
    """Add brand with enhanced processing"""
    brand = db_manager.add_brand(brand_data.name)
    
    # Process posts in background
    background_tasks.add_task(process_and_store_posts, brand.id)
    
    # Send notification email if configured
    email = db_manager.get_email_config()
    if email:
        profiles = [{"platform": "twitter", "name": brand_data.name.lower()},
                   {"platform": "instagram", "name": brand_data.name.lower()},
                   {"platform": "youtube", "name": f"{brand_data.name.capitalize()}Official"}]
        
        email_content = email_template_manager.generate_brand_added_email(
            brand_data.name, profiles
        )
        # In a real implementation, you'd send this email
    
    # Broadcast real-time update
    await websocket_manager.broadcast_brand_update({
        "id": brand.id,
        "name": brand.name,
        "action": "added"
    })
    
    return {
        "id": brand.id,
        "name": brand.name,
        "profiles": [
            {"platform": "twitter", "name": brand_data.name.lower()},
            {"platform": "instagram", "name": brand_data.name.lower()},
            {"platform": "youtube", "name": f"{brand_data.name.capitalize()}Official"}
        ]
    }

@app.delete("/brands/{brand_id}", status_code=204)
async def delete_brand(brand_id: int):
    """Delete brand with real-time updates"""
    success = db_manager.delete_brand(brand_id)
    if not success:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    await websocket_manager.broadcast_brand_update({
        "id": brand_id,
        "action": "deleted"
    })
    
    return

@app.get("/posts")
def get_latest_posts(brand_id: Optional[int] = None, limit: int = 50):
    """Get posts with enhanced filtering"""
    return db_manager.get_posts(brand_id=brand_id, limit=limit)

@app.get("/analytics/{brand_id}")
async def get_analytics(brand_id: int):
    """Get enhanced analytics data"""
    analytics = db_manager.get_analytics(brand_id)
    
    # Broadcast analytics update
    await websocket_manager.broadcast_analytics_update(brand_id, analytics)
    
    return analytics

@app.post("/reports/send-all")
async def send_all_reports_now(background_tasks: BackgroundTasks):
    """Send all reports immediately"""
    email = db_manager.get_email_config()
    if not email:
        raise HTTPException(status_code=400, detail="Email not configured")
    
    brands = db_manager.get_brands()
    if not brands:
        raise HTTPException(status_code=400, detail="No brands to monitor")
    
    background_tasks.add_task(generate_and_send_report, email=email)
    
    await websocket_manager.broadcast_notification(
        "Generating and sending reports for all brands", 
        "info"
    )
    
    return {"message": f"Reports are being generated and sent to {email}"}

@app.post("/reports/send/{brand_id}")
async def send_brand_report(brand_id: int, background_tasks: BackgroundTasks):
    """Send report for specific brand"""
    email = db_manager.get_email_config()
    if not email:
        raise HTTPException(status_code=400, detail="Email not configured")
    
    background_tasks.add_task(generate_and_send_report, brand_id, email)
    
    return {"message": f"Report for brand {brand_id} is being sent to {email}"}

@app.post("/notifications/send")
async def send_notification(notification: NotificationRequest):
    """Send custom notification to all connected clients"""
    await websocket_manager.broadcast_notification(
        notification.message, 
        notification.notification_type
    )
    return {"message": "Notification sent to all connected clients"}

@app.get("/websocket/info")
def get_websocket_info():
    """Get WebSocket connection information"""
    return {
        "active_connections": websocket_manager.get_connection_count(),
        "connection_details": websocket_manager.get_connection_info()
    }

@app.on_event("startup")
async def startup_event():
    """Initialize database and start scheduler"""
    init_database()
    threading.Thread(target=run_scheduler, daemon=True).start()
    logger.info("Enhanced Social Media Monitor started successfully")
    logger.info("Database initialized and scheduler started")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

