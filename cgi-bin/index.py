#!/usr/bin/env python3

import pycgi, pycgitb

class WebCGI():
    def __init__(self, lang = "ja"):
        self.template               = """Content-Type: text/html

<!DOCTYPE html>
<html lang="{lang}">
    <head>
        <meta charset="UTF-8">
        <title>
            {title}
        </title>
    </head>
    <body>
        {html}
    </body>
    <footer>
        <style>
            {css}
        </style>
    </footer>
</html>
"""
        self.lang                   = lang
    
    def page_index(self): 
        return { 
            "title": "Hello", 
            "html": """
<h1>Hello World</h1>
""", 
            "css": "" 
        }
    
    def urls(self, url):
        log.handler("Hello")
        self.pages = { 
            "index": self.page_index, 
        } 

        param = self.pages.get(url, self.page_index)() 
        return self.template.format(lang=self.lang, **param)


if __name__ == "__main__": 
    form    = pycgi.FieldStorage()
    log     = pycgitb.enable()
    html    = WebCGI()

    print(html.urls(form.getvalue("url", default = "index")))