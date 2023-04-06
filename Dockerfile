from python:2

WORKDIR /code
COPY ./requirements.txt /code

RUN pip2 install -r requirements.txt  --no-cache-dir
