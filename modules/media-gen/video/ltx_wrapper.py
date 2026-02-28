"""
AMFbot LTX-Video Wrapper

Provides high-level interface for LTX-Video generation:
- Text-to-video generation
- Image-to-video generation
- Video extension
- Automatic model weight downloading

License: Apache-2.0
"""

import os
import logging
from pathlib import Path
from typing import Optional, List, Union
from dataclasses import dataclass, field

import torch
from huggingface_hub import hf_hub_download, snapshot_download
from diffusers import LTXPipeline, LTXImageToVideoPipeline
from PIL import Image

logger = logging.getLogger(__name__)

# Default model configurations
DEFAULT_MODEL = "Lightricks/LTX-Video"
DISTILLED_MODEL = "Lightricks/LTX-Video-0.9.8-distilled"
MODELS_DIR = Path(os.environ.get("AMFBOT_MODELS_DIR", "./models/ltx-video"))


@dataclass
class VideoGenerationConfig:
    """Configuration for video generation."""
    
    prompt: str
    negative_prompt: str = ""
    width: int = 768
    height: int = 512
    num_frames: int = 97  # ~4 seconds at 24fps
    num_inference_steps: int = 50
    guidance_scale: float = 7.5
    seed: Optional[int] = None
    fps: int = 24
    output_path: Optional[str] = None
    

@dataclass
class Image2VideoConfig(VideoGenerationConfig):
    """Configuration for image-to-video generation."""
    
    image_path: str = ""
    conditioning_strength: float = 1.0


