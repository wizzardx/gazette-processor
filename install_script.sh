#!/bin/bash
# Complete installation script for Enhanced OCR Module using Rye
# Run with: bash install_enhanced_ocr.sh

set -e

echo "🚀 Installing Enhanced OCR Module Dependencies with Rye..."

# Update package list
echo "📦 Updating package list..."
sudo apt update

# Install system dependencies
echo "🔧 Installing system packages..."
sudo apt install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-osd \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgcc-s1 \
    build-essential \
    cmake \
    pkg-config \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    python3-dev \
    curl

# Install additional Tesseract language packs
echo "🌍 Installing additional language packs..."
sudo apt install -y \
    tesseract-ocr-fra \
    tesseract-ocr-deu \
    tesseract-ocr-spa \
    tesseract-ocr-ita \
    tesseract-ocr-por \
    tesseract-ocr-rus \
    tesseract-ocr-chi-sim \
    tesseract-ocr-chi-tra \
    tesseract-ocr-jpn \
    tesseract-ocr-kor 2>/dev/null || echo "Some language packs not available"

# Install Rye if not already installed
echo "🔥 Checking Rye installation..."
if ! command -v rye &> /dev/null; then
    echo "📥 Installing Rye..."
    curl -sSf https://rye-up.com/get | bash
    echo 'source "$HOME/.rye/env"' >> ~/.bashrc
    source "$HOME/.rye/env"
    export PATH="$HOME/.rye/shims:$PATH"
else
    echo "✅ Rye already installed: $(rye --version)"
fi

# Ensure rye is in PATH for this session
export PATH="$HOME/.rye/shims:$PATH"

# Initialize rye project if pyproject.toml doesn't exist
if [ ! -f "pyproject.toml" ]; then
    echo "🆕 Initializing new Rye project..."
    rye init --name enhanced-ocr --py 3.11
    cd enhanced-ocr || exit 1
else
    echo "✅ Using existing Rye project"
fi

# Sync to ensure we have a virtual environment
echo "🔄 Syncing Rye environment..."
rye sync

# Add core Python dependencies
echo "🐍 Adding core Python dependencies..."
rye add pdf2image
rye add Pillow
rye add opencv-python
rye add numpy
rye add pytesseract

# Add optional dependencies
echo "✨ Adding optional dependencies..."
rye add tqdm
rye add click

# Detect GPU and install appropriate PyTorch/EasyOCR
echo "🔍 Detecting GPU support..."
if command -v nvidia-smi &> /dev/null; then
    echo "🎮 NVIDIA GPU detected, adding CUDA-enabled packages..."
    rye add torch
    rye add torchvision
    rye add easyocr
else
    echo "💻 No NVIDIA GPU detected, adding CPU-only packages..."
    # For CPU-only torch, we need to specify the index URL
    # Rye doesn't directly support index URLs like pip, so we'll add normally
    # and let torch auto-detect CPU usage
    rye add torch
    rye add torchvision
    rye add easyocr
    echo "ℹ️  Note: PyTorch will use CPU-only mode automatically"
fi

# Sync to install all dependencies
echo "🔄 Installing all dependencies..."
rye sync

# Verify installations
echo "✅ Verifying installations..."

# Test Tesseract
if tesseract --version > /dev/null 2>&1; then
    echo "✅ Tesseract OCR: $(tesseract --version | head -n1)"
else
    echo "❌ Tesseract OCR installation failed"
    exit 1
fi

# Test poppler
if pdftoppm -h > /dev/null 2>&1; then
    echo "✅ Poppler utilities: Available"
else
    echo "❌ Poppler utilities installation failed"
    exit 1
fi

# Test Python packages using rye run
echo "🧪 Testing Python packages..."
rye run python -c "
import sys
packages = [
    'pdf2image', 'PIL', 'cv2', 'numpy', 'pytesseract'
]
optional_packages = ['easyocr', 'torch', 'tqdm']

failed = []
for pkg in packages:
    try:
        __import__(pkg)
        print(f'✅ {pkg}: Available')
    except ImportError:
        print(f'❌ {pkg}: FAILED')
        failed.append(pkg)

for pkg in optional_packages:
    try:
        __import__(pkg)
        print(f'✅ {pkg}: Available')
    except ImportError:
        print(f'⚠️  {pkg}: Not available (optional)')

if failed:
    print(f'❌ Critical packages failed: {failed}')
    sys.exit(1)
else:
    print('🎉 All critical packages installed successfully!')
"

# Show current dependencies
echo ""
echo "📋 Current project dependencies:"
rye list

echo ""
echo "🎉 Installation completed successfully!"
echo ""
echo "📖 Usage examples:"
echo "  # Copy enhanced_ocr.py to your project directory, then:"
echo "  rye run python enhanced_ocr.py document.pdf"
echo "  rye run python enhanced_ocr.py document.pdf --pages 1-5 --engine tesseract"
echo ""
echo "  # Or activate the environment and run directly:"
echo "  rye shell"
echo "  python enhanced_ocr.py document.pdf"
echo ""
echo "  # Or in Python scripts:"
echo "  rye run python -c \"from enhanced_ocr import extract_pdf_text; print(extract_pdf_text('doc.pdf'))\""
echo ""
echo "🔧 Project management with Rye:"
echo "  rye sync          # Install/update dependencies"
echo "  rye add [package] # Add new dependency"
echo "  rye remove [pkg]  # Remove dependency"
echo "  rye shell         # Activate virtual environment"
echo "  rye run [command] # Run command in virtual environment"
echo ""
echo "🔧 Optional: Install additional Tesseract language packs:"
echo "  sudo apt install tesseract-ocr-[language_code]"
echo "  # Available languages: tesseract --list-langs"
echo ""
echo "📁 Project structure:"
echo "  enhanced-ocr/"
echo "  ├── pyproject.toml     # Project configuration (managed by Rye)"
echo "  ├── README.md"
echo "  ├── enhanced_ocr.py    # Your OCR module (copy here)"
echo "  └── .venv/             # Virtual environment (managed by Rye)"