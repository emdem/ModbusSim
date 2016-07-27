FROM hypriot/rpi-alpine-scratch:latest
RUN apk update && apk upgrade

RUN apk add python3 && \
  python3 -m ensurepip && \
  pip3 install --upgrade pip setuptools

RUN mkdir -p /opt
ADD requirements.txt /opt/.
RUN pip3 install -r /opt/requirements.txt
RUN rm /opt/requirements.txt
ADD . /opt/
CMD ["python3", "-u", "/opt/src/server.py"]
