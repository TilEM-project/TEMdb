FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY . /app

CMD ["uvicorn", "run:app", "--host", "0.0.0.0", "--port", "80"]