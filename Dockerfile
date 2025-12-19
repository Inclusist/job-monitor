# Use Python 3.13 slim image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies for sentence-transformers, PDF parsing, and PostgreSQL
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpoppler-cpp-dev \
    poppler-utils \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the sentence-transformers model during build
# This prevents timeout on first run and ensures model is cached
RUN python -c "from sentence_transformers import SentenceTransformer; print('Downloading model...'); model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); print('Model ready!')"

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data temp_uploads data/logs

# Expose port
EXPOSE 8080

# Run the application with Gunicorn (production server)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
