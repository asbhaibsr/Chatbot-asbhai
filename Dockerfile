# Use an official Python runtime as the base image
# python:latest ki jagah specific version use karo, jyada stable
FROM python:3.10-slim-buster

# Set the working directory inside the container
WORKDIR /app

# Install build-essential package (for compilers like gcc) and dumb-init
# build-essential mein gcc, g++ aur make jaise tools hote hain jo C extensions compile karne ke liye zaroori hain
RUN apt-get update && apt-get install -y build-essential dumb-init && rm -rf /var/lib/apt/lists/*

# Copy your requirements.txt first to leverage Docker's layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all your application code into the container
COPY . /app
