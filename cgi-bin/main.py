#!/usr/bin/env python3

import pycgi, pycgitb
import os, platform, subprocess, requests, math, psutil, markdown

# sudo apt install python3-psutil
# pip install libcgipy markdown
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
        for p in psutil.process_iter():
            try:
                p.cpu_percent(None)
            except:
                pass
        with open(f"{os.path.dirname(self.dirName)}/template/html/index.html", "r", encoding="UTF-8") as index:
            self.template = index.read()
        if zabbix:
            with open(f"{os.path.dirname(self.dirName)}/TOKEN/zabbix.token", "r", encoding="UTF-8") as token:
                self.zabbixToken = token.read()
        else:
            self.zabbixToken = None

        self.lang                   = lang
        self.log                    = pycgitb.enable()
        self.md                     = markdown.Markdown(extensions=["extra", "tables", "attr_list"])
    
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
        bgColor         = "#eee",
        scales          = [0, 100]
    ):
        maxLength       = math.pi * radius
        
        margin          = 10
        # 中心座標 (cx, cy)
        cx              = radius + margin
        cy              = radius + margin
        
        # 針の長さ
        rNeedle         = radius * 1.15
        angle           = math.pi * (1 - valuePercent)
        xNeedle         = cx + rNeedle * math.cos(angle)
        yNeedle         = cy - rNeedle * math.sin(angle)

        scaleLine       = ""
        for s in scales:
            p           = (s - scales[0]) / (scales[-1] - scales[0])
            p           = max(0, min(1, p))

            angle       = math.pi * (1 - p)

            r1          = radius * 0.85   # 内側
            r2          = radius * 1.00   # 外側

            x1          = cx + r1 * math.cos(angle)
            y1          = cy - r1 * math.sin(angle)
            x2          = cx + r2 * math.cos(angle)
            y2          = cy - r2 * math.sin(angle)

            scaleLine += f"""
            <line
                x1="{x1}" y1="{y1}"
                x2="{x2}" y2="{y2}"
                stroke="#666"
                stroke-width="0.5"
            />
            """
        
        return f"""
<div class="position-relative d-inline-block text-start">
    <svg class = {svgClass} viewBox="0 0 {2 * radius + (margin * 2)} {radius + (margin * 2)}">
        <!-- 背景の半円 -->
        <path 
            d="
                M
                    {margin},{cy} 
                A
                    {radius},{radius} 
                    0 0,1 
                    {2*radius + margin}, {cy}
            "
            fill="none" 
            stroke="{bgColor}" 
            stroke-width="{margin/2}" 
        />

        <!-- 値の半円 -->
        <path 
            d="
                M
                    {margin},{cy} 
                A
                    {radius},{radius} 
                    0 0,1 
                    {2*radius + margin}, {cy}
            "
            fill="none" 
            stroke = "{color}"
            stroke-width="{margin/2}"
            stroke-linecap="butt"
            stroke-dasharray="{maxLength * valuePercent} {maxLength}"
        />
        <!-- 目盛り -->
            {scaleLine}
        <!-- 針 -->
        <line
            x1="{cx}" y1="{cy}"
            x2="{xNeedle}" y2="{yNeedle}"
            stroke="#000"
            stroke-width="0.5"
        />

        <!-- 中心の丸 -->
        <circle
            cx="{cx}" cy="{cy}"
            r="{radius * 0.08}"
            fill="#000"
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
    

    def card_create(self, title = "情報", message = ""):
        return f"""
<div class="row mb-2 pt-4">
    <div class="col-12">
        <div class="row g-0 border rounded overflow-hidden flex-md-row mb-4 shadow-sm position-relative">
            <div class="col p-4 d-flex flex-column position-static">
                <h3 class="mb-0">{title}</h3>
                <p class="card-text mb-auto mt-3">
                    {message}
                </p>
            </div>
        </div>
    </div>
</div>
"""

    def html_body(self, body = "", title = "Raspberry Pi 4B WebUI", hostid = "10084"):
        param           = self.page_index(title)
        radius          = 20
        xSize           = 300
        
        if self.zabbixToken is not None:
            data        = GetZabbixData(token = self.zabbixToken)
            temp        = float(data.data_request(hostid = "10084", key = "outside.temp"))
            hum         = float(data.data_request(hostid = "10084", key = "outside.hum"))
            cpuTemp     = float(data.data_request(hostid = hostid, key = "cpu.temp"))
            hostName    = data.data_request(hostid = hostid, key = "system.hostname")
        else:
            temp        = 20
            hum         = 50

        tempValue       = max(0, min(1, (temp - (-20)) / (60 - (-20))))
        if temp < 0:
            tempColor   = "#6600FF"
        elif temp < 20:
            tempColor   = "#66CCFF"
        elif temp < 30:
            tempColor   = "#009933"
        elif temp < 35:
            tempColor   = "#FF9900"
            body        += self.card_create(title = "注意", message = "気温が高くなっています")
        elif temp < 45:
            tempColor   = "#FF3366"
            body        += self.card_create(title = "警告", message = "気温が高くなっています")
        else:
            tempColor   = "#FF0000"
            body        += self.card_create(title = "警告", message = "気温が高くなっています")

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
        
        cpuValue        = max(0, min(1, (cpuTemp - 0) / (100 - 0)))
        if cpuTemp < 30:
            cpuColor   = "#66CCFF"
        elif cpuTemp < 40:
            cpuColor   = "#009933"
        elif cpuTemp < 50:
            cpuColor   = "#FF9900"
        elif cpuTemp < 60:
            cpuColor   = "#FF3366"
            body        += self.card_create(title = "注意", message = "CPU温度が高くなっています")
        else:
            cpuColor   = "#FF0000"
            body        += self.card_create(title = "警告", message = "CPU温度が高くなっています")
        

        processTable    = f"""| PID | NAME | CPU | メモリ | 使用ポート |
