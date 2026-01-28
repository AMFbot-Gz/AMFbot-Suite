#!/bin/bash
#
# AMFbot Model Downloader
# Downloads AI model weights for local generation
#
# Usage:
#   bash scripts/download_models.sh [--video] [--image] [--all]
#

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

MODELS_DIR="${AMFBOT_MODELS_DIR:-./models}"

download_video_models() {
    echo -e "${GREEN}Downloading LTX-Video models...${NC}"
    
    # Using Python's huggingface_hub
    python3 -c "
from huggingface_hub import snapshot_download
import os

models_dir = os.environ.get('AMFBOT_MODELS_DIR', './models')

print('Downloading LTX-Video 0.9.8 (distilled)...')
snapshot_download(
    repo_id='Lightricks/LTX-Video-0.9.8-distilled',
    local_dir=f'{models_dir}/ltx-video/distilled',
    ignore_patterns=['*.md', '*.txt']
)
print('✓ LTX-Video download complete')
"
}

download_image_models() {
    echo -e "${GREEN}Downloading Flux.1 models...${NC}"
    
    python3 -c "
from huggingface_hub import snapshot_download
import os

models_dir = os.environ.get('AMFBOT_MODELS_DIR', './models')

print('Downloading Flux.1 Schnell...')
snapshot_download(
    repo_id='black-forest-labs/FLUX.1-schnell',
    local_dir=f'{models_dir}/flux/schnell',
    ignore_patterns=['*.md', '*.txt']
)
print('✓ Flux.1 Schnell download complete')
"
}

main() {
    mkdir -p "$MODELS_DIR"
    
    case "${1:-all}" in
        --video)
            download_video_models
            ;;
        --image)
            download_image_models
            ;;
        --all|*)
            download_video_models
            download_image_models
            ;;
    esac
    
    echo -e "${GREEN}All requested models downloaded to $MODELS_DIR${NC}"
}

main "$@"
