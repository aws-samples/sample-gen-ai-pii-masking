#!/bin/bash
set -e

# Configuration
LAYERS_DIR="layers"
PYTHON_VERSION="python3.12"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Starting layer build process...${NC}"

# Create layers directory
mkdir -p "$LAYERS_DIR"

# Function to build a layer
build_layer() {
    local layer_name="$1"
    local requirements_file="$2"

    echo -e "${YELLOW}Building ${layer_name} layer...${NC}"

    # Create layer directory structure
    mkdir -p "$LAYERS_DIR/${layer_name}/python"

    # Create virtual environment
    python -m venv "$LAYERS_DIR/${layer_name}/venv"
    source "$LAYERS_DIR/${layer_name}/venv/bin/activate"

    # Install dependencies
    pip install --upgrade pip
    pip install -r "$requirements_file" --target "$LAYERS_DIR/${layer_name}/python"

    # Create ZIP file
    cd "$LAYERS_DIR/${layer_name}/python"
    zip -r "../../${layer_name}-layer.zip" .
    cd ../../..

    # Cleanup
    rm -rf "$LAYERS_DIR/${layer_name}"
    
    echo -e "${GREEN}Successfully built ${layer_name} layer${NC}"
}

# Build boto3 layer
build_layer "boto3" "layers/boto3/requirements.txt"

# Build pandas layer
build_layer "pandas" "layers/pandas/requirements.txt"

echo -e "${GREEN}Layer build process completed!${NC}"