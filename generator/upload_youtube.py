"""Upload ke YouTube via Data API v3 (opsional).

Env: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN, YT_PRIVACY (private|unlisted|public)
"""
import json
import os
import sys

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def main(out="out"):
    meta = json.load(open(os.path.join(out, "metadata.json"), encoding="utf-8"))
    creds = Credentials(
        None, refresh_token=os.environ["YT_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"])
    yt = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {k: meta[k] for k in ("title", "description", "tags", "categoryId")},
        "status": {"privacyStatus": os.environ.get("YT_PRIVACY", "private"),
                   "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(os.path.join(out, "satisfying-relaxation.mp4"),
                            mimetype="video/mp4", chunksize=16 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"upload {status.progress():.0%}", flush=True)
    vid = resp["id"]
    print(f"https://youtu.be/{vid}")
    try:
        yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(os.path.join(out, "thumbnail.jpg"))).execute()
    except Exception as e:  # channel belum terverifikasi dll.
        print("thumbnail dilewati:", e)


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
