FROM python:3.10-slim

# Install system dependencies required by Playwright/Chromium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libpango-1.0-0 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libnss3-dev \
    libxshmfence-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend files from the nested folder structure
COPY auto-saas-provisioner/backend/ /app/

# Install Python packages and Playwright browsers
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

EXPOSE 8000

# Run FastAPI via Uvicorn using the dynamic port assigned by the cloud host
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]