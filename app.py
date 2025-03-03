import os
import hashlib
import time
from flask import Flask, request, send_file
from flask_cors import CORS
from gotenberg_client import GotenbergClient
import requests
import tempfile
import logging
from pathlib import Path

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Gotenberg client
GOTENBERG_HOST = os.getenv('GOTENBERG_HOST', 'http://localhost:3000')
gotenberg = GotenbergClient(GOTENBERG_HOST)
logger.info(f"Connecting to Gotenberg at: {GOTENBERG_HOST}")

# Cache configuration
ENABLE_CACHE = bool(int(os.getenv('ENABLE_CACHE', '0')))
CACHE_DIR = Path('pdf_cache')
if ENABLE_CACHE:
    CACHE_DIR.mkdir(exist_ok=True)
CACHE_MAX_AGE_MINUTES = int(os.getenv('CACHE_MAX_AGE_MINUTES', '60'))
CACHE_MAX_AGE = CACHE_MAX_AGE_MINUTES * 60  # Convert to seconds

logger.info(f"Cache enabled: {ENABLE_CACHE}")
if ENABLE_CACHE:
    logger.info(f"Cache directory: {CACHE_DIR.absolute()}")
    logger.info(f"Cache expiry: {CACHE_MAX_AGE_MINUTES} minutes")

def is_cache_valid(cache_path: Path) -> bool:
    """Check if cached file is still valid based on its age."""
    if not ENABLE_CACHE or not cache_path.exists():
        return False
    file_age = time.time() - cache_path.stat().st_mtime
    return file_age < CACHE_MAX_AGE

def clean_url(url: str) -> str:
    """Remove query parameters from URL."""
    return url.split('?')[0]

def get_cache_path(url):
    """Generate a unique cache path for a given URL."""
    url_hash = hashlib.sha256(url.encode()).hexdigest()
    return CACHE_DIR / f"{url_hash}.pdf"

def clean_filename(url_path: str, max_length: int = 50) -> str:
    """Clean filename from URL path by removing query parameters and limiting length."""
    # Remove query parameters
    filename = clean_url(url_path)
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
    
    # Create a temporary file with the correct name
    temp_dir = Path(tempfile.gettempdir())
    temp_path = temp_dir / filename
    
    with open(temp_path, 'wb') as f:
        f.write(response.content)
    return str(temp_path)

@app.route('/convert', methods=['GET'])
def convert_to_pdf():
    url = request.args.get('url')
    logger.debug(f"Received conversion request for URL: {url}")
    
    if not url:
        logger.warning("No URL provided in request")
        return {'error': 'URL is required'}, 400

    try:
        # Handle caching if enabled
        if ENABLE_CACHE:
            cache_path = get_cache_path(url)
            logger.debug(f"Cache path for URL: {cache_path}")
            
            # Check if PDF is cached and still valid
            if is_cache_valid(cache_path):
                logger.info(f"Serving cached PDF for URL: {url}")
                return send_file(cache_path, mimetype='application/pdf')
            elif cache_path.exists():
                logger.info(f"Cache expired for URL: {url}, reconverting")
                cache_path.unlink()

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
            output_path = cache_path if ENABLE_CACHE else Path(tempfile.gettempdir()) / f"converted_{int(time.time())}.pdf"
            response.to_file(output_path)
            logger.info(f"Saved {'cached' if ENABLE_CACHE else 'temporary'} PDF to {output_path}")

            return send_file(output_path, mimetype='application/pdf')
        finally:
            # Clean up temporary file
            try:
                Path(input_file_path).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {input_file_path}: {e}")

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
