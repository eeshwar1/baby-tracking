FROM python:3.9.12-alpine

WORKDIR /app

COPY requirements.txt ./

RUN pip install --upgrade pip 
RUN \
 apk add --no-cache postgresql-libs && \
 apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev
RUN pip install -r requirements.txt

COPY . .

EXPOSE 4000

ENV SQLALCHEMY_TRACK_MODIFICATIONS=False