| -   |  -   | -   | -      | - |
"""

        # まず全接続を取得して PID → ポート一覧 の辞書を作る
        pid_ports = {}

        for conn in psutil.net_connections(kind='inet'):
            if conn.pid and conn.laddr and conn.status == psutil.CONN_LISTEN:
                pid_ports.setdefault(conn.pid, set()).add(conn.laddr.port)

        
        warningApps = []
        # プロセス一覧を表示
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            info        = p.info
            pid         = info['pid']
            nameFull    = info['name']
            name        = nameFull 
            if len(nameFull) > 16: 
                name    = f"{nameFull[:16]}..."

            cpu         = info.get('cpu_percent', -1) / psutil.cpu_count()
            cpu_str     = f"{cpu:.2f}%" 
            if cpu < 0: 
                cpu_str = "N/A"

            mem         = float(info['memory_info'].rss)/(1024*1024) if info.get('memory_info') else '?'

            # ポート一覧（LISTENのみ）
            ports       = map(str,sorted(pid_ports.get(pid, set())))
            port_str    = ", ".join(ports)

            if mem == '?':
                mem_style = ""
            elif mem > 500:
                mem_style = "bg-danger text-black fw-bold"   # 赤
                warningApps.append(f"| {pid} | {nameFull} | {mem:.2f}MB |")
            elif mem > 200:
                mem_style = "bg-warning text-black fw-bold"  # オレンジ
                warningApps.append(f"| {pid} | {nameFull} | {mem:.2f}MB |")
            else:
                mem_style = ""
                

            processTable += f"""| {pid} | {name} | {cpu_str} | <span class="{mem_style}">{mem:.2f}MB</span> | {port_str} |
"""
        processTable = self.md.convert(processTable)
        processTable = processTable.replace(
            "<table>", 
            """<table class= "table table-bordered table-striped">"""
        ).replace(
            "<td>",
            """<td class="text-nowrap">"""
        )

        processTable = f"""
<div class = "pt-4">
    {processTable}
</div>
""" 
        if len(warningApps) > 0:
            apps = f"""
| PID | アプリ名 | メモリ使用量 |
| - | - | - |
{"\n".join(warningApps)}"""
            apps = self.md.convert(apps)
            apps = apps.replace(
                "<table>", 
                """<table class= "table table-bordered table-striped">"""
            ).replace(
                "<td>",
                """<td class="text-nowrap">"""
            )
            body        += self.card_create(title = "注意", message = f"""<h4 class="mb-4 border-bottom">メモリ使用量が多いアプリ</h4>{apps}""")

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
                                        color           = tempColor,
                                        scales          = [-20, 0, 20, 30, 35, 45, 60]
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
                                        color           = humColor,
                                        scales          = [0, 20, 40, 50, 60, 80, 100]
                                    )
                                }
                            </div>
                        </div>
                        <div class="card shadow-sm text-center" style="width: fit-content;">
                            <div class="card-header text-start fw-bold">
                                {hostName} CPU温度
                            </div>
                            <div class="card-body">
                                {
                                    self.gauge_create(
                                        radius          = radius,
                                        value           = f"{cpuTemp:.2f}℃",
                                        valuePercent    = cpuValue,
                                        color           = cpuColor,
                                        scales          = [0, 30, 40, 50, 60, 100]
                                    )
                                }
                            </div>
                        </div>
                    </div>
                    
                    <div class="pt-4">
                        <div class = "border-top">
                            {body}
                        </div>
                    </div>
                
                </div>
                <div class="col-md-4">
                    <div class="position-sticky" style="top: 2rem;">
                        {processTable}
                    </div>
                </div>
            </div>
        
        </main>
    </div>
</body>"""
        return param
    def cmd_exe(self, cmd = []):
        return subprocess.run(
            cmd,
            capture_output  = True,
            text            = True
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
            
        return self.html_body(body = f"""{self.card_create(message = value)}""")
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