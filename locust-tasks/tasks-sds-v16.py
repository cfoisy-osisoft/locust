from locust import HttpLocust, TaskSet, between
import datetime
import socket
from ocs_hackdavis import (
    ucdavis_buildings,  # list of campus buildings
    ucdavis_ceeds_of,  # list of CEED element of a building (Electricity, Steam, Chilled Water, etc)
    ucdavis_streams_of,  # The list of all OCS data streams for a building and CEED pair
    ucdavis_building_metadata,  # Metadata for a building: building code, lat/long, usage, etc.
    ocs_stream_interpolated_data,  # Interpolated data from a stream given a time range + interpolation interval
    ucdavis_outside_temperature,  # Outside temperature at UC Davis for a given a time range + interpolation interval
)
from ocs_sample_library_preview import OCSClient, Sds503, SdsError
import random
import os
from gevent.lock import BoundedSemaphore
import backoff
import logging
from random import randrange
import math

logging.getLogger("backoff").addHandler(logging.StreamHandler())


def client_id():
    my_ip = socket.gethostbyname(socket.gethostname())
    return int(my_ip.split(".")[2])


slave_id = client_id()
print(f"@@@@@@@@@@@@@@@@@ slave id: {slave_id} @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")


buildings = ucdavis_buildings()
all_dv_ids = []
month_offset = {}
month_span = {}
sema = {}
bad = {}
all_streams = []
for b in buildings:
    for c in ucdavis_ceeds_of(b):
        if c == os.environ.get("CEED", "Electricity"):
            for stream_att in ucdavis_streams_of(b):
                stream_id = ucdavis_streams_of(b)[stream_att]
                all_streams.append((b, stream_att, stream_id))
                month_offset[stream_id] = 0
                bad[stream_id] = False

namespace_id = os.environ.get("NAMESPACE_ID", "UC__Davis")

print(
    f"@@@@@ Slave id: {slave_id} \n\n ## of streams = {len(all_streams)}\n\n > all_streams={all_streams}\n\nbad={bad}"
)


def login(self):
    self.ocs_client = OCSClient(
        "v1-preview",
        "65292b6c-ec16-414a-b583-ce7ae04046d4",
        "https://dat-b.osisoft.com",
        os.environ["CLIENT_ID"],
        os.environ["CLIENT_SECRET"],
        web_client=self.client,
    )
    # self.ocs_client.request_timeout = int(os.environ.get("OCS_TIMEOUT", "30"))
    self.dv_month_span = int(os.environ.get("DV_SPAN_MONTH", "4"))
    self.dv_min_interval = int(os.environ.get("DV_INTERVAL", "20"))
    self.event_count = int(self.dv_month_span * 30 * 24 * 60 / self.dv_min_interval) + 1
    print(
        f"@@@ Parameters: month_span= {self.dv_month_span}, interval= {self.dv_min_interval}, count= {self.event_count}"
    )


"""
max_tries = int(os.environ.get("MAX_TRIES_503", 6))


@backoff.on_exception(
    backoff.expo, Sds503, max_tries=max_tries, jitter=backoff.full_jitter
)
@backoff.on_exception(backoff.expo, SdsError, max_tries=4, jitter=backoff.full_jitter)
def get_interpolated_data(
    ocs_client, stream_id, start, end, count, stream_name, month_span
):
    result = ocs_client.Streams.getRangeValuesInterpolated(
        namespace_id,
        stream_id,
        None,
        start.isoformat(),
        end.isoformat(),
        count=count,
        locust_name=f"{stream_name}|{stream_id}:{month_span}",
    )
    return result

"""


def logout(self):
    pass


def get_data(self):
    # bc_dv_id = random.choice(all_dv_ids)
    # b, c, dv_id = bc_dv_id
    while True:
        _, stream_name, stream_id = random.choice(all_streams)
        if not bad[stream_id]:
            break

    offset = month_offset[stream_id]
    span = self.dv_month_span  # month_span[stream_id]
    print(
        f"@@@@@@@@@ testing stream {stream_id}|{stream_name}, off={offset}, span={span}"
    )
    # month_offset[stream_id] = (month_offset[stream_id] + span) % 36
    start = datetime.datetime(2017 + int(offset / 12), 1 + (offset % 12), 1, 0, 0)
    span_days = datetime.timedelta(days=span * 31)
    end = start + span_days
    # count = int(span * 30 * 24 * 60 / self.dv_min_interval) + 1
    try:
        result = ocs_stream_interpolated_data(
            self.ocs_client,
            namespace_id,
            stream_id,
            start.isoformat(),
            end.isoformat(),
            self.dv_min_interval,
            locust_name=f"{stream_name}|{stream_id}:{self.dv_month_span}",
        )
        print(
            f"@@@@@@@@@ result stream {stream_id}|{stream_name}:{self.dv_month_span} len={len(result)}"
        )
    except Sds503 as e:
        print(f"###################### 503 for {stream_id}|{stream_name}")
        raise e
    except SdsError as e:
        # 408s - no retry
        bad[stream_id] = True
        print(f"###################### 408 for {stream_id}|{stream_name}")
        raise e
        """ 
        print(f"###################### retry for {stream_id}|{stream_name}")
        try:
            result = get_interpolated_data(
                self.ocs_client,
                stream_id,
                start,
                end,
                count,
                stream_name,
                str(span) + "-retry",
            )
        except Sds503 as e:
            raise e
        except SdsError:
            print(f"!!!!##############!!!! RETRY FAILED for {stream_id}|{stream_name}")
            raise e
        """
    except Exception as e:
        print(f"###################### Exception for {stream_id}|{stream_name}")
        raise e

    month_offset[stream_id] = (month_offset[stream_id] + span) % 36


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
