#!/usr/bin/env sh

# if [ -z "${TARGET_URL}" ]; then
#  echo "ERROR: TARGET_URL not configured" >&2
#  exit 1
# fi

LOCUST_MODE="${LOCUST_MODE:=standalone}"
_LOCUST_OPTS="-f ${LOCUST_SCRIPTS:-/locust-tasks/tasks.py} -H ${TARGET_HOST}"

if [ "${LOCUST_MODE}" = "master" ]; then
    _LOCUST_OPTS="${_LOCUST_OPTS} --master"
elif [ "${LOCUST_MODE}" = "worker" ]; then
    if [ -z "${LOCUST_MASTER}" ]; then
        echo "ERROR: LOCUST_MASTER is empty. Slave mode requires a master" >&2
        exit 1
    fi
    LOCUST_MASTER_HOST=${LOCUST_MASTER}
    LOCUST_MASTER=no
    while ! wget --spider -qT5 ${LOCUST_MASTER_HOST}:8089 >/dev/null 2>&1; do
        echo "Waiting for master"
	sleep 5
    done

    _LOCUST_OPTS="${_LOCUST_OPTS} --slave --master-host=${LOCUST_MASTER_HOST} --master-port=${LOCUST_MASTER_PORT:-5557}"
fi

echo "Starting Locust in ${LOCUST_MODE} mode..."
echo "$ locust ${LOCUST_OPTS} ${_LOCUST_OPTS}"

exec locust ${LOCUST_OPTS} ${_LOCUST_OPTS}
