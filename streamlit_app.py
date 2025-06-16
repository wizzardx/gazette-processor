import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st

# Add the project root to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from ongoing_convo_with_bronn_2025_06_10.cached_llm import CachedLLM
from ongoing_convo_with_bronn_2025_06_10.common_types import Notice
from ongoing_convo_with_bronn_2025_06_10.utils import (
    get_notice_for_gg_num,
    output_testing_bulletin,
    parse_gg_filename,
)

# SHA256 Hash of the password for users to use this applet.
TARGET_HASH = "332ae4926cbb3e66ecb24b356318eacac8470cf8fba264fafa3238c710dc87dd"

# Global variable to store the file server port
FILE_SERVER_PORT = None


class PDFFileHandler(SimpleHTTPRequestHandler):
    """Custom file handler for serving PDFs with proper MIME types"""

    def __init__(self, *args, **kwargs):
        # Set the directory to serve files from
        self.pdf_directory = "streamlit_app_data/pdf_files"
        super().__init__(*args, directory=self.pdf_directory, **kwargs)

    def end_headers(self):
        # Add CORS headers to allow cross-origin requests
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET")
        self.send_header("Access-Control-Allow-Headers", "*")
        super().end_headers()

    def guess_type(self, path):
        # Ensure PDFs are served with correct MIME type
        if path.lower().endswith(".pdf"):
            return "application/pdf"
        return super().guess_type(path)


