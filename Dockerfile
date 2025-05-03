FROM python:3.13-slim

# Set the working directory
WORKDIR /usr/local/app

# Copy the entire application code
COPY . .

USER root

RUN apt-get update && apt-get install build-essential unixodbc-dev -y

# Install dependencies
RUN pip install -r requirements.txt

# Expose the port
EXPOSE 8000

CMD ["python", "app_mssql.py"]