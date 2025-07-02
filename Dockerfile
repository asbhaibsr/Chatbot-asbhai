# Use an official Python runtime as the base image
FROM python:3.10-slim-buster

# Set the working directory inside the container
WORKDIR /app

# Install dumb-init first
# dumb-init is useful for proper signal handling in containers
RUN apt-get update && apt-get install -y dumb-init && rm -rf /var/lib/apt/lists/*

# Copy your requirements.txt first to leverage Docker's layer caching
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir: Don't store cache locally, saves space
# -r requirements.txt: Install packages from the requirements file
RUN pip install --no-cache-dir -r requirements.txt

# Copy all your application code into the container
COPY . /app

# Expose the port that the health check server will listen on
# Koyeb will use its own PORT environment variable, but this is good practice
EXPOSE 8000

# Set the entrypoint for the container.
# dumb-init is used as the primary process.
# gunicorn runs the Flask health check server on port 8000 in the background.
# python main.py then runs your Pyrogram bot.
# Both run concurrently within the same container.
CMD ["dumb-init", "--", "gunicorn", "--bind", "0.0.0.0:8000", "health_check_server:app", "&", "python", "main.py"]
