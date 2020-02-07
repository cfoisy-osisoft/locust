FROM python:3.7-alpine as builder

RUN apk --no-cache add g++ zeromq-dev libffi-dev 
COPY locust/ /src/locust
COPY setup.* LICENSE* MANIFEST* README* /src/
WORKDIR /src
RUN pip install --upgrade pip
RUN pip install .
# [LOADTEST]
# [LT] HackDavis library to test
## RUN pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple ocs-hackdavis==0.36.0
# [LT] Remove standard OCS python sample library installed by ocs-hackdavis, replace with locust-instrumented version
## RUN pip uninstall -y ocs-sample-library-preview

#  [LT] Locust-instrumented version of OCS Python sample library at https://github.com/osisoft/OSI-Samples-OCS
#  [LT] Source: https://github.com/osisoft-academic/OSI-Samples-OCS
RUN pip install backoff
RUN pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple ocs-sample-library-preview-hub==0.0.72rc0 
# [LT] Display installed python packages for verification
RUN pip list

FROM python:3.7-alpine

RUN apk --no-cache add zeromq wget && adduser -s /bin/false -D locust
COPY --from=builder /usr/local/lib/python3.7/site-packages /usr/local/lib/python3.7/site-packages
COPY --from=builder /usr/local/bin/locust /usr/local/bin/locust
COPY docker_start.sh docker_start.sh
RUN chmod +x docker_start.sh

EXPOSE 8089 5557 5558

USER locust
CMD ["./docker_start.sh"]
