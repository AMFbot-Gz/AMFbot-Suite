"""
AMFbot Model Downloader

Asynchronous download manager for AI model weights:
- LTX-Video models
- Flux.1 models
- Progress tracking
- Resume support

License: Apache-2.0
"""

import os
import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Optional, Callable, List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from huggingface_hub import hf_hub_download, snapshot_download
from tqdm import tqdm

logger = logging.getLogger(__name__)

MODELS_DIR = Path(os.environ.get("AMFBOT_MODELS_DIR", "./models"))


@dataclass
class ModelInfo:
    """Information about a downloadable model."""
    
    id: str
    name: str
    repo_id: str
    type: str  # "video" or "image"
    size_gb: float
    description: str
    required_vram_gb: float


# Available models
AVAILABLE_MODELS: List[ModelInfo] = [
    ModelInfo(
        id="ltx-video-distilled",
        name="LTX-Video 0.9.8 (Distilled)",
        repo_id="Lightricks/LTX-Video-0.9.8-distilled",
        type="video",
        size_gb=8.5,
        description="Fast video generation, optimized for consumer GPUs",
        required_vram_gb=8.0,
    ),
    ModelInfo(
        id="ltx-video-full",
        name="LTX-Video 13B",
        repo_id="Lightricks/LTX-Video",
        type="video",
        size_gb=26.0,
        description="Full quality video generation model",
        required_vram_gb=16.0,
    ),
    ModelInfo(
        id="flux-schnell",
        name="Flux.1 Schnell",
        repo_id="black-forest-labs/FLUX.1-schnell",
        type="image",
        size_gb=12.0,
        description="Ultra-fast image generation (4 steps)",
        required_vram_gb=6.0,
    ),
    ModelInfo(
        id="flux-dev",
        name="Flux.1 Dev",
        repo_id="black-forest-labs/FLUX.1-dev",
        type="image",
        size_gb=24.0,
        description="High quality image generation",
        required_vram_gb=12.0,
    ),
]


@dataclass
class DownloadProgress:
    """Progress information for a download."""
    
    model_id: str
    total_bytes: int
    downloaded_bytes: int
    current_file: str
    files_completed: int
    files_total: int
    
    @property
    def percentage(self) -> float:
        if self.total_bytes == 0:
            return 0.0
        return (self.downloaded_bytes / self.total_bytes) * 100


