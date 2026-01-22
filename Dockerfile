# Use Python 3.13 slim image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies for sentence-transformers, PDF parsing, PostgreSQL, and WeasyPrint
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpoppler-cpp-dev \
    poppler-utils \
    libpq-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    libcairo2 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the JobBERT sentence-transformers model during build
# This prevents timeout on first run and ensures model is cached
# Using TechWolf JobBERT-v3 for job-specialized semantic matching (EN, DE, ES, CN)
RUN python -c "from sentence_transformers import SentenceTransformer; print('Downloading JobBERT model...'); model = SentenceTransformer('TechWolf/JobBERT-v3'); print('JobBERT model ready!')"

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data temp_uploads data/logs

# Expose port
EXPOSE 8080

# Disable Python output buffering for immediate log visibility
ENV PYTHONUNBUFFERED=1

# Run the application with Gunicorn (production server)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "--timeout", "120", "--log-level=info", "--capture-output", "--enable-stdio-inheritance", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
