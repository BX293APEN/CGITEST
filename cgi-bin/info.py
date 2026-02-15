#!/usr/bin/env python3

# pip install pandas_datareader
from datetime import datetime, date
from zoneinfo import ZoneInfo
# from pandas_datareader import data as pdr
import requests, json, os, math
import yfinance as yf

class GetZabbixData:
    def __init__(
        self,
        url                             = "http://raspi5.lan:8080/api_jsonrpc.php",
        token                           = "XXXXXXXXXXXXXXXXXX"
    ):
        self.zabbixURL                  = url
        self.token                      = token

    def zabbix_request(
        self,
        method,
        params
    ):
        payload                         = {
            "jsonrpc"                   : "2.0",
            "method"                    : method,
            "params"                    : params,
            "auth"                      : self.token,
            "id"                        : 1
        }
        try:
            r                           = requests.post(self.zabbixURL, json = payload, timeout=5)
            r.raise_for_status()
        except Exception as e: 
            raise RuntimeError(f"Zabbix API request failed: {e}")
        
        res                             = r.json()
        if "error" in res:
            raise RuntimeError(
                f"""Zabbix API error {res['error']['code']}: 
{res['error']['message']} ({res['error'].get('data')})"""
            )

        return res
    
    def get_item_info(
        self,
        hostid                          = "10084",
        key                             = "outside.temp",
        mode                            = "filter"          # filter : 完全一致 search : 部分一致
    ):
        if mode not in ("filter", "search"):
            raise ValueError("mode must be 'filter' or 'search'")
        item                            = self.zabbix_request(
            "item.get", 
            {
                "hostids"               : hostid,
                mode                    : {
                    "key_"              : key
                },
                "output"                : [
                    "itemid", 
                    "value_type"
                ]
            }
        ).get("result", [])

        if not item: 
            raise ValueError(f"Item '{key}' not found on host {hostid}")
        
        if len(item) > 1:
            print(f"Warning: multiple items matched '{key}', using first")

        return item[0]["itemid"], item[0]["value_type"]
    
    def data_request(   # 最新値を取得
        self,
        hostid                          = "10084",
        key                             = "outside.temp"
    ):
        itemid, value_type              = self.get_item_info(hostid, key)

        value                           = self.zabbix_request(
            "history.get", 
            {
                "history"               : value_type,
                "itemids"               : itemid,
                "sortfield"             : "clock",
                "sortorder"             : "DESC",
                "limit"                 : 1
            }
        ).get("result", [])

        if not value:
            raise ValueError(f"No history found for itemid {itemid}")

        return value[0]["value"]

class RequestWebAPI:
    def __init__(self, pair='USDJPY=X'):
        self.pair = pair

    def get_doltoyen(self):
        try:
            ticker = yf.Ticker(self.pair)

            # 1分足の最新データを取得（最も安定）
            data = ticker.history(period="1d", interval="1m")

            if data.empty:
                raise ValueError("Empty data from Yahoo")

            # 最新の終値（実質リアルタイム）
            price = data["Close"].iloc[-1]

            if hasattr(price, "item"):
                price = price.item()

            if not isinstance(price, (float, int)) or math.isnan(price):
                raise ValueError("Invalid price")

            return float(price)

        except Exception as e:
            print(e)
            return 100



