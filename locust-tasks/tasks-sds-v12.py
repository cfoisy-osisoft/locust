from locust import HttpLocust, TaskSet, between
import datetime
import socket
from ocs_sample_library_preview import OCSClient, Sds503, SdsError
from ocs_hackdavis import (
    ucdavis_buildings,
    ucdavis_ceeds_of,
    ucdavis_dataview_id,
    ucdavis_config_data,
)
import random
import os
from gevent.lock import BoundedSemaphore
import backoff
import logging
from random import randrange
import math

logging.getLogger("backoff").addHandler(logging.StreamHandler())

bad_dv_ids = []
"""
    "hackdavis_4a9ca644",
    "hackdavis_0c857c77",  # Hopkins
    "hackdavis_f41831e3",
    "hackdavis_7827eb8e",
    "hackdavis_d05b4878",  # Kerr Hall
    "hackdavis_ce59eb5f",  # Medical Sciences I D 
"""


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
all_tags = []
for b in buildings:
    for c in ucdavis_ceeds_of(b):
        if c == "Electricity":
            dv_id = ucdavis_dataview_id(b, c)
            if dv_id not in bad_dv_ids:
                if int(f"0x{dv_id[-2:]}", 16) % 3 >= 0:  # == slave_id:
                    dv_id = ucdavis_dataview_id(b, c)
                    all_dv_ids.append((b, c, dv_id))
                    all_tags.append((b, c, dv_id[dv_id.find("_") + 1 :]))
                # month_offset[dv_id] = 0

namespace_id = os.environ.get("NAMESPACE_ID", "UC__Davis")
tocs_client = OCSClient(
    "v1-preview",
    "65292b6c-ec16-414a-b583-ce7ae04046d4",
    "https://dat-b.osisoft.com",
    os.environ["CLIENT_ID"],
    os.environ["CLIENT_SECRET"],
)
# streams = tocs_client.Streams.getStreams(os.environ.get("NAMESPACE_ID", "UC__Davis"), count=5000)
# all_streams = [s.Id for s in streams]
# for s in all_streams:
#    month_offset[s] = 0
dense_streams = [
    "PI_uni-pida-vm0_532",
    "PI_uni-pida-vm0_564",
    "PI_uni-pida-vm0_404",
    "PI_uni-pida-vm0_293",
    "PI_uni-pida-vm0_19",
    "PI_uni-pida-vm0_1006",
    "PI_uni-pida-vm0_2250",
    "PI_uni-pida-vm0_1033",
    "PI_uni-pida-vm0_1601",
    "PI_uni-pida-vm0_2191",
    "PI_uni-pida-vm0_880",
    "PI_uni-pida-vm0_1029",
    "PI_uni-pida-vm0_948",
    "PI_uni-pida-vm0_2263",
    "PI_uni-pida-vm0_2687",
    "PI_uni-pida-vm0_2373",
    "PI_uni-pida-vm0_1234",
    "PI_uni-pida-vm0_1607",
    "PI_uni-pida-vm0_1158",
    "PI_uni-pida-vm0_1087",
    "PI_uni-pida-vm0_1585",
    "PI_uni-pida-vm0_2021",
    "PI_uni-pida-vm0_952",
    "PI_uni-pida-vm0_1693",
    "PI_uni-pida-vm0_1822",
    "PI_uni-pida-vm0_2300",
    "PI_uni-pida-vm0_2015",
    "PI_uni-pida-vm0_1112",
    "PI_uni-pida-vm0_2013",
    "PI_uni-pida-vm0_1113",
    "PI_uni-pida-vm0_2220",
    "PI_uni-pida-vm0_2070",
    "PI_uni-pida-vm0_666",
    "PI_uni-pida-vm0_576",
    "PI_uni-pida-vm0_1657",
    "PI_uni-pida-vm0_1696",
    "PI_uni-pida-vm0_2624",
    # new batch 01/14
    "PI_uni-pida-vm0_1826",
    "PI_uni-pida-vm0_543",
    "PI_uni-pida-vm0_1918",
    "PI_uni-pida-vm0_11735",
    "PI_uni-pida-vm0_409",
    "PI_uni-pida-vm0_541",
    "PI_uni-pida-vm0_437",
    "PI_uni-pida-vm0_531",
    "PI_uni-pida-vm0_535",
]


