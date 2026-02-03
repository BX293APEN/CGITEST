#!/usr/bin/env python3

import pycgi, pycgitb
import os, platform, subprocess

# sudo visudo
# www-data ALL=(ALL) NOPASSWD: /sbin/shutdown

class WebCGI():
    dirName = os.path.dirname(os.path.abspath(__file__))

    def __init__(self, lang = "ja"):
        with open(f"{os.path.dirname(self.dirName)}/template/html/index.html", "r", encoding="UTF-8") as index:
            self.template = index.read()
            
        self.lang                   = lang
        self.log                    = pycgitb.enable()
    
    def page_index(self, title = "Raspberry Pi 4B WebUI"): 
        return { 
            "title": f"{title}", 
            "head" : f"""
<meta name="viewport" content="width=device-width, initial-scale=1">
<link href="/template/css/bootstrap.min.css" rel="stylesheet">
<link href="/template/css/index.css" rel="stylesheet">
<link href="/template/css/welcome.css" rel="stylesheet">
<link href="/template/css/carousel.css" rel="stylesheet">
<link href="/template/css/blog.css" rel="stylesheet">
<link rel="icon" href="/img/PEN.ico">
<link href="/template/css/loading.css" rel="stylesheet">
<div class="loading-container" id="loadingScreen">
    <div class="loading"></div>
</div>
<script src="/view/js/loading.js"></script>
""",
            "html": """
<header data-bs-theme="dark">
    <nav class="navbar navbar-expand-md navbar-dark fixed-top bg-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="https://bx293apen.github.io/">
                <img src = "/img/pen.svg" height= "40px" width="40px">
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarCollapse" aria-controls="navbarCollapse" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarCollapse">
                <ul class="navbar-nav me-auto mb-2 mb-md-0">
                    <li class="nav-item">
                        <a class="nav-link" id="home" aria-current="page" href="#">
                            Top
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" id="tipsIndex" aria-current="page" href="/cgi-bin/main.py">
                            Home
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" id="blog" aria-current="page" href="?url=reboot">
                            Reboot
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" id="apps" aria-current="page" href="?url=shutdown">
                            Shutdown
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" id="blog" aria-current="page" href="?url=stop">
                            Stop
                        </a>
                    </li>
                </ul>
                <ul class="navbar-nav mb-2 mb-md-0">
                    <li class="nav-item">
                        <a class="nav-link" href="https://github.com/BX293APEN">
                            <img src = "https://bx293apen.github.io/img/Github-Dark.svg" height= "40px" width="40px">
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="https://discord.gg/hszD9jqpq2">
                            <img src = "https://bx293apen.github.io/img/Discord.svg" height= "40px" width="40px">
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="https://x.com/BX293A_PEN">
                            <img src = "https://bx293apen.github.io/img/X.svg" height= "40px" width="40px">
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="https://bsky.app/profile/bx293apen.bsky.social">
                            <img src = "https://bx293apen.github.io/img/BlueSky.webp" height= "40px" width="40px">
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="https://ch.dlsite.com/pommu/profile/3945756">
                            <img src = "https://bx293apen.github.io/img/pommu.svg" height= "40px" width="40px">
                        </a>
                    </li>
                </ul>
                <span class="ms-3 d-flex" role="search">
                    <form method="get" action="/cgi-bin/main.py">
                        <input
                            class="form-control me-2"
                            type="search"
                            name="url"
                            placeholder="Query" 
                            aria-label="query"
                            id="searchbox"
                        >
                    </form>
                </span>
            </div>
        </div>
    </nav>
</header>
""", 
            "css": "" ,
            "style" : "",
            "footer" : """
<script src="/view/js/bootstrap.bundle.min.js"></script>
""",
            
        }
    
    def html_body(self, body = "", side = "", title = "Raspberry Pi 4B WebUI"):
        param = self.page_index(title)
        param["html"] += f"""
<body>
    <div class="container pt-3">
        <main>
            <div class="row g-5">
                <div class="col-md-8">
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