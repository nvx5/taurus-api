FROM python:3.10-slim

WORKDIR /app

# Install Chrome and other dependencies for Selenium - be more thorough
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    xvfb \
    chromium \
    chromium-driver \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    git \
    build-essential \
    curl \
    procps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for Chrome with fixed paths
ENV DISPLAY=:99
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMIUM_PATH=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV SELENIUM_HEADLESS=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Create Xvfb startup script
RUN echo '#!/bin/bash\nXvfb :99 -screen 0 1280x1024x24 -ac &\necho "Starting Xvfb..."\nsleep 2\necho "Starting Gunicorn..."\nexec "$@"' > /entrypoint.sh \
    && chmod +x /entrypoint.sh

# Test Chrome can start in the container
RUN echo "Testing Chrome installation..." && \
    $CHROME_BIN --version && \
    echo "Chrome installation verified!"

# Copy requirements first
COPY requirements.txt .

# Install packages except swisseph
RUN grep -v "swisseph" requirements.txt > requirements_without_swisseph.txt && \
    pip install --no-cache-dir -r requirements_without_swisseph.txt

# Install swisseph directly from source
RUN pip install swisseph==0.8.0

# Copy application files
COPY . .

# Create a healthcheck file for faster startup probes
RUN echo '#!/bin/bash\ncurl -f http://localhost:8000/health || exit 1' > /healthcheck.sh && \
    chmod +x /healthcheck.sh

# Create a simple readiness script
RUN echo "print('Ready!')" > /app/ready.py

# Expose port - use 8000 as Azure Container Apps prefers it
EXPOSE 8000

# Use the entrypoint script
ENTRYPOINT ["/entrypoint.sh"]

# Start Gunicorn server with higher timeout and workers
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "600", "--workers", "2", "--threads", "4", "app:app"] 