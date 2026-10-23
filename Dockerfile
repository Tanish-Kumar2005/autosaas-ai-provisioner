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

# /app is created inside the container automatically
WORKDIR /app

# Copy your local auto-saas-provisioner folder into the container's /app
COPY auto-saas-provisioner/ /app/

# Install python dependencies from backend folder
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
RUN playwright install chromium

# Move into backend directory where main.py is located
WORKDIR /app/backend

EXPOSE 8000

# Run FastAPI via Uvicorn
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]