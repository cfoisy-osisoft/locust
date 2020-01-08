from locust import HttpLocust, TaskSet, between
import datetime
from ocs_sample_library_preview import OCSClient
from ocs_hackdavis import (
    ucdavis_buildings,
    ucdavis_ceeds_of,
    ucdavis_dataview_id,
    ucdavis_config_data,
)
import random
import os


bad_dv_ids = ["hackdavis_4a9ca644"]

buildings = ucdavis_buildings()
all_dv_ids = []
month_offset = {}
for b in buildings:
    for c in ucdavis_ceeds_of(b):
        if c == "Electricity":
            dv_id = ucdavis_dataview_id(b, c)
            if dv_id not in bad_dv_ids:
                all_dv_ids.append( (b, c, ucdavis_dataview_id(b, c)) )
                month_offset[dv_id] = 0


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
    self.dv_min_interval = os.environ.get("DV_INTERVAL", "20")


def logout(self):
    pass


def get_dv(self):
    bc_dv_id = random.choice(all_dv_ids)
    b, c, dv_id = bc_dv_id
    offset = month_offset[dv_id]
    month_offset[dv_id] = (month_offset[dv_id] + self.dv_month_span) % 36
    start = datetime.datetime(2017 + int(offset/12), (1 + offset) % 12, 1, 0, 0)
    span_days = datetime.timedelta(days=self.dv_month_span*30)
    csv, token = self.ocs_client.DataViews.getDataInterpolated(
        namespace_id=os.environ.get("NAMESPACE_ID", "UC__Davis"),
        dataView_id=dv_id,
        startIndex=start.isoformat(),
        endIndex=(start + span_days).isoformat(),
        interval=f"00:{self.dv_min_interval}:00",
        count=250000,
        form="csvh",
        locust_name=f"{bc_dv_id}:{self.dv_month_span}:{offset:02}",
    )


class UserBehavior(TaskSet):
    tasks = {get_dv: 1}

    def on_start(self):
        login(self)

    def on_stop(self):
        logout(self)


class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    min_wait_time = float(os.environ.get("LOCUST_MIN_WAIT", "3.0"))
    max_wait_time = float(os.environ.get("LOCUST_MAX_WAIT", "5.0"))

    wait_time = between(min_wait_time, max_wait_time)