class LTXVideoWrapper:
    """Wrapper for LTX-Video model."""
    
    def __init__(
        self,
        model_id: str = DISTILLED_MODEL,
        device: Optional[str] = None,
        dtype: Optional[torch.dtype] = None,
        enable_model_cpu_offload: bool = True,
    ):
        """
        Initialize LTX-Video wrapper.
        
        Args:
            model_id: HuggingFace model ID or local path
            device: Device to run on (cuda, mps, cpu)
            dtype: Model precision (float16, bfloat16, float32)
            enable_model_cpu_offload: Enable CPU offload for low VRAM
        """
        self.model_id = model_id
        self.device = device or self._detect_device()
        self.dtype = dtype or self._get_optimal_dtype()
        self.enable_cpu_offload = enable_model_cpu_offload
        
        self._text2video_pipeline: Optional[LTXPipeline] = None
        self._img2video_pipeline: Optional[LTXImageToVideoPipeline] = None
        
        logger.info(f"LTX-Video initialized: device={self.device}, dtype={self.dtype}")
    
    def _detect_device(self) -> str:
        """Detect the best available device."""
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    
    def _get_optimal_dtype(self) -> torch.dtype:
        """Get optimal dtype for the device."""
        if self.device == "cuda":
            # Use bfloat16 for newer GPUs
            if torch.cuda.is_bf16_supported():
                return torch.bfloat16
            return torch.float16
        elif self.device == "mps":
            return torch.float16
        return torch.float32
    
    def ensure_model_downloaded(self) -> Path:
        """Ensure model weights are downloaded."""
        models_dir = MODELS_DIR / self.model_id.replace("/", "_")
        
        if not models_dir.exists():
            logger.info(f"Downloading model: {self.model_id}")
            snapshot_download(
                repo_id=self.model_id,
                local_dir=models_dir,
                ignore_patterns=["*.md", "*.txt"],
            )
            logger.info("Model download complete")
        
        return models_dir
    
    def _load_text2video_pipeline(self) -> LTXPipeline:
        """Load the text-to-video pipeline."""
        if self._text2video_pipeline is None:
            logger.info("Loading text-to-video pipeline...")
            
            self._text2video_pipeline = LTXPipeline.from_pretrained(
                self.model_id,
                torch_dtype=self.dtype,
            )
            
            if self.enable_cpu_offload and self.device == "cuda":
                self._text2video_pipeline.enable_model_cpu_offload()
            else:
                self._text2video_pipeline = self._text2video_pipeline.to(self.device)
            
            logger.info("Text-to-video pipeline loaded")
        
        return self._text2video_pipeline
    
    def _load_img2video_pipeline(self) -> LTXImageToVideoPipeline:
        """Load the image-to-video pipeline."""
        if self._img2video_pipeline is None:
            logger.info("Loading image-to-video pipeline...")
            
            self._img2video_pipeline = LTXImageToVideoPipeline.from_pretrained(
                self.model_id,
                torch_dtype=self.dtype,
            )
            
            if self.enable_cpu_offload and self.device == "cuda":
                self._img2video_pipeline.enable_model_cpu_offload()
            else:
                self._img2video_pipeline = self._img2video_pipeline.to(self.device)
            
            logger.info("Image-to-video pipeline loaded")
        
        return self._img2video_pipeline
    
    def generate_video(self, config: VideoGenerationConfig) -> str:
        """
        Generate a video from text prompt.
        
        Args:
            config: Video generation configuration
            
        Returns:
            Path to generated video file
        """
        pipeline = self._load_text2video_pipeline()
        
        # Set seed for reproducibility
        generator = None
        if config.seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(config.seed)
        
        logger.info(f"Generating video: {config.prompt[:50]}...")
        
        # Generate video
        output = pipeline(
            prompt=config.prompt,
            negative_prompt=config.negative_prompt,
            width=config.width,
            height=config.height,
            num_frames=config.num_frames,
            num_inference_steps=config.num_inference_steps,
            guidance_scale=config.guidance_scale,
            generator=generator,
        )
        
        # Save video
        output_path = config.output_path or f"output_{config.seed or 'random'}.mp4"
        self._save_video(output.frames[0], output_path, config.fps)
        
        logger.info(f"Video saved to: {output_path}")
        return output_path
    
    def generate_from_image(self, config: Image2VideoConfig) -> str:
        """
        Generate a video from an input image.
        
        Args:
            config: Image-to-video configuration
            
        Returns:
            Path to generated video file
        """
        pipeline = self._load_img2video_pipeline()
        
        # Load input image
        image = Image.open(config.image_path).convert("RGB")
        image = image.resize((config.width, config.height))
        
        # Set seed for reproducibility
        generator = None
        if config.seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(config.seed)
        
        logger.info(f"Generating video from image: {config.image_path}")
        
        # Generate video
        output = pipeline(
            prompt=config.prompt,
            negative_prompt=config.negative_prompt,
            image=image,
            width=config.width,
            height=config.height,
            num_frames=config.num_frames,
            num_inference_steps=config.num_inference_steps,
            guidance_scale=config.guidance_scale,
            generator=generator,
        )
        
        # Save video
        output_path = config.output_path or f"output_img2vid_{config.seed or 'random'}.mp4"
        self._save_video(output.frames[0], output_path, config.fps)
        
        logger.info(f"Video saved to: {output_path}")
        return output_path
    
    def _save_video(self, frames: List, output_path: str, fps: int) -> None:
        """Save frames as video file."""
        try:
            from diffusers.utils import export_to_video
            export_to_video(frames, output_path, fps=fps)
        except ImportError:
            # Fallback to manual saving
            import imageio
            writer = imageio.get_writer(output_path, fps=fps)
            for frame in frames:
                writer.append_data(frame)
            writer.close()
    
    def unload(self) -> None:
        """Unload pipelines to free memory."""
        self._text2video_pipeline = None
        self._img2video_pipeline = None
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("Pipelines unloaded")
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        return {
            "model_id": self.model_id,
            "device": self.device,
            "dtype": str(self.dtype),
            "text2video_loaded": self._text2video_pipeline is not None,
            "img2video_loaded": self._img2video_pipeline is not None,
        }


# Convenience function for quick generation
def generate_video(
    prompt: str,
    output_path: str = "output.mp4",
    width: int = 768,
    height: int = 512,
    num_frames: int = 97,
    seed: Optional[int] = None,
) -> str:
    """
    Quick video generation function.
    
    Args:
        prompt: Text description of the video
        output_path: Where to save the video
        width: Video width
        height: Video height
        num_frames: Number of frames to generate
        seed: Random seed for reproducibility
        
    Returns:
        Path to the generated video
    """
    wrapper = LTXVideoWrapper()
    
    config = VideoGenerationConfig(
        prompt=prompt,
        width=width,
        height=height,
        num_frames=num_frames,
        seed=seed,
        output_path=output_path,
    )
    
    result = wrapper.generate_video(config)
    wrapper.unload()
    
    return result