def find_free_port():
    """Find a free port to use for the file server"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def start_file_server():
    """Start a background HTTP server for serving PDF files"""
    global FILE_SERVER_PORT

    # Check for required environment variable
    server_host = os.environ.get("PDF_SERVER_HOST")
    if not server_host:
        raise RuntimeError(
            "PDF_SERVER_HOST environment variable is required. "
            "Set it to the hostname where the PDF server should be hosted (e.g., 'localhost', 'example.com', or '0.0.0.0')"
        )

    # Only start if not already running
    if FILE_SERVER_PORT is not None:
        return FILE_SERVER_PORT

    # Check for PDF_SERVER_PORT environment variable
    server_port_env = os.environ.get("PDF_SERVER_PORT")
    if server_port_env:
        try:
            FILE_SERVER_PORT = int(server_port_env)
        except ValueError:
            raise RuntimeError(
                f"PDF_SERVER_PORT environment variable must be a valid integer, got: {server_port_env}"
            )
    else:
        # Find a free port if PDF_SERVER_PORT is not specified
        FILE_SERVER_PORT = find_free_port()

    # Create the PDF directory if it doesn't exist
    pdf_dir = "streamlit_app_data/pdf_files"
    os.makedirs(pdf_dir, exist_ok=True)

    def run_server():
        try:
            server = HTTPServer((server_host, FILE_SERVER_PORT), PDFFileHandler)
            server.serve_forever()
        except Exception as e:
            print(f"File server error: {e}")

    # Start server in daemon thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Give the server a moment to start
    time.sleep(0.5)

    return FILE_SERVER_PORT


def get_pdf_url(filename):
    """Get the URL for viewing a PDF file"""
    global FILE_SERVER_PORT

    if FILE_SERVER_PORT is None:
        FILE_SERVER_PORT = start_file_server()

    # Get the server host from environment variable
    server_host = os.environ.get("PDF_SERVER_HOST", "localhost")

    # URL encode the filename to handle special characters
    encoded_filename = quote(filename)
    return f"http://{server_host}:{FILE_SERVER_PORT}/{encoded_filename}"


def hash_password(password):
    """Convert password string to SHA256 hash"""
    return hashlib.sha256(password.strip().encode()).hexdigest()


def is_valid_filename(filename):
    """Check if filename contains a 5-digit sequence starting with 5"""
    # Remove the extension to get the base filename
    base_name = os.path.splitext(filename)[0]

    # Pattern to find exactly 5-digit sequences starting with 5
    # (?<!\d) ensures no digit before, (?!\d) ensures no digit after
    pattern = r"(?<!\d)5\d{4}(?!\d)"

    # Check if pattern exists in the filename
    return bool(re.search(pattern, base_name))


def check_password():
    """Returns True if the user has entered the correct password"""

    # Initialize session state
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    # Return True if password was already entered correctly
    if st.session_state["password_correct"]:
        return True

    # Password input form
    with st.form("password_form"):
        st.write("### 🔐 Authentication Required")
        password = st.text_input("Enter password:", type="password")
        submit = st.form_submit_button("Submit")

        if submit:
            password_hash = hash_password(password)

            if password_hash == TARGET_HASH:
                st.session_state["password_correct"] = True
                st.success("✅ Password correct! Access granted.")
                st.rerun()
            else:
                st.error("❌ Incorrect password. Please try again.")
                # Optionally show the hash for debugging
                with st.expander("Debug info"):
                    st.code(f"Your hash: {password_hash}")
                    st.code(f"Target hash: {TARGET_HASH}")

    return False


def home_page():
    """Main dashboard page"""
    st.title("🏛️ Government Gazette Annotation System")
    st.write("Welcome to the GG PDF annotation platform.")

    # Add your main application content here
    st.markdown("---")
    st.subheader("System Overview")

    # Example content
    col1, col2 = st.columns(2)

    with col1:
        st.write("### 📄 Upload GG PDFs")
        st.write(
            "Upload Government Gazette PDF files with valid 5-digit IDs starting with 5."
        )
        if st.button("Go to Upload Page"):
            st.session_state["current_page"] = "📄 Upload GG PDF Files"
            st.rerun()

    with col2:
        st.write("### ✏️ Annotate Documents")
        st.write("Add publication dates and notice numbers to GG documents.")
        if st.button("Go to Annotation Page"):
            st.session_state["current_page"] = "✏️ Annotate GG PDF Files"
            st.rerun()

    # Add more features
    st.markdown("---")
    st.write("### 📰 Generate Bulletin")
    st.write("Generate formatted bulletin from annotated PDFs.")
    if st.button("Generate Bulletin", type="primary"):
        st.session_state["current_page"] = "📰 Generate Bulletin"
        st.rerun()

    st.markdown("---")
    st.write("### Quick Stats")

    # Check for existing files and annotations
    storage_dir = "streamlit_app_data/pdf_files"
    annotations_dir = "streamlit_app_data/annotations"

    total_pdfs = 0
    annotated_pdfs = 0
    total_notices = 0

    if os.path.exists(storage_dir):
        valid_pdfs = [
            f
            for f in os.listdir(storage_dir)
            if f.endswith(".pdf") and is_valid_filename(f)
        ]
        total_pdfs = len(valid_pdfs)

        if os.path.exists(annotations_dir):
            for pdf in valid_pdfs:
                annotation_file = os.path.join(
                    annotations_dir, f"{os.path.splitext(pdf)[0]}.json"
                )
                if os.path.exists(annotation_file):
                    try:
                        with open(annotation_file, "r") as f:
                            annotations = json.load(f)
                            if isinstance(annotations, dict) and annotations.get(
                                "publication_date"
                            ):
                                annotated_pdfs += 1
                                total_notices += len(
                                    annotations.get("notice_numbers", [])
                                )
                    except:
                        pass

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total GG PDFs", total_pdfs)

    with col2:
        st.metric("Annotated PDFs", annotated_pdfs)

    with col3:
        st.metric("Total Notice Numbers", total_notices)


def upload_pdf_page():
    """Page for uploading GG PDF files"""
    st.title("📄 Upload Government Gazette PDF Files")
    st.write("Upload Government Gazette documents for annotation.")

    st.markdown("---")

    # Define the storage directory
    storage_dir = "streamlit_app_data/pdf_files"

    # File uploader
    uploaded_files = st.file_uploader(
        "Choose PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        help="Select one or more PDF files to upload",
    )

    if uploaded_files:
        # Validate filenames
        valid_files = []
        invalid_files = []

        for file in uploaded_files:
            if is_valid_filename(file.name):
                valid_files.append(file)
            else:
                invalid_files.append(file)

        # Display validation results
        if valid_files:
            st.success(f"✅ {len(valid_files)} valid file(s) ready for processing")

        if invalid_files:
            st.error(
                f"❌ {len(invalid_files)} invalid file(s) - filenames must contain a 5-digit sequence starting with 5"
            )
            with st.expander("Invalid files details"):
                for file in invalid_files:
                    st.write(
                        f"- **{file.name}** - Missing 5-digit sequence starting with 5"
                    )

        # Store valid files in session state
        st.session_state["uploaded_pdfs"] = valid_files

        # Display valid files info
        if valid_files:
            st.subheader("Valid Files for Processing:")
            for idx, file in enumerate(valid_files, 1):
                col1, col2, col3 = st.columns([3, 2, 1])

                with col1:
                    # Extract and highlight the 5-digit sequence
                    base_name = os.path.splitext(file.name)[0]
                    match = re.search(r"(?<!\d)5\d{4}(?!\d)", base_name)
                    if match:
                        sequence = match.group()
                        st.write(f"**{idx}. {file.name}** (ID: {sequence})")
                    else:
                        st.write(f"**{idx}. {file.name}**")

                with col2:
                    file_size = file.size / 1024  # Convert to KB
                    if file_size > 1024:
                        file_size = file_size / 1024  # Convert to MB
                        st.write(f"Size: {file_size:.2f} MB")
                    else:
                        st.write(f"Size: {file_size:.2f} KB")

                with col3:
                    if st.button("Remove", key=f"remove_{idx}"):
                        st.warning(
                            f"Remove functionality would go here for {file.name}"
                        )

            st.markdown("---")

            # Process button - only show if there are valid files
            if st.button("Process PDFs", type="primary"):
                # Create directory if it doesn't exist
                try:
                    os.makedirs(storage_dir, exist_ok=True)

                    # Save each valid file and auto-detect publication dates
                    saved_files = []
                    overwritten_files = []
                    auto_detected_dates = []
                    with st.spinner(
                        "Saving valid PDF files and detecting publication dates..."
                    ):
                        for file in valid_files:
                            # Use original filename (will overwrite if exists)
                            file_path = os.path.join(storage_dir, file.name)

                            # Check if file already exists
                            if os.path.exists(file_path):
                                overwritten_files.append(file.name)

                            # Save the file (overwrites if exists)
                            with open(file_path, "wb") as f:
                                f.write(file.getbuffer())

                            # Auto-detect publication date from filename
                            parsed_info = parse_gg_filename(file.name)
                            if parsed_info and parsed_info.get("publish_date"):
                                # Create annotation file with auto-detected date
                                base_name = os.path.splitext(file.name)[0]
                                annotation_file_path = os.path.join(
                                    "streamlit_app_data/annotations",
                                    f"{base_name}.json",
                                )

                                # Create annotations directory if it doesn't exist
                                os.makedirs(
                                    "streamlit_app_data/annotations", exist_ok=True
                                )

                                # Only create annotation if it doesn't already exist
                                if not os.path.exists(annotation_file_path):
                                    annotations = {
                                        "publication_date": parsed_info[
                                            "publish_date"
                                        ].strftime("%Y-%m-%d"),
                                        "notice_numbers": [],
                                    }
                                    with open(annotation_file_path, "w") as f:
                                        json.dump(annotations, f, indent=2)
                                    auto_detected_dates.append(
                                        f"{file.name} → {parsed_info['publish_date'].strftime('%Y-%m-%d')}"
                                    )

                            saved_files.append(
                                {
                                    "original_name": file.name,
                                    "saved_name": file.name,
                                    "path": file_path,
                                }
                            )

                    # Store saved file info in session state
                    st.session_state["saved_pdf_info"] = saved_files

                    # Show success message
                    if overwritten_files:
                        st.success(
                            f"✅ {len(saved_files)} valid PDF file(s) saved to {storage_dir}/"
                        )
                        st.warning(
                            f"⚠️ {len(overwritten_files)} file(s) were overwritten: {', '.join(overwritten_files)}"
                        )
                    else:
                        st.success(
                            f"✅ {len(saved_files)} valid PDF file(s) saved to {storage_dir}/"
                        )

                    # Show auto-detected publication dates
                    if auto_detected_dates:
                        st.info(
                            f"📅 Auto-detected {len(auto_detected_dates)} publication date(s):"
                        )
                        for detection in auto_detected_dates:
                            st.write(f"• {detection}")

                    # Show saved files info
                    with st.expander("📁 Saved Files Details"):
                        for info in saved_files:
                            status = (
                                " (overwritten)"
                                if info["original_name"] in overwritten_files
                                else " (new)"
                            )
                            st.write(f"- **{info['original_name']}**{status}")

                    # Navigate to annotation page after a short delay
                    st.info("📄 Redirecting to annotation page...")
                    st.session_state["current_page"] = "✏️ Annotate GG PDF Files"
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Error saving files: {str(e)}")
        else:
            st.warning(
                "⚠️ No valid files to process. Please upload files with 5-digit sequences starting with 5."
            )

    else:
        # Instructions when no files are uploaded
        st.info("👆 Please upload one or more PDF files to get started.")

        with st.expander("ℹ️ Instructions"):
            st.markdown(
                """
            1. Click the **Browse files** button above
            2. Select one or more Government Gazette PDF files from your computer
            3. **Important:** Only files with 5-digit GG numbers starting with 5 are valid
               - ✅ Valid examples: `54321.pdf`, `GG_51234.pdf`, `gazette_50000.pdf`
               - ❌ Invalid examples: `12345.pdf`, `test.pdf`, `4321.pdf`
            4. Click **Process PDFs** to save valid files and proceed to annotation
            5. Annotate your GG PDFs with:
               - Publication date
               - Notice numbers (3-4 digit law amendment identifiers)

            **Supported formats:** PDF only
            **Maximum file size:** 200MB per file
            **Storage location:** streamlit_app_data/pdf_files/
            **⚠️ Note:** Uploading a file with the same name will overwrite the existing file
            """
            )


def annotate_pdf_page():
    """Page for annotating GG PDF files"""
    st.title("✏️ Annotate Government Gazette PDF Files")
    st.write("Edit publication dates and notice numbers for PDF files.")

    # Add usage instructions
    with st.expander("📋 Usage Instructions", expanded=False):
        st.markdown(
            """
        **How to edit annotations:**
        1. Enter publication dates using the date picker
        2. Enter notice numbers as space-separated 3 or 4-digit numbers (e.g., "123 4567 890")
        3. Changes are saved automatically when you move to the next field
        4. Click **Save All Changes** button to ensure all changes are persisted
        """
        )

    # Define directories
    storage_dir = "streamlit_app_data/pdf_files"
    annotations_dir = "streamlit_app_data/annotations"

    # Create annotations directory if it doesn't exist
    os.makedirs(annotations_dir, exist_ok=True)

    # Check if directory exists and has PDF files
    if not os.path.exists(storage_dir):
        st.warning("⚠️ PDF storage directory does not exist.")
        if st.button("← Go to Upload Page"):
            st.session_state["current_page"] = "📄 Upload GG PDF Files"
            st.rerun()
        return

    # Get all PDF files from directory
    pdf_files = [f for f in os.listdir(storage_dir) if f.endswith(".pdf")]

    if not pdf_files:
        st.warning("⚠️ No PDF files found in the storage directory.")
        if st.button("← Go to Upload Page"):
            st.session_state["current_page"] = "📄 Upload GG PDF Files"
            st.rerun()
        return

    st.markdown("---")
    st.subheader(f"PDF Files ({len(pdf_files)} files)")

    # Show file server info
    if FILE_SERVER_PORT:
        server_host = os.environ.get("PDF_SERVER_HOST", "localhost")
        st.info(
            f"🔗 PDF file server running on {server_host}:{FILE_SERVER_PORT} - Click any filename below to view the PDF!"
        )

    # Start the file server
    start_file_server()

    # Initialize session state for form data
    if "annotation_forms" not in st.session_state:
        st.session_state.annotation_forms = {}

    # Process each PDF file with individual form inputs
    changes_made = False
    for idx, filename in enumerate(pdf_files):
        file_path = os.path.join(storage_dir, filename)
        base_name = os.path.splitext(filename)[0]

        # Get file info
        file_size = os.path.getsize(file_path) / 1024  # KB
        if file_size > 1024:
            size_str = f"{file_size / 1024:.2f} MB"
        else:
            size_str = f"{file_size:.2f} KB"

        # Extract 5-digit ID if present
        match = re.search(r"(?<!\d)5\d{4}(?!\d)", base_name)
        gg_id = match.group() if match else "N/A"

        # Load existing annotations
        annotation_file_path = os.path.join(annotations_dir, f"{base_name}.json")
        current_publish_date = None
        current_notice_numbers = ""

        if os.path.exists(annotation_file_path):
            try:
                with open(annotation_file_path, "r") as f:
                    annotations = json.load(f)
                    if isinstance(annotations, dict):
                        if annotations.get("publication_date"):
                            try:
                                current_publish_date = pd.to_datetime(
                                    annotations["publication_date"]
                                ).date()
                            except:
                                current_publish_date = None
                        if annotations.get("notice_numbers"):
                            current_notice_numbers = " ".join(
                                str(n) for n in annotations["notice_numbers"]
                            )
            except:
                pass

        # Get PDF URL for viewing
        pdf_url = get_pdf_url(filename)

        # Create expandable section for each PDF
        with st.expander(
            f"📄 {filename} (GG ID: {gg_id}, Size: {size_str})", expanded=idx < 3
        ):
            col1, col2 = st.columns([1, 1])

            with col1:
                st.markdown(f"**[📖 View PDF]({pdf_url})**")

                # Publication date input
                new_publish_date = st.date_input(
                    "Publication Date",
                    value=current_publish_date,
                    key=f"date_{base_name}",
                    help="Select the publication date of this Government Gazette",
                )

            with col2:
                # Notice numbers input
                new_notice_numbers = st.text_input(
                    "Notice Numbers",
                    value=current_notice_numbers,
                    key=f"notices_{base_name}",
                    help="Enter space-separated 3 or 4-digit numbers (e.g., '123 4567 890')",
                    placeholder="e.g., 123 456 789",
                )

                # Auto-save when values change
                if (
                    new_publish_date != current_publish_date
                    or new_notice_numbers.strip() != current_notice_numbers.strip()
                ):
                    # Prepare annotation data
                    annotations = {"publication_date": None, "notice_numbers": []}

                    # Handle publish date
                    if new_publish_date:
                        annotations["publication_date"] = new_publish_date.strftime(
                            "%Y-%m-%d"
                        )

                    # Handle notice numbers
                    if new_notice_numbers.strip():
                        try:
                            numbers = []
                            for num_str in new_notice_numbers.strip().split():
                                num = int(num_str)
                                if 100 <= num <= 9999:  # 3 or 4 digit numbers
                                    numbers.append(num)
                                else:
                                    st.error(
                                        f"'{num_str}' is not a valid 3 or 4-digit number"
                                    )
                            annotations["notice_numbers"] = sorted(numbers)
                        except ValueError:
                            st.error(
                                "Invalid notice numbers format. Use space-separated numbers."
                            )

                    # Save annotations automatically
                    try:
                        with open(annotation_file_path, "w") as f:
                            json.dump(annotations, f, indent=2)
                        changes_made = True
                        st.success("✅ Auto-saved!", icon="💾")
                    except Exception as e:
                        st.error(f"❌ Error saving: {str(e)}")

    # Show summary of changes if any were made
    if changes_made:
        st.success("🎉 All changes have been automatically saved!")


def generate_bulletin_page():
    """Page for generating bulletin from annotated PDFs"""
    st.title("📰 Generate Government Gazette Bulletin")
    st.write("Generate formatted bulletin from your annotated PDF files.")

    # Define directories
    storage_dir = "streamlit_app_data/pdf_files"
    annotations_dir = "streamlit_app_data/annotations"

    # Check if directories exist
    if not os.path.exists(storage_dir) or not os.path.exists(annotations_dir):
        st.warning(
            "⚠️ No PDF files or annotations found. Please upload and annotate PDFs first."
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Go to Upload Page"):
                st.session_state["current_page"] = "📄 Upload GG PDF Files"
                st.rerun()
        with col2:
            if st.button("← Go to Annotation Page"):
                st.session_state["current_page"] = "✏️ Annotate GG PDF Files"
                st.rerun()
        return

    # Get annotated PDFs
    pdf_files = [f for f in os.listdir(storage_dir) if f.endswith(".pdf")]
    annotated_files = []

    for filename in pdf_files:
        base_name = os.path.splitext(filename)[0]
        annotation_file = os.path.join(annotations_dir, f"{base_name}.json")

        if os.path.exists(annotation_file):
            try:
                with open(annotation_file, "r") as f:
                    annotations = json.load(f)
                    if annotations.get("publication_date") and annotations.get(
                        "notice_numbers"
                    ):
                        annotated_files.append(
                            {
                                "filename": filename,
                                "publication_date": annotations["publication_date"],
                                "notice_numbers": annotations["notice_numbers"],
                            }
                        )
            except:
                pass

    if not annotated_files:
        st.warning(
            "⚠️ No fully annotated PDFs found. Please annotate PDFs with both publication dates and notice numbers."
        )
        if st.button("← Go to Annotation Page"):
            st.session_state["current_page"] = "✏️ Annotate GG PDF Files"
            st.rerun()
        return

    st.markdown("---")
    st.subheader(f"Ready for Bulletin Generation ({len(annotated_files)} files)")

    # Display annotated files
    for file_info in annotated_files:
        with st.expander(f"📄 {file_info['filename']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Publication Date:** {file_info['publication_date']}")
            with col2:
                notice_nums = ", ".join(map(str, file_info["notice_numbers"]))
                st.write(f"**Notice Numbers:** {notice_nums}")

    st.markdown("---")

    # Generation options
    st.subheader("📋 Generation Options")

    col1, col2 = st.columns(2)
    with col1:
        output_format = st.selectbox(
            "Output Format",
            ["Markdown", "PDF", "DOCX"],
            help="Choose the output format for the bulletin",
        )

    with col2:
        include_toc = st.checkbox(
            "Include Table of Contents",
            value=True,
            help="Add a table of contents to the bulletin",
        )

    # Generate button
    if st.button("🚀 Generate Bulletin", type="primary"):
        with st.spinner("Generating bulletin..."):
            try:
                # Create notices.csv for bb_logic
                notices_data = []
                for file_info in annotated_files:
                    pdf_path = os.path.join(storage_dir, file_info["filename"])

                    # Extract gazette number from filename (5-digit number starting with 5)
                    base_name = os.path.splitext(file_info["filename"])[0]
                    match = re.search(r"(?<!\d)5\d{4}(?!\d)", base_name)
                    gazette_num = int(match.group()) if match else None

                    if gazette_num is None:
                        st.error(
                            f"❌ Could not extract gazette number from filename: {file_info['filename']}"
                        )
                        continue

                    for notice_num in file_info["notice_numbers"]:
                        notices_data.append(
                            {"gazette_number": gazette_num, "notice_number": notice_num}
                        )

                # Check if we have valid data
                if not notices_data:
                    st.error(
                        "❌ No valid notice data found. Please ensure your PDF filenames contain 5-digit gazette numbers starting with 5."
                    )
                    return

                # Create temporary notices.csv
                temp_csv_path = "temp_notices.csv"
                df = pd.DataFrame(notices_data)
                df.to_csv(temp_csv_path, index=False)

                # Show what we're processing
                st.info(
                    f"📋 Processing {len(notices_data)} notices from {len(annotated_files)} gazette files..."
                )
                with st.expander("🔍 Debug Info - Generated CSV Data"):
                    st.dataframe(df)

                # Run bulletin generation using the core functions
                try:
                    # Change to the temp CSV file directory and run bulletin generation
                    original_cwd = os.getcwd()

                    # Create a temporary notices.csv in the current directory since that's what the function expects
                    with open("notices.csv", "w") as f:
                        df.to_csv(f, index=False)

                    # Capture stdout to get the bulletin content
                    import io
                    from contextlib import redirect_stdout

                    bulletin_buffer = io.StringIO()
                    with redirect_stdout(bulletin_buffer):
                        output_testing_bulletin(gg_dir=Path("./streamlit_app_data/pdf_files/"))

                    bulletin_content = bulletin_buffer.getvalue()

                    # Clean up temp files
                    if os.path.exists(temp_csv_path):
                        os.remove(temp_csv_path)
                    if os.path.exists("notices.csv"):
                        os.remove("notices.csv")

                    if bulletin_content:
                        st.success("✅ Bulletin generated successfully!")

                        # Display bulletin content
                        st.markdown("---")
                        st.subheader("📰 Generated Bulletin")

                        if output_format == "Markdown":
                            st.markdown(bulletin_content)

                            # Download button for markdown
                            st.download_button(
                                label="💾 Download Markdown",
                                data=bulletin_content,
                                file_name=f"bulletin_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                                mime="text/markdown",
                            )

                        else:
                            # For PDF/DOCX, convert using Pandoc
                            with st.expander("📄 Preview (Markdown)"):
                                st.markdown(bulletin_content)

                            # Convert to PDF or DOCX using Pandoc
                            try:
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                                with tempfile.NamedTemporaryFile(
                                    mode="w", suffix=".md", delete=False
                                ) as temp_md:
                                    temp_md.write(bulletin_content)
                                    temp_md_path = temp_md.name

                                if output_format == "PDF":
                                    output_file = f"bulletin_{timestamp}.pdf"
                                    # Use XeLaTeX engine for better formatting as mentioned in CLAUDE.md
                                    pandoc_cmd = [
                                        "pandoc",
                                        temp_md_path,
                                        "-o",
                                        output_file,
                                        "--pdf-engine=xelatex",
                                        "--toc" if include_toc else "--no-toc",
                                    ]
                                    mime_type = "application/pdf"

                                elif output_format == "DOCX":
                                    output_file = f"bulletin_{timestamp}.docx"
                                    pandoc_cmd = [
                                        "pandoc",
                                        temp_md_path,
                                        "-o",
                                        output_file,
                                        "--toc" if include_toc else "--no-toc",
                                    ]
                                    mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

                                # Run Pandoc conversion
                                with st.spinner(f"Converting to {output_format}..."):
                                    result = subprocess.run(
                                        pandoc_cmd,
                                        capture_output=True,
                                        text=True,
                                        timeout=60,  # 60 second timeout
                                    )

                                # Clean up temp markdown file
                                os.unlink(temp_md_path)

                                if result.returncode == 0:
                                    # Success - offer download
                                    if os.path.exists(output_file):
                                        with open(output_file, "rb") as f:
                                            file_data = f.read()

                                        st.success(
                                            f"✅ Successfully converted to {output_format}!"
                                        )

                                        # Download button for converted file
                                        st.download_button(
                                            label=f"💾 Download {output_format}",
                                            data=file_data,
                                            file_name=output_file,
                                            mime=mime_type,
                                        )

                                        # Clean up output file after download
                                        os.unlink(output_file)
                                    else:
                                        st.error(
                                            f"❌ Pandoc completed but output file {output_file} not found"
                                        )
                                else:
                                    # Pandoc failed
                                    st.error(
                                        f"❌ Pandoc conversion failed with exit code {result.returncode}"
                                    )
                                    if result.stderr:
                                        with st.expander("🔍 Pandoc Error Details"):
                                            st.code(result.stderr)

                                    # Fallback to markdown download
                                    st.warning("⚠️ Falling back to Markdown download")
                                    st.download_button(
                                        label="💾 Download Markdown (Fallback)",
                                        data=bulletin_content,
                                        file_name=f"bulletin_{timestamp}.md",
                                        mime="text/markdown",
                                    )

                            except subprocess.TimeoutExpired:
                                st.error("❌ Pandoc conversion timed out (60 seconds)")
                                # Clean up temp file
                                if "temp_md_path" in locals() and os.path.exists(
                                    temp_md_path
                                ):
                                    os.unlink(temp_md_path)

                            except FileNotFoundError:
                                st.error(
                                    "❌ Pandoc not found. Please install Pandoc to use PDF/DOCX conversion."
                                )
                                st.info(
                                    "💡 Install Pandoc: https://pandoc.org/installing.html"
                                )
                                # Fallback to markdown download
                                st.download_button(
                                    label="💾 Download Markdown (Fallback)",
                                    data=bulletin_content,
                                    file_name=f"bulletin_{timestamp}.md",
                                    mime="text/markdown",
                                )

                            except Exception as e:
                                st.error(
                                    f"❌ Unexpected error during conversion: {str(e)}"
                                )
                                # Clean up temp file if it exists
                                if "temp_md_path" in locals() and os.path.exists(
                                    temp_md_path
                                ):
                                    os.unlink(temp_md_path)
                                # Clean up output file if it exists
                                if "output_file" in locals() and os.path.exists(
                                    output_file
                                ):
                                    os.unlink(output_file)
                    else:
                        st.error("❌ Failed to generate bulletin content")

                except Exception as e:
                    st.error(f"❌ Error running bulletin generation: {str(e)}")

                    # Show more detailed error information
                    import traceback

                    with st.expander("🔍 Detailed Error Information"):
                        st.code(traceback.format_exc())

                        # Also show the CSV content for debugging
                        if os.path.exists("notices.csv"):
                            st.write("**Generated notices.csv content:**")
                            try:
                                with open("notices.csv", "r") as f:
                                    st.text(f.read())
                            except:
                                st.write("Could not read notices.csv file")

                    # Clean up temp files
                    if os.path.exists(temp_csv_path):
                        os.remove(temp_csv_path)
                    if os.path.exists("notices.csv"):
                        os.remove("notices.csv")

            except Exception as e:
                st.error(f"❌ Error preparing bulletin data: {str(e)}")


# Main app
st.set_page_config(page_title="GG Annotation System", page_icon="🏛️", layout="wide")

# Check password before showing main content
if not check_password():
    st.stop()  # Stop execution here if password is incorrect

# Initialize current page in session state
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "🏠 Home"

# Sidebar navigation
st.sidebar.title("🧭 Navigation")

# Map the current page to display labels
display_mapping = {
    "🏠 Home": "🏠 Home",
    "📄 Upload GG PDF Files": "📄 Upload GG PDFs",
    "✏️ Annotate GG PDF Files": "✏️ Annotate GG PDFs",
    "📰 Generate Bulletin": "📰 Generate Bulletin",
}

# Reverse mapping for converting display labels back to page keys
page_mapping = {
    "🏠 Home": "🏠 Home",
    "📄 Upload GG PDFs": "📄 Upload GG PDF Files",
    "✏️ Annotate GG PDFs": "✏️ Annotate GG PDF Files",
    "📰 Generate Bulletin": "📰 Generate Bulletin",
}

# Get the current display label
current_display = display_mapping.get(st.session_state["current_page"], "🏠 Home")

# Find the index for the radio button
display_options = [
    "🏠 Home",
    "📄 Upload GG PDFs",
    "✏️ Annotate GG PDFs",
    "📰 Generate Bulletin",
]
try:
    current_index = display_options.index(current_display)
except ValueError:
    current_index = 0

page = st.sidebar.radio("Go to", display_options, index=current_index)

# Update current page in session state
st.session_state["current_page"] = page_mapping.get(page, page)

# Logout button in sidebar
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Logout", use_container_width=True):
    # Clear all session state
    keys_to_remove = []
    for key in st.session_state.keys():
        if (
            key.startswith("annotations_")
            or key.startswith("gg_annotations_")
            or key
            in ["password_correct", "uploaded_pdfs", "saved_pdf_info", "current_page"]
        ):
            keys_to_remove.append(key)

    for key in keys_to_remove:
        st.session_state.pop(key, None)

    st.rerun()

# Page routing
if st.session_state["current_page"] == "🏠 Home":
    home_page()
elif st.session_state["current_page"] == "📄 Upload GG PDF Files":
    upload_pdf_page()
elif st.session_state["current_page"] == "✏️ Annotate GG PDF Files":
    annotate_pdf_page()
elif st.session_state["current_page"] == "📰 Generate Bulletin":
    generate_bulletin_page()
