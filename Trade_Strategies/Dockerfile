FROM python:3.11-slim

WORKDIR /app

# Ensure Flask and Flask-CORS are installed since it might not be in requirements
RUN pip install --no-cache-dir flask flask-cors pandas numpy requests

COPY . .

CMD ["python", "strategies_app.py"]
