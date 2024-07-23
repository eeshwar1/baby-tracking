FROM python:3.6-slim-buster

WORKDIR /app

COPY requirements.txt ./

RUN pip install --upgrade pip 
RUN pip install -r requirements.txt

COPY . .

EXPOSE 4000

ENV PYTHONUNBUFFERED=1
ENV SQLALCHEMY_TRACK_MODIFICATIONS=False