class RequestWeather:
    def __init__(
        self,
        weatherURL                      = "https://weather.tsukumijima.net/api/forecast/city/",
        cities                          = {
            "Aichi"                     : {
                "id"                    : "230010",
                "weather"               : []
            }, 
            "Tokyo"                     : {
                "id"                    : "130010",
                "weather"               : []
            }, 
            "Osaka"                     : {
                "id"                    : "270000",
                "weather"               : []
            }, 
            "Okinawa"                   : {
                "id"                    : "471010",
                "weather"               : []
            }, 
            "Hokkaido"                  : {
                "id"                    : "016010",
                "weather"               : []
            }, 
        }
    ):
        self.weatherURL                 = weatherURL
        self.cities                     = cities
    
    def get_weather(self):
        for city in self.cities:
            cityparam                   = self.cities[city]["id"]
            url                         = f"{self.weatherURL}{cityparam}"
            try:
                tenki_data              = requests.get(url, timeout=3)
                data                    = json.loads(tenki_data.text)
                self.cities[city]["weather"].clear()
            except Exception as e:
                print(e)
                continue
            
            for daten in range(3):
                try:
                    if daten            == 2:
                        weather_data    = data["forecasts"][daten]["telop"]
                    else:
                        weather_data    = data["forecasts"][daten]["detail"]["weather"]
                    weather_data        = weather_data.replace("\u3000","")
                except Exception as e:
                    print(e)
                    weather_data        = "取得失敗"
                finally:
                    self.cities[city]["weather"].append(str(weather_data))

        return self.cities
    
class JSONDataCreate():
    dirName = os.path.dirname(os.path.abspath(__file__))

    def __init__(self):
        self.weather                    = RequestWeather()
        self.api                        = RequestWebAPI()
        with open(f"{os.path.dirname(self.dirName)}/TOKEN/zabbix.token", "r", encoding="UTF-8") as token:
            self.zabbixToken = token.read()
            self.zbxdata                = GetZabbixData(token = self.zabbixToken)

    def get_data(self, hostid = "10688"):
        JPYUSD                          = self.api.get_doltoyen()
        self.cities                     = self.weather.get_weather()
        hostName                        = self.zbxdata.data_request(hostid = hostid, key = "system.hostname")
        cpuTemp                         = float(self.zbxdata.data_request(hostid = hostid, key = "cpu.temp"))
        self.tmp                        = float(self.zbxdata.data_request(hostid = "10084", key = "outside.temp"))
        self.rhm                        = float(self.zbxdata.data_request(hostid = "10084", key = "outside.hum"))
        
        data                            = { 
            "HostName"                  : hostName,
            "CPUTemp"                   : cpuTemp,
            "温度"                      : f"{self.tmp:4.2f}℃",
            "湿度"                      : f"{self.rhm:4.2f}%",
            "為替"                      :{
                "ドル円"                : str(JPYUSD)
            },
            "天気"                      :{
                "北海道"                :{
                    "今日"              : self.cities["Hokkaido"]["weather"][0],
                    "明日"              : self.cities["Hokkaido"]["weather"][1],
                    "明後日"            : self.cities["Hokkaido"]["weather"][2],
                },
                "東京都"                :{
                    "今日"              : self.cities["Tokyo"]["weather"][0],
                    "明日"              : self.cities["Tokyo"]["weather"][1],
                    "明後日"            : self.cities["Tokyo"]["weather"][2],
                },
                "愛知県"                :{
                    "今日"              : self.cities["Aichi"]["weather"][0],
                    "明日"              : self.cities["Aichi"]["weather"][1],
                    "明後日"            : self.cities["Aichi"]["weather"][2],
                },
                "大阪府"                :{
                    "今日"              : self.cities["Osaka"]["weather"][0],
                    "明日"              : self.cities["Osaka"]["weather"][1],
                    "明後日"            : self.cities["Osaka"]["weather"][2],
                },
                "沖縄県"                :{
                    "今日"              : self.cities["Okinawa"]["weather"][0],
                    "明日"              : self.cities["Okinawa"]["weather"][1],
                    "明後日"            : self.cities["Okinawa"]["weather"][2],
                }
            },
            "UpdateTime"                : datetime.strftime(datetime.now(ZoneInfo("Asia/Tokyo")), '%Y/%m/%d %H:%M:%S'),
            
        }

        return data
    


if __name__ == "__main__": 
    data = JSONDataCreate()
    print("""Content-Type: application/json; charset=UTF-8
""")
    print(
        json.dumps(
            data.get_data("10688"),
            ensure_ascii = False,
            indent = 4
        )
    )