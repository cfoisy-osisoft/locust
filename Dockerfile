FROM python:3.6-alpine as builder

RUN apk --no-cache add g++ zeromq-dev libffi-dev 
COPY . /src
WORKDIR /src
RUN pip install .
RUN pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple ocs-hackdavis==0.10.0
RUN pip uninstall -y ocs-sample-library-preview
RUN pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple ocs-sample-library-preview-hub==0.0.36rc0 
RUN pip install pyyaml
RUN pip list

FROM python:3.6-alpine

RUN apk --no-cache add zeromq wget && adduser -s /bin/false -D locust
COPY --from=builder /usr/local/lib/python3.6/site-packages /usr/local/lib/python3.6/site-packages
COPY --from=builder /usr/local/bin/locust /usr/local/bin/locust
COPY docker_start.sh docker_start.sh
COPY locustfile.py locustfile.py
RUN chmod +x docker_start.sh

EXPOSE 8089 5557 5558

USER locust
CMD ["./docker_start.sh"]
