# Use an official Python runtime as the base image
FROM python:3.10-slim-buster

# Set the working directory inside the container
WORKDIR /app

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
# dumb-init handles signals correctly, ensuring graceful shutdowns.
# gunicorn runs the Flask health check server on port 8000.
# The '&' runs it in the background.
# python3 main.py then runs your Pyrogram bot.
# Both run concurrently within the same container.
CMD ["/usr/bin/dumb-init", "--", "gunicorn", "--bind", "0.0.0.0:8000", "health_check_server:app", "&", "python3", "main.py"]
