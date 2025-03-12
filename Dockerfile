# Use Python 3.10 slim image for minimal footprint
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for numpy and scipy
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only necessary files
COPY requirements.txt .
COPY app.py .
COPY point3d.py .
COPY terrain_storage.py .
COPY terrain_analysis.py .
COPY dxf_importer.py .
COPY terrain_interpolation.py .
COPY templates/ templates/
COPY static/ static/

# Create data directory
RUN mkdir -p data

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5000

# Use gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]
