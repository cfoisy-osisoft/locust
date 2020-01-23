FROM python:3.7-alpine as builder

RUN apk --no-cache add g++ zeromq-dev libffi-dev 
COPY locust/ /src/locust
COPY setup.* LICENSE* MANIFEST* README* /src/
WORKDIR /src
RUN pip install .
RUN pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple ocs-hackdavis==0.34.0
RUN pip uninstall -y ocs-sample-library-preview
RUN pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple ocs-sample-library-preview-hub==0.0.56rc0 
# RUN pip install pyyaml backoff
RUN pip list

FROM python:3.7-alpine

RUN apk --no-cache add zeromq wget && adduser -s /bin/false -D locust
COPY --from=builder /usr/local/lib/python3.7/site-packages /usr/local/lib/python3.7/site-packages
COPY --from=builder /usr/local/bin/locust /usr/local/bin/locust
COPY docker_start.sh docker_start.sh
# COPY locustfile.py locustfile.py
RUN chmod +x docker_start.sh

EXPOSE 8089 5557 5558

USER locust
CMD ["./docker_start.sh"]
