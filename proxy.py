from flask import Flask, request, Response, redirect
import requests
import os
from urllib.parse import urlparse, urljoin

app = Flask(__name__)

BLOCKED_HOSTS = {"localhost", "127.0.0.1"}

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def proxy(path):
    target_url = request.args.get("url")

    if not target_url:
        return """
        <h2>Simple Proxy</h2>
        <form>
        <input name="url" style="width:400px">
        <button type="submit">Go</button>
        </form>
        """

    if not target_url.startswith(("http://", "https://")):
        target_url = "http://" + target_url

    parsed = urlparse(target_url)
    if parsed.hostname in BLOCKED_HOSTS:
        return "Blocked URL", 403

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": request.headers.get("Accept", "*/*"),
        "Accept-Language": request.headers.get("Accept-Language", "en-US,en;q=0.9"),
        "Accept-Encoding": "identity"
    }

    try:
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data() if request.method in ["POST", "PUT", "PATCH"] else None,
            allow_redirects=False,
            timeout=10
        )

        if 300 <= resp.status_code < 400:
            location = resp.headers.get("Location")
            if location:
                return redirect(f"/?url={urljoin(target_url, location)}")

        excluded_headers = {
            "content-encoding",
            "content-length",
            "transfer-encoding",
            "connection",
            "set-cookie"
        }

        response_headers = [
            (k, v) for k, v in resp.headers.items()
            if k.lower() not in excluded_headers
        ]

        content_type = resp.headers.get("Content-Type", "")

        if "text/html" in content_type:
            content = resp.content

            if b"<head>" in content:
                base_tag = f'<base href="{target_url}">'.encode()
                content = content.replace(b"<head>", b"<head>" + base_tag, 1)

            return Response(content, status=resp.status_code, headers=response_headers)

        return Response(resp.content, status=resp.status_code, headers=response_headers)

    except requests.RequestException:
        return "Error fetching site", 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port)
