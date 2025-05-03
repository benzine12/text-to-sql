FROM python:3.13-slim

# Set the working directory
WORKDIR /usr/local/app

# Copy the entire application code
COPY . .

USER root

RUN apt-get update && apt-get install -y curl gnupg2 unixodbc unixodbc-dev
RUN mkdir -p /etc/apt/keyrings \
    && curl -sSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /etc/apt/keyrings/microsoft.gpg \
    && echo "deb [arch=amd64,arm64 signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list
    RUN apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18

# Install dependencies
RUN pip install -r requirements.txt

# Expose the port
EXPOSE 8000

CMD ["python", "app_mssql.py"]