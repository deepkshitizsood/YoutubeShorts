from googleapiclient.discovery import build
from src.upload import credentials
from src.analytics import recent_video_ids
import re
yt = build("youtube","v3",credentials=credentials())
ids=[v["video_id"] for v in recent_video_ids(max_results=25)]
r=yt.videos().list(part="contentDetails,snippet",id=",".join(ids)).execute()
def secs(d):
    m=re.match(r"PT(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?",d or "")
    return int(m.group(1) or 0)*60+float(m.group(2) or 0) if m else 0
print(f"{'video':<13} {'dur':>6}  {'SHORT?':<7} title")
for it in r.get("items",[]):
    d=secs(it["contentDetails"]["duration"])
    ok="YES" if d<=60 else "NO >60s"
    t=it["snippet"]["title"].encode("ascii","ignore").decode()[:44]
    print(f"{it['id']:<13} {d:>5.0f}s  {ok:<7} {t}")
