# Use the official Python image from the Python Docker Hub repository as the base image
FROM python:3.14-slim

# Set the working directory to /app in the container
WORKDIR /app

FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt ./

# Install build tools, build Python packages, and clean up apt cache
RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential python3-dev && \
    useradd -m myuser && \
    pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove gcc build-essential python3-dev && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p logs qr_codes && \
    chown -R myuser:myuser /app

# Before copying the application code, create the logs and qr_codes directories
# and ensure they are owned by the non-root user

# Copy the rest of the application's source code into the container, setting ownership to 'myuser'
COPY --chown=myuser:myuser . .

# Switch to the 'myuser' user to run the application
USER myuser

# Use the Python interpreter as the entrypoint and the script as the first argument
# This allows additional command-line arguments to be passed to the script via the docker run command
ENTRYPOINT ["python", "main.py"]
# this sets a default argument, its also set in the program but this just illustrates how to use cmd and override it from the terminal
CMD ["--url","https://hub.docker.com/r/nosaomoregie/qr_codemaker"]