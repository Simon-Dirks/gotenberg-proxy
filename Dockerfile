FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV FLASK_APP=app.py
ENV FLASK_DEBUG=0

CMD flask run --host=0.0.0.0 --port ${PORT:-5000}