class ModelDownloader:
    """Asynchronous model downloader with progress tracking."""
    
    def __init__(
        self,
        models_dir: Optional[Path] = None,
        max_concurrent: int = 2,
    ):
        """
        Initialize the downloader.
        
        Args:
            models_dir: Directory to store downloaded models
            max_concurrent: Maximum concurrent downloads
        """
        self.models_dir = models_dir or MODELS_DIR
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.max_concurrent = max_concurrent
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self._active_downloads: dict = {}
    
    def get_available_models(self) -> List[ModelInfo]:
        """Get list of available models for download."""
        return AVAILABLE_MODELS
    
    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get information about a specific model."""
        for model in AVAILABLE_MODELS:
            if model.id == model_id:
                return model
        return None
    
    def is_downloaded(self, model_id: str) -> bool:
        """Check if a model is already downloaded."""
        model = self.get_model_info(model_id)
        if not model:
            return False
        
        model_dir = self.models_dir / model.type / model_id
        
        # Check for marker file
        marker = model_dir / ".download_complete"
        return marker.exists()
    
    async def download_model(
        self,
        model_id: str,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
        force: bool = False,
    ) -> Path:
        """
        Download a model asynchronously.
        
        Args:
            model_id: ID of the model to download
            progress_callback: Optional callback for progress updates
            force: Force re-download even if exists
            
        Returns:
            Path to the downloaded model
        """
        model = self.get_model_info(model_id)
        if not model:
            raise ValueError(f"Unknown model: {model_id}")
        
        if self.is_downloaded(model_id) and not force:
            model_dir = self.models_dir / model.type / model_id
            logger.info(f"Model {model_id} already downloaded at {model_dir}")
            return model_dir
        
        model_dir = self.models_dir / model.type / model_id
        model_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Starting download: {model.name} ({model.size_gb}GB)")
        
        # Track progress
        progress = DownloadProgress(
            model_id=model_id,
            total_bytes=int(model.size_gb * 1024 * 1024 * 1024),
            downloaded_bytes=0,
            current_file="",
            files_completed=0,
            files_total=1,
        )
        
        self._active_downloads[model_id] = progress
        
        try:
            # Run download in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._executor,
                self._download_sync,
                model,
                model_dir,
                progress,
                progress_callback,
            )
            
            # Create marker file
            marker = model_dir / ".download_complete"
            marker.write_text(model.repo_id)
            
            logger.info(f"Download complete: {model.name}")
            return result
            
        finally:
            del self._active_downloads[model_id]
    
    def _download_sync(
        self,
        model: ModelInfo,
        model_dir: Path,
        progress: DownloadProgress,
        callback: Optional[Callable],
    ) -> Path:
        """Synchronous download with progress tracking."""
        
        def update_progress(current: int, total: int, filename: str):
            progress.downloaded_bytes = current
            progress.total_bytes = total
            progress.current_file = filename
            if callback:
                callback(progress)
        
        # Download using huggingface_hub
        snapshot_download(
            repo_id=model.repo_id,
            local_dir=model_dir,
            ignore_patterns=["*.md", "*.txt", "*.json"],
        )
        
        return model_dir
    
    async def download_all(
        self,
        model_ids: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[str, DownloadProgress], None]] = None,
    ) -> dict:
        """
        Download multiple models concurrently.
        
        Args:
            model_ids: List of model IDs to download (all if None)
            progress_callback: Callback with (model_id, progress)
            
        Returns:
            Dict mapping model_id to download path or error
        """
        if model_ids is None:
            model_ids = [m.id for m in AVAILABLE_MODELS]
        
        results = {}
        
        async def download_with_callback(model_id: str):
            def cb(progress: DownloadProgress):
                if progress_callback:
                    progress_callback(model_id, progress)
            
            try:
                path = await self.download_model(model_id, progress_callback=cb)
                return model_id, str(path)
            except Exception as e:
                return model_id, f"error: {e}"
        
        tasks = [download_with_callback(mid) for mid in model_ids]
        completed = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in completed:
            if isinstance(result, tuple):
                model_id, path = result
                results[model_id] = path
            else:
                results[str(result)] = f"error: {result}"
        
        return results
    
    def get_active_downloads(self) -> dict:
        """Get information about active downloads."""
        return {
            mid: {
                "percentage": p.percentage,
                "current_file": p.current_file,
                "downloaded_gb": p.downloaded_bytes / (1024 * 1024 * 1024),
            }
            for mid, p in self._active_downloads.items()
        }
    
    def get_downloaded_models(self) -> List[str]:
        """Get list of downloaded model IDs."""
        downloaded = []
        for model in AVAILABLE_MODELS:
            if self.is_downloaded(model.id):
                downloaded.append(model.id)
        return downloaded
    
    def get_total_size(self, model_ids: Optional[List[str]] = None) -> float:
        """Get total size of models in GB."""
        if model_ids is None:
            model_ids = [m.id for m in AVAILABLE_MODELS]
        
        total = 0.0
        for model in AVAILABLE_MODELS:
            if model.id in model_ids:
                total += model.size_gb
        return total
    
    def cleanup(self, model_id: str) -> bool:
        """Remove a downloaded model."""
        model = self.get_model_info(model_id)
        if not model:
            return False
        
        model_dir = self.models_dir / model.type / model_id
        
        if model_dir.exists():
            import shutil
            shutil.rmtree(model_dir)
            logger.info(f"Removed model: {model_id}")
            return True
        
        return False


# CLI interface
async def main():
    """CLI for downloading models."""
    import sys
    
    downloader = ModelDownloader()
    
    if len(sys.argv) < 2:
        print("Usage: python downloader.py <command> [args]")
        print("\nCommands:")
        print("  list          - List available models")
        print("  status        - Show download status")
        print("  download <id> - Download a model")
        print("  download-all  - Download all models")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        print("\nAvailable models:\n")
        for model in downloader.get_available_models():
            downloaded = "✓" if downloader.is_downloaded(model.id) else " "
            print(f"  [{downloaded}] {model.id}")
            print(f"      {model.name} ({model.size_gb}GB)")
            print(f"      {model.description}")
            print(f"      Requires: {model.required_vram_gb}GB VRAM")
            print()
    
    elif command == "status":
        downloaded = downloader.get_downloaded_models()
        print(f"\nDownloaded models: {len(downloaded)}/{len(AVAILABLE_MODELS)}")
        for mid in downloaded:
            print(f"  ✓ {mid}")
    
    elif command == "download":
        if len(sys.argv) < 3:
            print("Usage: python downloader.py download <model_id>")
            return
        
        model_id = sys.argv[2]
        
        def progress_cb(progress: DownloadProgress):
            print(f"\r  {progress.percentage:.1f}% - {progress.current_file}", end="")
        
        print(f"Downloading {model_id}...")
        path = await downloader.download_model(model_id, progress_callback=progress_cb)
        print(f"\n✓ Downloaded to: {path}")
    
    elif command == "download-all":
        print("Downloading all models...")
        
        def progress_cb(model_id: str, progress: DownloadProgress):
            print(f"\r  [{model_id}] {progress.percentage:.1f}%", end="")
        
        results = await downloader.download_all(progress_callback=progress_cb)
        print("\n\nResults:")
        for mid, path in results.items():
            status = "✓" if not path.startswith("error") else "✗"
            print(f"  {status} {mid}: {path}")


if __name__ == "__main__":
    asyncio.run(main())
