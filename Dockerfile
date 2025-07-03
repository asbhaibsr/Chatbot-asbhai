# Use an official Python runtime as the base image
FROM python:3.10-slim-buster # python:latest ki jagah specific version use karo, jyada stable

# Set the working directory inside the container
WORKDIR /app

# Install dumb-init (recommended for proper signal handling)
# Debian-based images par apt se install karna sahi hai
RUN apt-get update && apt-get install -y dumb-init && rm -rf /var/lib/apt/lists/*

# Copy your requirements.txt first to leverage Docker's layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all your application code into the container
# Ab main.py ko bot.py rename kiya hai, to directly copy kar sakte hain
COPY . /app

# No EXPOSE needed as Procfile defines which process handles the exposed port.
# No CMD or ENTRYPOINT here. Procfile will define the commands for 'web' and 'bot' processes.
