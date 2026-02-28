"""
AMFbot Flux.1 Image Wrapper

Provides high-level interface for Flux image generation:
- Text-to-image generation
- Multiple model variants (schnell, dev)
- Automatic model weight downloading

License: Apache-2.0
"""

import os
import logging
from pathlib import Path
from typing import Optional, List, Union
from dataclasses import dataclass

import torch
from huggingface_hub import snapshot_download
from diffusers import FluxPipeline
from PIL import Image

logger = logging.getLogger(__name__)

# Model configurations
FLUX_MODELS = {
    "schnell": "black-forest-labs/FLUX.1-schnell",
    "dev": "black-forest-labs/FLUX.1-dev",
}
DEFAULT_MODEL = "schnell"
MODELS_DIR = Path(os.environ.get("AMFBOT_MODELS_DIR", "./models/flux"))


@dataclass
class ImageGenerationConfig:
    """Configuration for image generation."""
    
    prompt: str
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    num_inference_steps: int = 4  # schnell is fast
    guidance_scale: float = 0.0  # schnell doesn't need guidance
    seed: Optional[int] = None
    output_path: Optional[str] = None
    num_images: int = 1


class FluxWrapper:
    """Wrapper for Flux.1 image generation model."""
    
    def __init__(
        self,
        model_variant: str = DEFAULT_MODEL,
        device: Optional[str] = None,
        dtype: Optional[torch.dtype] = None,
        enable_model_cpu_offload: bool = True,
    ):
        """
        Initialize Flux wrapper.
        
        Args:
            model_variant: Model variant (schnell, dev)
            device: Device to run on (cuda, mps, cpu)
            dtype: Model precision
            enable_model_cpu_offload: Enable CPU offload for low VRAM
        """
        if model_variant not in FLUX_MODELS:
            raise ValueError(f"Unknown model variant: {model_variant}. Choose from: {list(FLUX_MODELS.keys())}")
        
        self.model_variant = model_variant
        self.model_id = FLUX_MODELS[model_variant]
        self.device = device or self._detect_device()
        self.dtype = dtype or self._get_optimal_dtype()
        self.enable_cpu_offload = enable_model_cpu_offload
        
        self._pipeline: Optional[FluxPipeline] = None
        
        logger.info(f"Flux initialized: variant={model_variant}, device={self.device}, dtype={self.dtype}")
    
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
            if torch.cuda.is_bf16_supported():
                return torch.bfloat16
            return torch.float16
        elif self.device == "mps":
            return torch.float16
        return torch.float32
    
    def ensure_model_downloaded(self) -> Path:
        """Ensure model weights are downloaded."""
        models_dir = MODELS_DIR / self.model_variant
        
        if not models_dir.exists():
            logger.info(f"Downloading model: {self.model_id}")
            snapshot_download(
                repo_id=self.model_id,
                local_dir=models_dir,
                ignore_patterns=["*.md", "*.txt"],
            )
            logger.info("Model download complete")
        
        return models_dir
    
    def _load_pipeline(self) -> FluxPipeline:
        """Load the image generation pipeline."""
        if self._pipeline is None:
            logger.info(f"Loading Flux pipeline ({self.model_variant})...")
            
            self._pipeline = FluxPipeline.from_pretrained(
                self.model_id,
                torch_dtype=self.dtype,
            )
            
            if self.enable_cpu_offload and self.device == "cuda":
                self._pipeline.enable_model_cpu_offload()
            else:
                self._pipeline = self._pipeline.to(self.device)
            
            logger.info("Flux pipeline loaded")
        
        return self._pipeline
    
    def generate_image(self, config: ImageGenerationConfig) -> Union[str, List[str]]:
        """
        Generate image(s) from text prompt.
        
        Args:
            config: Image generation configuration
            
        Returns:
            Path to generated image file(s)
        """
        pipeline = self._load_pipeline()
        
        # Set seed for reproducibility
        generator = None
        if config.seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(config.seed)
        
        logger.info(f"Generating image: {config.prompt[:50]}...")
        
        # Adjust parameters based on model variant
        num_steps = config.num_inference_steps
        guidance = config.guidance_scale
        
        if self.model_variant == "schnell":
            # Schnell is optimized for 4 steps without guidance
            num_steps = min(num_steps, 4)
            guidance = 0.0
        elif self.model_variant == "dev":
            # Dev model benefits from more steps and guidance
            num_steps = max(num_steps, 20)
            guidance = max(guidance, 3.5)
        
        # Generate images
        output = pipeline(
            prompt=config.prompt,
            width=config.width,
            height=config.height,
            num_inference_steps=num_steps,
            guidance_scale=guidance,
            generator=generator,
            num_images_per_prompt=config.num_images,
        )
        
        # Save images
        output_paths = []
        for i, image in enumerate(output.images):
            if config.num_images == 1:
                path = config.output_path or f"output_{config.seed or 'random'}.png"
            else:
                base = config.output_path or f"output_{config.seed or 'random'}"
                name, ext = os.path.splitext(base)
                path = f"{name}_{i}{ext or '.png'}"
            
            image.save(path)
            output_paths.append(path)
            logger.info(f"Image saved to: {path}")
        
        return output_paths[0] if config.num_images == 1 else output_paths
    
    def generate_variations(
        self,
        prompt: str,
        num_variations: int = 4,
        base_seed: int = 42,
        **kwargs,
    ) -> List[str]:
        """
        Generate multiple variations of an image.
        
        Args:
            prompt: Text description
            num_variations: Number of variations to generate
            base_seed: Starting seed for reproducibility
            **kwargs: Additional config options
            
        Returns:
            List of paths to generated images
        """
        output_paths = []
        
        for i in range(num_variations):
            config = ImageGenerationConfig(
                prompt=prompt,
                seed=base_seed + i,
                output_path=f"variation_{i}.png",
                **kwargs,
            )
            path = self.generate_image(config)
            output_paths.append(path)
        
        return output_paths
    
    def unload(self) -> None:
        """Unload pipeline to free memory."""
        self._pipeline = None
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("Pipeline unloaded")
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        return {
            "model_variant": self.model_variant,
            "model_id": self.model_id,
            "device": self.device,
            "dtype": str(self.dtype),
            "pipeline_loaded": self._pipeline is not None,
        }


# Convenience function for quick generation
def generate_image(
    prompt: str,
    output_path: str = "output.png",
    width: int = 1024,
    height: int = 1024,
    model: str = "schnell",
    seed: Optional[int] = None,
) -> str:
    """
    Quick image generation function.
    
    Args:
        prompt: Text description of the image
        output_path: Where to save the image
        width: Image width
        height: Image height
        model: Model variant (schnell, dev)
        seed: Random seed for reproducibility
        
    Returns:
        Path to the generated image
    """
    wrapper = FluxWrapper(model_variant=model)
    
    config = ImageGenerationConfig(
        prompt=prompt,
        width=width,
        height=height,
        seed=seed,
        output_path=output_path,
    )
    
    result = wrapper.generate_image(config)
    wrapper.unload()
    
    return result
