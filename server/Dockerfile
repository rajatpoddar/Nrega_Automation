# Use an official lightweight Python image as a parent image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application files into the container
COPY license_server.py .
COPY templates ./templates

# Updated: Make port 8000 available inside the container
EXPOSE 8000

# Updated: Bind Gunicorn to port 8000
CMD ["gunicorn", "--workers", "1", "--bind", "0.0.0.0:8000", "license_server:app"]