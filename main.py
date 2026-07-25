# backend/main.py
import asyncio
import smtplib
import sys
import httpx
import schedule
import time
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import random
import os
from faker import Faker

# Fix for Uvicorn reloader on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

app = FastAPI(title="Brand Watch AI Backend V5")
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
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "you@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "pass of app")

REPORT_EMAIL = None

# --- In-Memory Database ---
db = { "brands": [], "posts": [] }

# --- Pydantic Models ---
class Brand(BaseModel):
    id: int
    name: str
    profiles: List[dict]

class BrandCreate(BaseModel):
    name: str

class Post(BaseModel):
    id: int
    brand_id: int
    platform: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    likes: int
    comments: int
    shares: int
    summary: Optional[str] = None
    sentiment: str

class EmailConfig(BaseModel):
    email: str

# --- AI & Advanced Scraping Simulation ---
async def generate_ai_summary(content: str) -> dict:
    sentiments = ["Positive", "Negative", "Neutral"]
    summary = " ".join(content.split()[:12]) + "..."
    return {"summary": f"AI Summary: {summary}", "sentiment": random.choice(sentiments)}

async def scrape_social_media_data(profile: dict) -> List[dict]:
    print(f"-> SCRAPING: Starting data collection for {profile['name']} on {profile['platform']}...")
    await asyncio.sleep(random.uniform(1.0, 2.5))
    
    posts = []
    for _ in range(random.randint(2, 5)):
        if profile['platform'] == 'youtube':
            content = f"Video: {fake.catch_phrase()} | {profile['name']} Official"
        elif profile['platform'] == 'twitter':
            content = f"{fake.sentence(nb_words=15)} #{profile['name']} #{random.choice(['innovation', 'tech', 'news'])}"
        elif profile['platform'] == 'instagram':
            content = f"{fake.sentence(nb_words=8)} 📸 Photo by our amazing team! #picoftheday #{profile['name']}"
        else:
            content = fake.paragraph(nb_sentences=2)

        posts.append({
            "content": content,
            "likes": random.randint(100, 25000),
            "comments": random.randint(20, 1000),
            "shares": random.randint(10, 500),
            "timestamp": fake.date_time_between(start_date='-2d', end_date='now')
        })
    print(f"-> SCRAPING: Found {len(posts)} new posts for {profile['name']} on {profile['platform']}.")
    return posts

async def process_and_store_posts(brand_id: int):
    brand_data = next((b for b in db["brands"] if b["id"] == brand_id), None)
    if not brand_data: return
        
    brand = Brand(**brand_data)
    db["posts"] = [p for p in db["posts"] if p["brand_id"] != brand_id]
    
    for profile in brand.profiles:
        new_posts_data = await scrape_social_media_data(profile)
        for post_data in new_posts_data:
            analysis = await generate_ai_summary(post_data["content"])
            new_post = Post(id=len(db["posts"]) + 1, brand_id=brand.id, platform=profile['platform'], **post_data, **analysis)
            db["posts"].append(new_post.dict())
    print(f"-> PROCESSING: Finished AI analysis for {brand.name}'s posts.")

# --- Email & Reporting ---
async def generate_and_send_report(brand: Brand, email: str):
    print(f"-> REPORTING: Generating 2-day activity report for {brand.name} to be sent to {email}...")
    recent_posts = [p for p in db["posts"] if p['brand_id'] == brand.id]
    
    report_content = f"<html><body><h2>2-Day Report for {brand.name}</h2>"
    if not recent_posts:
        report_content += "<p>No new posts detected in the last 2 days.</p>"
    else:
        for profile in brand.profiles:
            report_content += f"<h3>{profile['platform'].capitalize()}</h3><ul>"
            profile_posts = [p for p in recent_posts if p['platform'] == profile['platform']]
            if not profile_posts:
                report_content += "<li>No posts from this platform.</li>"
            for post in profile_posts:
                report_content += f"<li style='margin-bottom: 15px;'><strong>Post:</strong> \"{post['content'][:100]}...\"<br><strong>AI Summary:</strong> {post['summary']}</li>"
            report_content += "</ul>"
    report_content += "</body></html>"
    
    if EMAIL_SENDER == "your_email@gmail.com" or EMAIL_PASSWORD == "your_app_password":
        print(f"!!! EMAIL SIMULATION: Report for {brand.name} would be sent to {email}.")
        return

    try:
        msg = MIMEMultipart(); msg['From'] = EMAIL_SENDER; msg['To'] = email; msg['Subject'] = f"Brand Watch AI: 2-Day Report for {brand.name}"
        msg.attach(MIMEText(report_content, 'html'))
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(); server.login(EMAIL_SENDER, EMAIL_PASSWORD); server.sendmail(EMAIL_SENDER, email, msg.as_string())
        print(f"-> REPORTING: Email report for {brand.name} sent successfully to {email}.")
    except Exception as e: print(f"!!! FAILED TO SEND EMAIL: {e}")

