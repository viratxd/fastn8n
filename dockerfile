FROM python:3.10

# Install git and ffmpeg as root
RUN apt-get update && apt-get install -y git ffmpeg

# Create a non-root user
RUN useradd -m -u 1000 user
ENV HOME=/home/user
USER user
WORKDIR /app

# Receive Git URL from build argument
ARG GIT_REP
RUN echo "Cloning repository: ${GIT_REP}" && \
    git clone https://github.com/viratxd/fastn8n.git /app/fastn8n

WORKDIR /app/fastn8n

# Set up virtual environment and dependencies
RUN python -m venv shared_venv && \
    shared_venv/bin/pip install --upgrade pip && \
    shared_venv/bin/pip install --no-cache-dir -r requirements.txt && \
    shared_venv/bin/pip install --no-cache-dir numpy opencv-python-headless  && \
    shared_venv/bin/python -m pip list > /app/pip_list.txt

# Ensure permissions
RUN chown -R user:user /app

EXPOSE 7860
CMD ["shared_venv/bin/python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
