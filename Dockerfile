FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY . /app

WORKDIR /app
RUN pip install .


EXPOSE 8000

# Command to run the FastAPI application
CMD ["uvicorn", "run:app",  "--host", "0.0.0.0", "--port", "80", "--lifespan", "on"]
