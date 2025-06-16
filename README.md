# Government Gazette Notice Processing System

A comprehensive system for parsing PDF government gazettes, extracting structured notice information, and generating formatted bulletins in multiple output formats.

## Features

- **Multi-strategy PDF parsing** - Handles various gazette formats with fallback strategies
- **AI-powered text analysis** - Uses Claude API for intelligent notice extraction
- **Comprehensive caching** - PDF text and LLM response caching for performance
- **Multiple output formats** - Markdown, PDF, and DOCX bulletin generation
- **Web interface** - Streamlit app for PDF annotation and processing
- **CLI interface** - Command-line tools for automated processing

## Quick Start

### Prerequisites

- Python 3.8+
- Rye package manager
- Anthropic API key

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd ongoing_convo_with_bronn_2025_06_10

# Install dependencies
rye sync

# Set up environment
export ANTHROPIC_API_KEY=your_api_key_here
```

### Basic Usage

```bash
# Generate bulletin from notices.csv
rye run python bb_logic.py bulletin

# Generate bulletin using all available PDFs
rye run python bb_logic.py bulletin2

# Launch web interface
rye run streamlit run streamlit_app.py

# Run complete development workflow
./utils/test.sh
```

## Architecture

### Core Components

- **bb_logic.py** - Main CLI application with Click framework
- **streamlit_app.py** - Web interface with password protection
- **src/ongoing_convo_with_bronn_2025_06_10/** - Core processing modules

### Key Modules

| Module | Purpose |
|--------|---------|
| `cached_llm.py` | Claude API wrapper with MD5-based caching |
| `utils.py` | PDF processing utilities with multi-strategy parsing |
| `common_types.py` | Pydantic models for Notice, MajorType, and Act |
| `pdf_parser_*.py` | Three different PDF parsing strategies |
| `validation_helpers.py` | Pydantic configuration utilities |

### Processing Pipeline

1. **Input** - Read notice specifications from `notices.csv`
2. **PDF Processing** - Download/locate and extract text from gazette PDFs
3. **Text Analysis** - Use Claude API to analyze and structure notice content
4. **Validation** - Validate extracted data with Pydantic models
5. **Output** - Generate formatted bulletins in multiple formats

## Development

### Testing & Quality Assurance

```bash
# Run all tests with coverage
rye run pytest tests/ --cov=bb_logic --cov-report=term-missing

# Type checking
rye run mypy --strict src/ongoing_convo_with_bronn_2025_06_10/*.py

# Code formatting
rye run black .
rye run isort .
```

### Supported Notice Types

- **GenN** - General Notices
- **GN** - Government Notices  
- **BN** - Board Notices
- **Proc** - Proclamations

### Caching System

The system implements multi-level caching:

- **PDF Text Cache** - MD5-based caching in `cache/` directory
- **LLM Response Cache** - JSON-based caching of Claude API responses
- **Notice Cache** - Serialization caching for notice validation

## Output Formats

### Bulletin Generation

The system generates bulletins in three formats:

- **Markdown** - Primary format with government gazette citations
- **PDF** - Generated via pandoc with XeLaTeX engine
- **DOCX** - Complete with table of contents and metadata

### Sample Output Structure

```markdown
# Government Gazette Bulletin

## General Notices (GenN)
- [Notice Title] - [Citation]

## Government Notices (GN)  
- [Notice Title] - [Citation]

## Board Notices (BN)
- [Notice Title] - [Citation]
```

## Configuration

### Environment Variables

```bash
ANTHROPIC_API_KEY=your_claude_api_key
```

### Input Files

- `notices.csv` - Notice specifications and metadata
- PDF gazette files - Processed automatically or via web interface

## Web Interface

The Streamlit web application provides:

- Password-protected access
- PDF upload and annotation
- Real-time processing status
- Bulletin preview and download

Launch with:
```bash
rye run streamlit run streamlit_app.py
```

## Contributing

1. Follow the existing code style (enforced by black and isort)
2. Add type hints for all functions (checked by mypy --strict)
3. Write tests for new functionality
4. Run `./utils/test.sh` before committing

## License

[Add your license information here]

## Support

For issues or questions, please check the existing documentation in `CLAUDE.md` or create an issue in the repository.