#!/usr/bin/env python3

import pycgi, pycgitb
import os, platform, subprocess, requests, math

# pip install libcgipy
# sudo visudo
# www-data ALL=(ALL) NOPASSWD: /sbin/shutdown

class GetZabbixData:
    def __init__(
        self,
        url                 = "http://raspi5.lan:8080/api_jsonrpc.php",
        token               = "XXXXXXXXXXXXXXXXXX"
    ):
        self.zabbixURL      = url
        self.token          = token

    def zabbix_request(
        self,
        method,
        params
    ):
        payload             = {
            "jsonrpc"       : "2.0",
            "method"        : method,
            "params"        : params,
            "auth"          : self.token,
            "id"            : 1
        }
        try:
            r               = requests.post(self.zabbixURL, json = payload, timeout=5)
            r.raise_for_status()
        except Exception as e: 
            raise RuntimeError(f"Zabbix API request failed: {e}")
        
        res                 = r.json()
        if "error" in res:
            raise RuntimeError(
                f"""Zabbix API error {res['error']['code']}: 
{res['error']['message']} ({res['error'].get('data')})"""
            )

        return res
    
    def get_item_info(
        self,
        hostid              = "10084",
        key                 = "outside.temp",
        mode                = "filter"          # filter : 完全一致 search : 部分一致
    ):
        if mode not in ("filter", "search"):
            raise ValueError("mode must be 'filter' or 'search'")
        item                = self.zabbix_request(
            "item.get", 
            {
                "hostids"   : hostid,
                mode        : {
                    "key_"  : key
                },
                "output"    : [
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
        hostid              = "10084",
        key                 = "outside.temp"
    ):
        itemid, value_type  = self.get_item_info(hostid, key)

        value = self.zabbix_request(
            "history.get", 
            {
                "history"   : value_type,
                "itemids"   : itemid,
                "sortfield" : "clock",
                "sortorder" : "DESC",
                "limit"     : 1
            }
        ).get("result", [])

        if not value:
            raise ValueError(f"No history found for itemid {itemid}")

        return value[0]["value"]




class WebCGI():
    dirName = os.path.dirname(os.path.abspath(__file__))

    def __init__(self, lang = "ja", zabbix = True):
        with open(f"{os.path.dirname(self.dirName)}/template/html/index.html", "r", encoding="UTF-8") as index:
            self.template = index.read()
        if zabbix:
            with open(f"{os.path.dirname(self.dirName)}/TOKEN/zabbix.token", "r", encoding="UTF-8") as token:
                self.zabbixToken = token.read()
        else:
            self.zabbixToken = None

        self.lang                   = lang
        self.log                    = pycgitb.enable()
    
    def page_index(self, title = "Raspberry Pi 4B WebUI"): 
        with open(f"{os.path.dirname(self.dirName)}/template/html/styleConfig.html", "r", encoding="UTF-8") as html:
            head = html.read()
        with open(f"{os.path.dirname(self.dirName)}/template/html/body.html", "r", encoding="UTF-8") as html:
            body = html.read()
        
        return { 
            "title": f"{title}", 
            "head" : head,
            "html": body, 
            "css": """""",
            "style" : """""",
            "footer" : """
<script src="/view/js/bootstrap.bundle.min.js"></script>
<script> 
    setTimeout(
        function () {
            location.href = location.origin + location.pathname; 
        }, 30000
    ); 
</script>
""",
            
        }
    
    def gauge_create(
        self,
        radius          = 20,
        value           = "",
        valuePercent    = 0.5,
        svgClass        = "gauge",
        color           = "#4caf50",
        bgColor         = "#eee"
    ):
        maxLength   = math.pi * radius
        return f"""
<div class="position-relative d-inline-block text-start">
    <svg class = {svgClass} viewBox="0 0 {2 * radius + 20} {radius + 10}">
        <!-- 背景の半円 -->
        <path 
            d="M10,{radius + 10} A{radius},{radius} 0 0,1 {2*radius + 10}, {radius + 10}"
            fill="none" 
            stroke="{bgColor}" 
            stroke-width="{radius * 0.25}" 
        />

        <!-- 値の半円 -->
        <path 
            d="M10,{radius + 10} A{radius},{radius} 0 0,1 {2*radius + 10}, {radius + 10}"
            fill="none" 
            stroke = "{color}"
            stroke-width="{radius * 0.25}"
            stroke-linecap="round"
            stroke-dasharray="{maxLength * valuePercent} {maxLength}"
        />
    </svg>
    <div 
        class="
            position-absolute
            top-100 start-50
            translate-middle
            fw-bold
            fs-4
            text-center
            pe-none
        "
    >
        {value}
    </div>
</div>
"""

    def html_body(self, body = "", side = "", title = "Raspberry Pi 4B WebUI"):
        param           = self.page_index(title)
        radius          = 20
        xSize           = 300
        
        if self.zabbixToken is not None:
            data        = GetZabbixData(token = self.zabbixToken)
            temp        = float(data.data_request(hostid = "10084", key = "outside.temp"))
            hum         = float(data.data_request(hostid = "10084", key = "outside.hum"))
        else:
            temp        = 20
            hum         = 50

        tempValue       = max(0, min(1, (temp - (-20)) / (60 - (-20))))
        if temp < 0:
            tempColor   = "#6600FF"
        elif temp < 20:
            tempColor   = "#66CCFF"
        elif temp < 30:
            tempColor   = "#66FF33"
        elif temp < 35:
            tempColor   = "#FF9900"
        elif temp < 45:
            tempColor   = "#FF3366"
        else:
            tempColor   = "#FF0000"

        humValue        = max(0, min(1, hum / 100))
        if hum < 20:
            humColor    = "#FF9900"
        elif hum < 40:
            humColor    = "#66FF33"
        elif hum < 50:
            humColor    = "#99FFFF"
        elif hum < 60:
            humColor    = "#6699FF"
        elif hum < 80:
            humColor    = "#3333CC"
        else:
            humColor    = "#0033CC"

        param["css"]    += f"""
.gauge {{
    width: {xSize}px;
    height: auto;
    display: block;
}}
"""
        param["html"]   += f"""
<body>
    <div class="container pt-3">
        <main>
            <div class="row g-5">
                <div class="col-md-8">
                    <div class="d-flex flex-wrap justify-content-start gap-3 pt-3">
                        <div class="card shadow-sm text-center" style="width: fit-content;">
                            <div class="card-header text-start fw-bold">
                                温度
                            </div>
                            <div class="card-body">
                                {
                                    self.gauge_create(
                                        radius          = radius,
                                        value           = f"{temp:.2f}℃",
                                        valuePercent    = tempValue,
                                        color           = tempColor
                                    )
                                }
                            </div>
                        </div>
                        <div class="card shadow-sm text-center" style="width: fit-content;">
                            <div class="card-header text-start fw-bold">
                                湿度
                            </div>
                            <div class="card-body">
                                {
                                    self.gauge_create(
                                        radius          = radius,
                                        value           = f"{hum:.2f}%",
                                        valuePercent    = humValue,
                                        color           = humColor
                                    )
                                }
                            </div>
                        </div>
                    </div>
                    {body}
                
                </div>
                <div class="col-md-4">
                    <div class="position-sticky" style="top: 2rem;">
                        {side}
                    </div>
                </div>
            </div>
        
        </main>
    </div>
</body>"""
        return param
    def cmd_exe(self, cmd = []):
        return subprocess.run(
            cmd,                    # コマンドをリストで渡す（安全） 
            capture_output=True,    # stdout / stderr を取得 
            text=True               # str で受け取る（デフォは bytes） 
        )
    def poweroff(self, mode):
        osName = platform.system()
        if osName == "Windows": 
            second = 30
            if mode     == "shutdown":
                self.log.handler(self.cmd_exe(["shutdown", "-s", "-f", "-t", f"{second}"]))
                value = f"{second}秒後にシャットダウンします"

            elif mode   == "reboot":
                self.log.handler(self.cmd_exe(["shutdown", "-r", "-f", "-t", f"{second}"]))
                value = f"{second}秒後に再起動します"
                
            else:
                self.log.handler(self.cmd_exe(["shutdown", "-a"]))
                value = f"予約された電源動作をキャンセルしました"

        elif osName == "Linux": 
            second = 60
            if mode     == "shutdown":
                self.log.handler(self.cmd_exe(["sudo", "shutdown", "-h", f"+{second//60}"]))
                value = f"{second}秒後にシャットダウンします"

            elif mode   == "reboot":
                self.log.handler(self.cmd_exe(["sudo", "shutdown", "-r", f"+{second//60}"]))
                value = f"{second}秒後に再起動します"

            else:
                self.log.handler(self.cmd_exe(["sudo", "shutdown", "-c"]))
                value = f"予約された電源動作をキャンセルしました"
            
        return self.html_body(
            body = f"""
<h2 class="pt-4 mt-4 border-bottom fw-bold">{value}</h2>
"""
        )
    def urls(self, url):
        if url in ["shutdown", "reboot", "stop"]:
            param = self.poweroff(url)
        else:
            param = self.html_body()
        return self.template.format(lang=self.lang, **param)


if __name__ == "__main__": 
    form    = pycgi.FieldStorage()
    html    = WebCGI()

    print(html.urls(form.getvalue("url", default = "index")))