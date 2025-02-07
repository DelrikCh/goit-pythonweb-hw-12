# Use the official Python image as the base image
FROM python:3.13.1

# Set the working directory in the container
WORKDIR /app

RUN apt-get update && apt-get install -y postgresql-client

# Copy the requirements file into the container
COPY app/requirements.txt .

# Install dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the app code into the container
COPY . .

# Expose port 8000 for the FastAPI application
EXPOSE 8000

COPY ./docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

# Start the FastAPI app with Uvicorn (this runs the app)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
