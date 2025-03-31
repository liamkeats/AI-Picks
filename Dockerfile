FROM python:3.12-slim

# 🧰 Install necessary system dependencies for MongoDB SSL
RUN apt-get update && apt-get install -y \
    gcc \
    libssl-dev \
    ca-certificates \
    curl \
 && update-ca-certificates \
 && apt-get clean

# 📁 Set working directory
WORKDIR /app

# 📦 Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 🗃 Copy bot files
COPY . .

# 🚀 Run bot
CMD ["python", "bot.py"]
