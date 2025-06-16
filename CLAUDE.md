# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a government gazette notice processing system that:
- Parses PDF government gazettes using multiple parsing strategies  
- Extracts structured notice information using Claude API for text analysis
- Generates formatted bulletin output in Markdown, PDF, and DOCX formats
- Maintains a comprehensive caching system for both PDF text extraction and LLM responses

## Development Commands

### Testing & Quality Assurance
```bash
# Run the complete development workflow
./utils/test.sh

# Individual commands:
rye run pytest tests/ --cov=bb_logic --cov-report=term-missing  # Run tests with coverage
rye run mypy --strict src/ongoing_convo_with_bronn_2025_06_10/*.py  # Type checking
rye run isort .  # Sort imports
rye run black .  # Format code
rye fmt  # Rye's built-in formatter
```

### Running the Application
```bash
# CLI Commands (using Click)
rye run python bb_logic.py bulletin      # Generate bulletin from notices.csv
rye run python bb_logic.py bulletin2     # Generate bulletin using all available PDFs

# Generate output files
rye run python bb_logic.py bulletin > output/output.md  # Generate markdown output

# Web Interface
rye run streamlit run streamlit_app.py   # Launch Streamlit web UI for PDF annotation
```

### Package Management
```bash
rye add <package>  # Add dependencies
rye sync  # Sync dependencies
rye run <command>  # Run commands in virtual environment
```

## Architecture

### Core Components

**bb_logic.py**: Main CLI application using Click framework with commands for bulletin generation

**streamlit_app.py**: Web interface for PDF annotation and processing with password protection

**src/ongoing_convo_with_bronn_2025_06_10/**:
- `cached_llm.py`: Claude API wrapper with MD5-based caching system
- `utils.py`: PDF processing utilities with multi-strategy parsing
- `utils_2.py`: Extended utilities for processing all available PDFs
- `common_types.py`: Pydantic models for Notice, MajorType enum, and Act
- `pdf_parser_*.py`: Three different PDF parsing strategies for various notice formats
- `validation_helpers.py`: Pydantic configuration utilities
- `prints.py`: Output formatting utilities

### PDF Processing Strategy

The system uses three parsing approaches to handle different gazette formats:
1. Single notice PDFs
2. Multi-notice PDFs  
3. Multi-notice PDFs with leading "R" notices

Each parser attempts to extract structured notice information, falling back to the next strategy if parsing fails.

### Caching System

- **PDF Text Cache**: MD5-based caching of extracted PDF text in `cache/` directory
- **LLM Response Cache**: JSON-based caching of Claude API responses to avoid duplicate calls
- **Notice Cache**: JSON serialization caching for notice validation

### Data Flow

1. Read notice specifications from `notices.csv`
2. Download/locate PDF gazette files  
3. Extract text using cached PDF processing
4. Analyze text structure using cached Claude API calls
5. Generate structured Notice objects with Pydantic validation
6. Format output as bulletin with proper government gazette citations

## Environment Setup

Required environment variables:
- `ANTHROPIC_API_KEY`: Claude API key for text analysis

## Output Formats

The system generates:
- Markdown bulletin format (stdout/output.md)
- PDF via pandoc with XeLaTeX engine
- DOCX with table of contents and metadata

### Document Generation Pipeline
The `./utils/test.sh` script runs the complete pipeline:
1. Code formatting and linting
2. Type checking with mypy
3. Test execution with coverage
4. Bulletin generation
5. PDF and DOCX conversion using pandoc

## Notice Types

The system processes these government notice types:
- General Notices (GenN)
- Government Notices (GN) 
- Board Notices (BN)
- Proclamations (Proc)