# Use an official Python runtime as the base image
# python:latest ki jagah specific version use karo, jyada stable
FROM python:3.10-slim-buster

# Set the working directory inside the container
WORKDIR /app

# Install dumb-init (recommended for proper signal handling)
RUN apt-get update && apt-get install -y dumb-init && rm -rf /var/lib/apt/lists/*

# Copy your requirements.txt first to leverage Docker's layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all your application code into the container
COPY . /app
