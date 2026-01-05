FROM python:3.10.8-slim-bullseye

RUN apt update && apt upgrade -y
RUN apt install git -y curl

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

COPY . /app
WORKDIR /app

CMD ["python", "bot.py"]
