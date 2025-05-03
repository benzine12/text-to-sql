FROM python:3.13-alpine

# Set the working directory
WORKDIR /usr/local/app

# Copy the entire application code
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port
EXPOSE 8000

CMD ["python", "app.py"]