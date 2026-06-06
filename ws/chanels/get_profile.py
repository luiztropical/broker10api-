import datetime
import time
from broker10api.ws.chanels.base import Base
import broker10api.global_value as global_value

class Get_profile(Base):
    name = "sendMessage"
    def __call__(self,req_id):
        data = {"name":"get-profile","version":"1.0","body":{}}

        self.send_websocket_request(self.name, data,request_id=req_id)
