# Use an official Python runtime as a parent image
FROM python:3.10

# Install necessary dependencies for Chrome
RUN apt-get update && \
    apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    libglib2.0-0 \
    libx11-6 \
    libxkbcommon0 \
    libnss3 \
    libgconf-2-4 \
    libxrandr2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libpango-1.0-0 \
    libcups2 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxshmfence1 \
    libxtst6 \
    xdg-utils \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    libpci3 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create the directory for Chrome
RUN mkdir -p /opt/google/chrome

# Download and install Google Chrome version 127.0.6533.119
RUN wget https://storage.googleapis.com/chrome-for-testing-public/127.0.6533.119/linux64/chrome-linux64.zip -O chrome-linux64.zip && \
    unzip chrome-linux64.zip -d /opt/google/chrome && \
    ln -s /opt/google/chrome/chrome /usr/bin/google-chrome && \
    rm chrome-linux64.zip

# Download and install ChromeDriver version 127.0.6533.119
RUN wget https://storage.googleapis.com/chrome-for-testing-public/127.0.6533.119/linux64/chromedriver-linux64.zip -O chromedriver-linux64.zip && \
    unzip chromedriver-linux64.zip -d /usr/local/bin && \
    rm chromedriver-linux64.zip

# Set up Python environment
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all scripts and config files
COPY config.ini .
COPY main_init.py .
COPY FH_final.py .

# Run the script
CMD ["python", "FH_final.py"]
