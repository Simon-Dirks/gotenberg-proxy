# Gotenberg PDF Proxy

A Python proxy service that converts documents to PDF using Gotenberg. Provide a URL to a document, and get back a PDF. See [Gotenberg documentation](https://gotenberg.dev/docs/routes#office-documents-into-pdfs-route) for supported file types.

## Features

- Converts documents to PDF using Gotenberg's LibreOffice conversion
- Caches PDFs to avoid redundant conversions
- Simple REST API

## Installation

Start the services using Docker Compose:

```bash
docker compose up -d --build
```

## Configuration

Configuration is done through environment variables. Create a `.env` file or set them directly.

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

The cache is stored in a Docker volume named `pdf_cache` for persistence between container restarts.
