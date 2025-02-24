# Gotenberg PDF Proxy

A Python proxy service that converts documents to PDF using Gotenberg. Provide a URL to a document, and get back a PDF. See [Gotenberg documentation](https://gotenberg.dev/docs/routes#office-documents-into-pdfs-route) for supported file types.

## Features

- Converts documents to PDF using Gotenberg's LibreOffice conversion
- Caches PDFs to avoid redundant conversions
- Simple REST API

## Prerequisites

- Python 3.8+
- Gotenberg running on localhost:3000

## Installation

1. Install Python dependencies:

```bash
pip install -r requirements.txt
```

2. Make sure Gotenberg is running:

```bash
docker run --rm -p 3000:3000 gotenberg/gotenberg:8
```

3. Start the proxy server:

```bash
flask run --debug
```

## Usage

### API

`POST /convert`

Request body:

```json
{
  "url": "https://example.com/document.docx"
}
```

Response: PDF file or error message

### Example

```bash
curl -X POST http://localhost:5000/convert \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com/document.docx"}' \
     -o document.pdf
```

## Caching

Converted PDFs are cached using the source URL as a key. Cached files:
- Are only accessible through the `/convert` endpoint
- Expire after a configurable time period (default: 60 minutes)
- Are automatically regenerated when expired

Configure cache expiry using the `CACHE_MAX_AGE_MINUTES` environment variable:
```bash
CACHE_MAX_AGE_MINUTES=120 flask run  # Set cache expiry to 2 hours
```
Converted PDFs are cached in the `pdf_cache` directory to improve performance for repeated requests.
