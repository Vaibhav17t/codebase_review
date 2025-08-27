FROM python:3.11-slim

WORKDIR /app

# Install git for repository analysis  
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install Python dependencies (now including ast-grep-cli)
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/reports /app/codebase

# Copy application
COPY code_debt_detective.py .

# Set environment
ENV PYTHONUNBUFFERED=1

# Create user
RUN useradd -m -u 1000 detective && chown -R detective:detective /app
USER detective

CMD ["python", "code_debt_detective.py"]
