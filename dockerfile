# Base image: Python 3.8
FROM python:3.8-slim

# Working directory set karo
WORKDIR /app

# System dependencies install karo (ffmpeg optional hai agar video cutter chahiye)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Project files copy karo
COPY . /app

# Virtual environment banao aur activate karo
RUN python -m venv /app/shared_venv

# Virtual environment ke pip ko upgrade karo
RUN /app/shared_venv/bin/pip install --upgrade pip

# Project dependencies virtual environment mein install karo
RUN /app/shared_venv/bin/pip install --no-cache-dir -r requirements.txt

# Virtual environment ka Python default path mein add karo
ENV PATH="/app/shared_venv/bin:$PATH"

# Port expose karo
EXPOSE 8000

# Command to run the application using virtual environment ka Python
CMD ["python", "main.py"]