all_streams = []
for b, _, tag in all_tags:
    streams = tocs_client.Streams.getStreams(namespace_id, query=f"{tag}_building:*")
    print(f"# streams for tag {tag} ({b}) is {len(streams)}")
    for s in streams:
        stream_id = s.Id
        if s.Id in dense_streams:
            stream_id += "_ds2m"
        all_streams.append((stream_id, s.Name))
        month_offset[stream_id] = 0
        month_span[stream_id] = int(os.environ.get("DV_SPAN_MONTH", "4"))
        sema[stream_id] = BoundedSemaphore()
        bad[stream_id] = False

print(
    f"@@@@@ Slave id: {slave_id} \n\n ## of streams = {len(all_streams)}\n\n > all_streams={all_streams}"
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
    self.ocs_client.request_timeout = int(os.environ.get("OCS_TIMEOUT", "30"))
    self.dv_month_span = int(os.environ.get("DV_SPAN_MONTH", "4"))
    self.dv_min_interval = int(os.environ.get("DV_INTERVAL", "20"))
    self.event_count = int(self.dv_month_span * 30 * 24 * 60 / self.dv_min_interval) + 1
    print(
        f"@@@ Parameters: month_span= {self.dv_month_span}, interval= {self.dv_min_interval}, count= {self.event_count}"
    )


max_tries = int(os.environ.get("MAX_TRIES_503", 6))


@backoff.on_exception(
    backoff.expo, Sds503, max_tries=max_tries, jitter=backoff.full_jitter
)
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


def logout(self):
    pass


def get_data(self):
    # bc_dv_id = random.choice(all_dv_ids)
    # b, c, dv_id = bc_dv_id
    stream_id, stream_name = random.choice(all_streams)

    offset = month_offset[stream_id]
    span = month_span[stream_id]
    # month_offset[stream_id] = (month_offset[stream_id] + span) % 36
    start = datetime.datetime(2017 + int(offset / 12), 1 + (offset % 12), 1, 0, 0)
    span_days = datetime.timedelta(days=span * 30)
    end = start + span_days
    count = int(span * 30 * 24 * 60 / self.dv_min_interval) + 1
    try:
        result = get_interpolated_data(
            self.ocs_client, stream_id, start, end, count, stream_name, span,
        )
    except Sds503 as e:
        raise e
    except SdsError as e:
        # 408s
        if month_span[stream_id] < 1:
            old_span = month_span[stream_id]
            span = 1  # int(math.ceil(month_span[stream_id] / 2.0))
            month_span[stream_id] = span
            print(
                f"@@@@@@@@@@@@@@@@@@@@@@ [{old_span}=>{span}] for {stream_id}|{stream_name}"
            )
        else:
            print(
                f"###################### span already 1 for {stream_id}|{stream_name}"
            )
        raise e
    except Exception as e:
        raise e

    month_offset[stream_id] = (month_offset[stream_id] + span) % 36
    # finally:
    #     sema[stream_id].release()
    """
    try:
        result = self.ocs_client.Streams.getRangeValuesInterpolated(
            namespace_id,
            stream_id,
            None,
            start.isoformat(),
            end.isoformat(),
            count=pan: {stream_id}|{stream_name}: from {old_span} -> {span}"ielf.event_count,
            locust_name=f"{stream_name}|{stream_id}:{self.dv_month_span}")  # :{offset:02}")
    except:
        pass 
    finally:
        sema[stream_id].release()

    csv, token = self.ocs_client.DataViews.getDataInterpolated(
        namespace_id=os.environ.get("NAMESPACE_ID", "UC__Davis"),
        dataView_id=dv_id,
        startIndex=start.isoformat(),
        endIndex=(start + span_days).isoformat(),
        interval=f"00:{self.dv_min_interval}:00",
        count=250000,
        form="csvh",
        locust_name=f"{bc_dv_id}:{self.dv_month_span}":{offset:02}",
    )
    """


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
