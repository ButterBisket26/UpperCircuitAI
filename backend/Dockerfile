# Use slim python runtime
FROM python:3.10-slim

# Prevent python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1
# Prevent writing compiled .pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies list
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code files
COPY . .

# Expose Hugging Face Spaces default port
EXPOSE 7860

# Execute server command on port 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
