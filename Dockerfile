FROM ubuntu:18.04
ENTRYPOINT []
RUN apt-get update && apt-get install -y python3 python3-pip && python3 -m pip install --no-cache --upgrade pip && pip3 install --no-cache tgtg && pip3 install --no-cache schedule && pip3 install --no-cache requests && pip3 install --no-cache flask
ADD . /app/

RUN chmod +x /app/start_services.sh
CMD /app/start_services.sh
