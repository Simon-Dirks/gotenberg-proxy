import os
import hashlib
from flask import Flask, request, send_file
from gotenberg_client import GotenbergClient
import requests
import tempfile
import magic
import logging
from pathlib import Path

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Gotenberg client
gotenberg = GotenbergClient('http://localhost:3000')

# Create cache directory
CACHE_DIR = Path('pdf_cache')
CACHE_DIR.mkdir(exist_ok=True)

def get_cache_path(url):
    """Generate a unique cache path for a given URL."""
    url_hash = hashlib.sha256(url.encode()).hexdigest()
    return CACHE_DIR / f"{url_hash}.pdf"

def clean_filename(url_path: str, max_length: int = 50) -> str:
    """Clean filename from URL path by removing query parameters and limiting length."""
    # Remove query parameters
    filename = url_path.split('?')[0]
    # Get basename in case of path
    filename = os.path.basename(filename)
    # Remove special characters except for extension
    name, ext = os.path.splitext(filename)
    name = ''.join(c for c in name if c.isalnum() or c in '._-')
    # Limit length
    if len(name) > max_length:
        name = name[:max_length]
    return name + ext

def download_file(url):
    """Download a file from URL and return its path."""
    response = requests.get(url)
    response.raise_for_status()
    
    # Get filename from URL and clean it
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    filename = clean_filename(parsed_url.path)
    logger.debug(f"Using filename: {filename} from URL: {url}")
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(delete=False, prefix=filename) as temp_file:
        temp_file.write(response.content)
        return temp_file.name

@app.route('/convert', methods=['POST'])
def convert_to_pdf():
    url = request.json.get('url')
    logger.debug(f"Received conversion request for URL: {url}")
    
    if not url:
        logger.warning("No URL provided in request")
        return {'error': 'URL is required'}, 400

    try:
        cache_path = get_cache_path(url)
        logger.debug(f"Cache path for URL: {cache_path}")
        
        # Check if PDF is already cached
        if cache_path.exists():
            logger.info(f"Serving cached PDF for URL: {url}")
            return send_file(cache_path, mimetype='application/pdf')

        # Download and convert the file
        logger.debug(f"Downloading file from URL: {url}")
        input_file_path = download_file(url)
        logger.info(f"Downloaded file to {input_file_path}")

        try:
            # Use LibreOffice conversion route
            logger.debug("Initializing Gotenberg LibreOffice conversion")
            route = gotenberg.libre_office.to_pdf()
            logger.debug(f"Converting file with Gotenberg, input path: {input_file_path}")
            
            # Convert file
            response = route.convert(Path(input_file_path)).run()
            
            # Save the converted PDF
            response.to_file(cache_path)
            logger.info(f"Saved converted PDF to {cache_path}")
            return send_file(cache_path, mimetype='application/pdf')

        finally:
            # Clean up temporary file
            os.unlink(input_file_path)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading file: {str(e)}", exc_info=True)
        return {'error': f'Failed to download file: {str(e)}'}, 400
    except Exception as e:
        logger.error(f"Conversion error: {str(e)}", exc_info=True)
        logger.debug(f"Error type: {type(e)}")
        logger.debug(f"Error args: {e.args}")
        return {'error': f'PDF conversion failed: {str(e)}'}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