def send_all_reports():
    if REPORT_EMAIL and db["brands"]:
        print("-> SCHEDULER: Starting 2-day report cycle...")
        for brand_data in db["brands"]:
            brand = Brand(**brand_data)
            asyncio.run(generate_and_send_report(brand, REPORT_EMAIL))
        print("-> SCHEDULER: 2-day report cycle complete.")

def run_scheduler():
    schedule.every(2).days.do(send_all_reports)
    while True:
        schedule.run_pending(); time.sleep(3600)

# --- API Endpoints ---
@app.get("/")
def read_root(): return {"message": "Brand Watch AI Backend V5 is running"}

@app.post("/configure-email")
def configure_email(config: EmailConfig):
    global REPORT_EMAIL; REPORT_EMAIL = config.email
    return {"message": f"Email configured. Reports will be sent to {config.email}."}

@app.get("/brands", response_model=List[Brand])
def get_brands(): return db["brands"]

@app.post("/brands", response_model=Brand, status_code=201)
async def add_brand(brand_data: BrandCreate, background_tasks: BackgroundTasks):
    brand_name = brand_data.name
    
    profiles = [
        {"platform": "twitter", "name": brand_name.lower()},
        {"platform": "instagram", "name": brand_name.lower()},
        {"platform": "youtube", "name": f"{brand_name.capitalize()}Official"}
    ]
    
    new_id = max([b["id"] for b in db["brands"]] + [0]) + 1
    new_brand = Brand(id=new_id, name=brand_data.name, profiles=profiles)
    db["brands"].append(new_brand.dict())
    
    background_tasks.add_task(process_and_store_posts, new_id)
    if REPORT_EMAIL:
        background_tasks.add_task(generate_and_send_report, new_brand, REPORT_EMAIL)
    
    return new_brand

@app.delete("/brands/{brand_id}", status_code=204)
def delete_brand(brand_id: int):
    db["brands"] = [b for b in db["brands"] if b["id"] != brand_id]
    db["posts"] = [p for p in db["posts"] if p["brand_id"] != brand_id]
    return

@app.get("/posts", response_model=List[Post])
def get_latest_posts(): return sorted(db["posts"], key=lambda p: p["timestamp"], reverse=True)

@app.post("/reports/send-all")
async def send_all_reports_now(background_tasks: BackgroundTasks):
    if not REPORT_EMAIL: raise HTTPException(status_code=400, detail="Email not configured.")
    if not db["brands"]: raise HTTPException(status_code=400, detail="No brands to monitor.")
    
    for brand_data in db["brands"]:
        background_tasks.add_task(generate_and_send_report, Brand(**brand_data), REPORT_EMAIL)
    return {"message": f"Reports for all brands are being generated and sent to {REPORT_EMAIL}."}

@app.get("/analytics/{brand_id}")
def get_analytics(brand_id: int):
    brand_posts = [p for p in db["posts"] if p["brand_id"] == brand_id]
    if not brand_posts: return {"engagement": {"labels": [], "data": []}, "sentiment": {"labels": [], "data": []}}

    engagement_data = {"likes": sum(p['likes'] for p in brand_posts), "comments": sum(p['comments'] for p in brand_posts), "shares": sum(p['shares'] for p in brand_posts)}
    sentiment_data = {"Positive": len([p for p in brand_posts if p['sentiment'] == 'Positive']), "Negative": len([p for p in brand_posts if p['sentiment'] == 'Negative']),"Neutral": len([p for p in brand_posts if p['sentiment'] == 'Neutral'])}

    return {"engagement": {"labels": list(engagement_data.keys()), "data": list(engagement_data.values())}, "sentiment": {"labels": list(sentiment_data.keys()), "data": list(sentiment_data.values())}}

@app.on_event("startup")
def startup_event():
    threading.Thread(target=run_scheduler, daemon=True).start()
    print("Scheduler started for automated 2-day reports.")
