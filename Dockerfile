FROM alpine:latest

RUN apk add --no-cache python3 && \
  python3 -m ensurepip && \
  rm -r /usr/lib/python*/ensurepip && \
  pip3 install --upgrade pip setuptools && \
  rm -r /root/.cache

RUN mkdir -p /opt
ADD requirements.txt /opt/.
RUN pip3 install -r /opt/requirements.txt
RUN rm /opt/requirements.txt
ADD . /opt/
CMD ["python3", "-u", "/opt/src/server.py"]
