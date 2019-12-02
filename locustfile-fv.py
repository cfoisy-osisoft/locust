from locust import HttpLocust, TaskSet, between
from ocs_sample_library_preview import OCSClient
import random

fv_range = range(31, 37)
all_dv_ids = (
    [f"HubDV_All_Data_fv{i}" for i in fv_range]
    + [f"HubDV_All_Data_fv{i}" for i in fv_range]
    + [f"HubDV_Cooling_Prediction_fv{i}" for i in fv_range]
    + [f"HubDV_PCA_fv{i}" for i in fv_range]
)


def login(self):
    self.ocs_client = OCSClient(
        "v1-preview",
        "65292b6c-ec16-414a-b583-ce7ae04046d4",
        "https://dat-b.osisoft.com",
        "228d0d48-c8b2-4cdd-8c4e-a156654432f3",
        "2/YME45JhNfv97W/gB/GR0Z6A64QM54rvn/uRiMAK18=",
        web_client=self.client,
    )
    # l.client.post("/login", {"username":"ellen_key", "password":"education"})


def logout(self):
    pass
    # l.client.post("/logout", {"username":"ellen_key", "password":"education"})


def get_dv(self):
    dv_id = random.choice(all_dv_ids)
    csv, token = self.ocs_client.Dataviews.getDataInterpolated(
        namespace_id="fermenter_vessels",
        dataview_id=dv_id,
        startIndex="2017-03-18",
        endIndex="2017-04-18",
        interval="00:05:00",
        count=100000,
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
    wait_time = between(5.0, 9.0)