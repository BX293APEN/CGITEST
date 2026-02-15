from httpcgi import CGIHTTP

if __name__ == "__main__":
    CGIHTTP("0.0.0.0", 8000).serve_forever()