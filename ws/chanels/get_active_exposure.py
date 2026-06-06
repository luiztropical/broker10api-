import time
from broker10api.ws.chanels.base import Base
import broker10api.global_value as global_value
from broker10api.expiration import get_expiration_time,get_digital_exp
class Get_Active_Exposure(Base):
    name = "sendMessage"
    def __call__(self,instrument_type,active_id,duration,request_id,currency="USD"):
        #"instrument_type""turbo-option"
        if instrument_type=="digital-option":
            exp=get_digital_exp(int(self.api.timesync.server_timestamp),duration)
        else:
            exp,_=get_expiration_time(int(self.api.timesync.server_timestamp),duration)
        
         
        data = {
        "name": "get-active-exposure",
        "version":"1.0",
        "body":{"instrument_type":instrument_type,"active_id":active_id,"time":exp,"currency":currency}
        }
        self.send_websocket_request(self.name, data,request_id=request_id) 
        
        
