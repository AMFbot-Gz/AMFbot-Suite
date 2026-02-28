"""
AMFbot Media Generation API Server

FastAPI server providing REST endpoints for:
- Image generation (Flux)
- Video generation (LTX-Video)
- Model management
- Health checks

License: Apache-2.0
"""

import os
import uuid
import asyncio
import logging
from pathlib import Path
from typing import Optional, Literal
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Conditional imports for AI models
try:
    from video.ltx_wrapper import LTXVideoWrapper, VideoGenerationConfig
    HAS_VIDEO = True
except ImportError:
    HAS_VIDEO = False

try:
    from image.flux_wrapper import FluxWrapper, ImageGenerationConfig
    HAS_IMAGE = True
except ImportError:
    HAS_IMAGE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Generation state
class GenerationState:
    video_wrapper: Optional["LTXVideoWrapper"] = None
    image_wrapper: Optional["FluxWrapper"] = None
    jobs: dict = {}

state = GenerationState()

# Output directory
OUTPUT_DIR = Path(os.environ.get("AMFBOT_OUTPUT_DIR", "./outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting AMFbot Media Generation Server")
    logger.info(f"Video generation available: {HAS_VIDEO}")
    logger.info(f"Image generation available: {HAS_IMAGE}")
    yield
    # Cleanup on shutdown
    if state.video_wrapper:
        state.video_wrapper.unload()
    if state.image_wrapper:
        state.image_wrapper.unload()
    logger.info("Server shutdown complete")


app = FastAPI(
    title="AMFbot Media Generation API",
    description="REST API for AI-powered image and video generation",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class ImageRequest(BaseModel):
    prompt: str = Field(..., description="Text description of the image")
    negative_prompt: str = Field("", description="What to avoid in the image")
    width: int = Field(1024, ge=256, le=2048, description="Image width")
    height: int = Field(1024, ge=256, le=2048, description="Image height")
    model: Literal["schnell", "dev"] = Field("schnell", description="Flux model variant")
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")
    num_images: int = Field(1, ge=1, le=4, description="Number of images to generate")


class VideoRequest(BaseModel):
    prompt: str = Field(..., description="Text description of the video")
    negative_prompt: str = Field("", description="What to avoid in the video")
    width: int = Field(768, ge=256, le=1280, description="Video width")
    height: int = Field(512, ge=256, le=720, description="Video height")
    num_frames: int = Field(97, ge=25, le=257, description="Number of frames")
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")
    image_path: Optional[str] = Field(None, description="Input image for img2vid")


class JobResponse(BaseModel):
    job_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    result: Optional[str] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    video_available: bool
    image_available: bool
    video_loaded: bool
    image_loaded: bool


# Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check server health and available capabilities."""
    return HealthResponse(
        status="healthy",
        video_available=HAS_VIDEO,
        image_available=HAS_IMAGE,
        video_loaded=state.video_wrapper is not None,
        image_loaded=state.image_wrapper is not None,
    )


@app.post("/api/generate/image", response_model=JobResponse)
async def generate_image(request: ImageRequest, background_tasks: BackgroundTasks):
    """
    Generate an image from text prompt.
    Returns a job ID to track progress.
    """
    if not HAS_IMAGE:
        raise HTTPException(
            status_code=503,
            detail="Image generation not available. Install Flux dependencies.",
        )
    
    job_id = str(uuid.uuid4())
    state.jobs[job_id] = {"status": "pending"}
    
    background_tasks.add_task(process_image_generation, job_id, request)
    
    return JobResponse(job_id=job_id, status="pending")


async def process_image_generation(job_id: str, request: ImageRequest):
    """Background task for image generation."""
    try:
        state.jobs[job_id]["status"] = "processing"
        
        # Initialize wrapper if needed
        if state.image_wrapper is None or state.image_wrapper.model_variant != request.model:
            if state.image_wrapper:
                state.image_wrapper.unload()
            state.image_wrapper = FluxWrapper(model_variant=request.model)
        
        # Generate image
        output_path = OUTPUT_DIR / f"{job_id}.png"
        
        config = ImageGenerationConfig(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            width=request.width,
            height=request.height,
            seed=request.seed,
            output_path=str(output_path),
            num_images=request.num_images,
        )
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, state.image_wrapper.generate_image, config
        )
        
        state.jobs[job_id] = {
            "status": "completed",
            "result": result if isinstance(result, str) else result[0],
        }
        
    except Exception as e:
        logger.exception(f"Image generation failed: {e}")
        state.jobs[job_id] = {"status": "failed", "error": str(e)}


@app.post("/api/generate/video", response_model=JobResponse)
async def generate_video(request: VideoRequest, background_tasks: BackgroundTasks):
    """
    Generate a video from text prompt.
    Returns a job ID to track progress.
    """
    if not HAS_VIDEO:
        raise HTTPException(
            status_code=503,
            detail="Video generation not available. Install LTX-Video dependencies.",
        )
    
    job_id = str(uuid.uuid4())
    state.jobs[job_id] = {"status": "pending"}
    
    background_tasks.add_task(process_video_generation, job_id, request)
    
    return JobResponse(job_id=job_id, status="pending")


async def process_video_generation(job_id: str, request: VideoRequest):
    """Background task for video generation."""
    try:
        state.jobs[job_id]["status"] = "processing"
        
        # Initialize wrapper if needed
        if state.video_wrapper is None:
            state.video_wrapper = LTXVideoWrapper()
        
        # Generate video
        output_path = OUTPUT_DIR / f"{job_id}.mp4"
        
        config = VideoGenerationConfig(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            width=request.width,
            height=request.height,
            num_frames=request.num_frames,
            seed=request.seed,
            output_path=str(output_path),
        )
        
        # Run in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, state.video_wrapper.generate_video, config
        )
        
        state.jobs[job_id] = {"status": "completed", "result": result}
        
    except Exception as e:
        logger.exception(f"Video generation failed: {e}")
        state.jobs[job_id] = {"status": "failed", "error": str(e)}


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """Get the status of a generation job."""
    if job_id not in state.jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = state.jobs[job_id]
    return JobResponse(
        job_id=job_id,
        status=job["status"],
        result=job.get("result"),
        error=job.get("error"),
    )


@app.get("/api/download/{job_id}")
async def download_result(job_id: str):
    """Download the generated file."""
    if job_id not in state.jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = state.jobs[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Job status: {job['status']}")
    
    file_path = Path(job["result"])
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Generated file not found")
    
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="image/png" if file_path.suffix == ".png" else "video/mp4",
    )


@app.post("/api/models/unload")
async def unload_models():
    """Unload all models to free memory."""
    if state.video_wrapper:
        state.video_wrapper.unload()
        state.video_wrapper = None
    
    if state.image_wrapper:
        state.image_wrapper.unload()
        state.image_wrapper = None
    
    return {"message": "All models unloaded"}


@app.get("/api/models/info")
async def get_models_info():
    """Get information about loaded models."""
    return {
        "video": state.video_wrapper.get_model_info() if state.video_wrapper else None,
        "image": state.image_wrapper.get_model_info() if state.image_wrapper else None,
    }


def main():
    """Run the server."""
    import uvicorn
    
    port = int(os.environ.get("AMFBOT_MEDIA_PORT", 8765))
    host = os.environ.get("AMFBOT_MEDIA_HOST", "0.0.0.0")
    
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
