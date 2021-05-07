FROM python:3.9-slim

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/

RUN apt-get clean \
  && apt -y update \
  && pip install --upgrade pip  \
  && apt -y install python3-dev \
     build-essential \
  && pip3 install --no-cache-dir -r requirements.txt

COPY . /usr/src/app

CMD ["uwsgi", "--ini", "uwsgi.ini"]