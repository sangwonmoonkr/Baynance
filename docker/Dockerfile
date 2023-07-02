# Use the Python 3.11 image as the base.
FROM python:3.11

# Set the working directory.
WORKDIR /app

# Install the necessary packages using requirements.txt.
COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source code.
COPY ../src ./

# Run the Python script.
CMD [ "python", "./main.py" ]
