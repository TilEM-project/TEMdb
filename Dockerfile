# Use the official Python image
FROM python:3.11

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Copy the rest of the application code to the working directory
COPY . .

EXPOSE 8000

# Command to run the FastAPI application
CMD ["uvicorn", "run:app",  "--host", "0.0.0.0", "--port", "80", "--lifespan", "on"]
