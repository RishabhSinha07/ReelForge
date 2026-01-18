from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import json
import logging
from reel_orchestrator import orchestrate_reel
from pydantic import BaseModel
from typing import List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ReelForge API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock database or file-based tracking
REELS_DB_FILE = "reels_status.json"

def load_db():
    if os.path.exists(REELS_DB_FILE):
        with open(REELS_DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db(db):
    with open(REELS_DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

class ReelRequest(BaseModel):
    idea: str
    theme: str
    name: str
    duration: int = 30

@app.post("/generate")
async def generate_reel(request: ReelRequest, background_tasks: BackgroundTasks):
    db = load_db()
    if request.name in db and db[request.name]["status"] == "processing":
        raise HTTPException(status_code=400, detail="Reel with this name is already being processed")
    
    db[request.name] = {
        "idea": request.idea,
        "theme": request.theme,
        "duration": request.duration,
        "status": "processing",
        "video_path": None
    }
    save_db(db)
    
    background_tasks.add_task(
        run_orchestration, 
        request.idea, 
        request.theme, 
        request.name, 
        request.duration
    )
    return {"message": "Generation started", "reel_name": request.name}

def run_orchestration(idea, theme, name, duration):
    try:
        video_path = orchestrate_reel(
            idea, 
            theme, 
            name, 
            duration=duration
        )
        db = load_db()
        if video_path:
            # We want the path relative to the static route
            # orchestrate_reel returns something like "output/reel_name/reel_name.mp4"
            # We serve the whole 'output' folder at /videos/
            # So the URL will be /videos/reel_name/reel_name.mp4
            db[name]["status"] = "completed"
            db[name]["video_path"] = f"/videos/{name}/{name}.mp4"
        else:
            db[name]["status"] = "failed"
        save_db(db)
    except Exception as e:
        logger.error(f"Error generating reel {name}: {e}")
        db = load_db()
        db[name]["status"] = "failed"
        save_db(db)

@app.get("/reels")
async def list_reels():
    db = load_db()
    # Also scan the output folder to sync if needed
    output_dir = "output"
    if os.path.exists(output_dir):
        for name in os.listdir(output_dir):
            reel_path = os.path.join(output_dir, name)
            if os.path.isdir(reel_path):
                video_file = os.path.join(reel_path, f"{name}.mp4")
                if os.path.exists(video_file) and name not in db:
                    db[name] = {
                        "idea": "Imported",
                        "theme": "Imported",
                        "status": "completed",
                        "video_path": f"/videos/{name}/{name}.mp4"
                    }
    
    return [{"name": k, **v} for k, v in db.items()]

@app.get("/status/{name}")
async def get_status(name: str):
    db = load_db()
    if name not in db:
        raise HTTPException(status_code=404, detail="Reel not found")
    return db[name]

@app.get("/config")
async def get_config():
    return {"status": "ok"}

# Serve the output directory as static files
if not os.path.exists("output"):
    os.makedirs("output")
app.mount("/videos", StaticFiles(directory="output"), name="videos")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
