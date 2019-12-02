from locust import HttpLocust, TaskSet, between
from ocs_sample_library_preview import OCSClient
from ocs_hackdavis import (
    ucdavis_buildings,
    ucdavis_ceeds_of,
    ucdavis_dataview_id,
    ucdavis_get_config_data,
)
import random

buildings = ucdavis_buildings()
all_dv_ids = []
for b in buildings:
    for c in ucdavis_ceeds_of(b):
        all_dv_ids.append( (b, c, ucdavis_dataview_id(b, c)) )


def login(self):
    self.ocs_client = OCSClient(
        "v1-preview",
        "65292b6c-ec16-414a-b583-ce7ae04046d4",
        "https://dat-b.osisoft.com",
        "<client-id>",
        "<client-secret>",
        web_client=self.client,
    )
    # l.client.post("/login", {"username":"ellen_key", "password":"education"})


def logout(self):
    pass
    # l.client.post("/logout", {"username":"ellen_key", "password":"education"})


def get_dv(self):
    dv_id = random.choice(all_dv_ids)
    csv, token = self.ocs_client.Dataviews.getDataInterpolated(
        namespace_id="UC__Davis",
        dataview_id=dv_id,
        startIndex="2019-03-18",
        endIndex="2019-05-18",
        interval="00:05:00",
        count=200000,
        form="csvh",
        locust_name=f"Dataview: {dv_id}",
    )

    # l.client.get("/")


class UserBehavior(TaskSet):
    tasks = {get_dv: 1}

    def on_start(self):
        login(self)

    def on_stop(self):
        logout(self)


class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    wait_time = between(3.0, 5.0)
