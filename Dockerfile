FROM python:3.9-slim

WORKDIR /app

COPY onsite/requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire FastAPI app directory (onsite) into the container
COPY onsite/ /app

# Expose the port that FastAPI will run on
EXPOSE 80

# Command to run the FastAPI app using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]