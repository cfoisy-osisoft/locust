from locust import HttpLocust, TaskSet, between
import datetime
import socket
from ocs_sample_library_preview import OCSClient, SdsError
import random
import os
import backoff
from random import randrange
import math

# ---------------------------------------------------------------------------------
# Overview
#
# This Locust script does the following:
#
# 1- builds a list of all the streams in the namespace to test
# 2- simulates as many independent OCS clients as specified in the Locust GUI
# 3- for each simulated client:
#      a) perform login by creating a new OCSClient object (do this once)
#      b) pick a stream at random
#      c) make a request for interpolated data:
#            i)  DV_SPAN_MONTH: number of month for request period
#            ii) DV_INTERVAL: interpolation interval in minute
#      d) wait between LOCUST_MIN_WAIT and LOCUST_MAX_WAIT seconds before repeating
#          steps b, c, and d.
# ---------------------------------------------------------------------------------


def client_id():
    my_ip = socket.gethostbyname(socket.gethostname())
    return int(my_ip.split(".")[2])


slave_id = client_id()
print(f"@@@@@@@@@@@@@@@@@ slave id: {slave_id} @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")


month_offset = {}
month_span = {}
bad = {}
all_streams = []
namespace_id = os.environ.get("NAMESPACE_ID", "---not-set---")

temp_ocs_client = OCSClient(
    os.environ.get("API_VERSION", "v1-preview"),
    os.environ["TENANT_ID"],
    os.environ.get("OCS_ENDPOINT", "https://dat-b.osisoft.com"),
    os.environ["CLIENT_ID"],
    os.environ["CLIENT_SECRET"],
)

ocs_streams = temp_ocs_client.Streams.getStreams(namespace_id, count=5000)

for stream in ocs_streams:
    stream_id = stream.Id
    stream_name = stream.Name
    all_streams.append((stream_id, stream_name))
    bad[stream_id] = False
    month_offset[stream_id] = 0

print(
    f"@@@@@ Slave id: {slave_id} \n\n ## of streams = {len(all_streams)}\n\n > all_streams={all_streams}\n\n"
)

# "65292b6c-ec16-414a-b583-ce7ae04046d4",


def login(self):
    self.ocs_client = OCSClient(
        os.environ.get("API_VERSION", "v1-preview"),
        os.environ["TENANT_ID"],
        "https://dat-b.osisoft.com",
        os.environ["CLIENT_ID"],
        os.environ["CLIENT_SECRET"],
        webclient=self.client,
    )
    self.dv_month_span = int(
        os.environ.get("DV_SPAN_MONTH", "4")
    )  # how many month to request
    self.dv_min_interval = int(
        os.environ.get("DV_INTERVAL", "2")
    )  # interpolation interval in minutes
    self.data_total_month = int(
        os.environ.get("DATA_TOTAL_MONTH", "36")
    )  # how many of data in total
    self.data_start_year = int(
        os.environ.get("DATA_START_YEAR", "2017")
    )  # starting year for data
    self.event_count = (
        int(self.dv_month_span * 30 * 24 * 60 / self.dv_min_interval) + 1
    )  # how many events
    print(
        f"@@@ Parameters: month_span= {self.dv_month_span}, interval= {self.dv_min_interval}, count= {self.event_count}"
    )


# NOTE: instead of calling SDS getRangeValuesInterpolated directly, the decorated (with @backeoff)
#       function below implements exponential backoff with random jitter, with 4 retries before
#       bailing out and returning the last exception
#
@backoff.on_exception(backoff.expo, SdsError, max_tries=4, jitter=backoff.full_jitter)
def get_interpolated_data(
    ocs_client, namespace_id, stream_id, start, end, count, **kwargs,
):
    result = ocs_client.Streams.getRangeValuesInterpolated(
        namespace_id,
        stream_id,
        value_class=None,
        start=start.isoformat(),
        end=end.isoformat(),
        count=count,
        **kwargs,
    )
    return result


def logout(self):
    pass


def get_data(self):
    while True:
        stream_id, stream_name = random.choice(all_streams)
        if not bad[stream_id]:
            break

    offset = month_offset[stream_id]
    span = self.dv_month_span  # month_span[stream_id]
    print(
        f"@@@@@@@@@ testing stream {stream_id}|{stream_name}, off={offset}, span={span}"
    )
    # month_offset[stream_id] = (month_offset[stream_id] + span) % 36
    start = datetime.datetime(
        self.data_start_year + int(offset / 12), 1 + (offset % 12), 1, 0, 0
    )
    span_days = datetime.timedelta(days=span * 30)
    end = start + span_days
    try:
        result = get_interpolated_data(
            self.ocs_client,
            namespace_id,
            stream_id,
            start,
            end,
            self.event_count,
            name=f"{stream_name}|{stream_id}:{self.dv_month_span}",
        )
        print(
            f"@@@@@@@@@ result stream {stream_id}|{stream_name}:{self.dv_month_span} len={len(result)}"
        )
    except SdsError as e:
        # Most of the time 408s, but may be 503
        #
        # Uncomment code below to mute (possibly) bad streams after error
        # bad[stream_id] = True

        print(f"###################### SdsError for {stream_id}|{stream_name}: {e}")
        raise e
    except Exception as e:
        print(f"###################### Exception for {stream_id}|{stream_name}: {e}")
        raise e

    # compute next offset
    month_offset[stream_id] = (month_offset[stream_id] + span) % self.data_total_month


class UserBehavior(TaskSet):
    tasks = {get_data: 1}

    def on_start(self):
        login(self)

    def on_stop(self):
        logout(self)


class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    min_wait_time = float(os.environ.get("LOCUST_MIN_WAIT", "3.0"))
    max_wait_time = float(os.environ.get("LOCUST_MAX_WAIT", "5.0"))

    wait_time = between(min_wait_time, max_wait_time)
