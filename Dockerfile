# Stick to a stable Debian base to avoid moving targets
FROM python:3.10-bookworm

# System deps for headless Chrome (minimal, no deprecated packages)
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    unzip \
    wget \
    xdg-utils \
    fonts-liberation \
    # chrome runtime libs
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0 \
    libnspr4 \
    libnss3 \
    libx11-6 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxkbcommon0 \
    libxrandr2 \
    libxshmfence1 \
    libxtst6 \
    libxss1 \
    libayatana-appindicator3-1 \
 && rm -rf /var/lib/apt/lists/*

# Install Chrome (chrome-for-testing layout)
ENV CHROME_VERSION=127.0.6533.119
RUN mkdir -p /opt/google/chrome \
 && wget -O /tmp/chrome.zip \
      https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chrome-linux64.zip \
 && unzip /tmp/chrome.zip -d /opt/google/chrome \
 && ln -sf /opt/google/chrome/chrome-linux64/chrome /usr/bin/google-chrome \
 && rm /tmp/chrome.zip

# Install matching ChromeDriver
RUN wget -O /tmp/chromedriver.zip \
      https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip \
 && unzip /tmp/chromedriver.zip -d /tmp \
 && mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
 && chmod +x /usr/local/bin/chromedriver \
 && rm -rf /tmp/chromedriver.zip /tmp/chromedriver-linux64

# Optional: make life easier for Selenium/Playwright
ENV CHROME_BIN=/usr/bin/google-chrome
ENV PATH="/opt/google/chrome/chrome-linux64:${PATH}"

# Python deps
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY config.ini .
COPY main_init.py .
COPY FH_final.py .

# If you use Selenium in CI, consider adding these flags in your code:
# options.add_argument("--no-sandbox")
# options.add_argument("--disable-dev-shm-usage")

CMD ["python", "FH_final.py"]
