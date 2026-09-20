import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.conf import settings
settings.ALLOWED_HOSTS = ["*"]
from django.test import Client

pk = "92ba50cc-7340-4eb9-b449-7a4e17bab07e"
c = Client()
assert c.login(email="admin@projectscheduler.local", password="admin12345"), "login failed"
urls = [
    f"/projects/{pk}/", f"/projects/{pk}/gantt/", f"/projects/{pk}/board/",
    f"/projects/{pk}/calendar/", f"/projects/{pk}/dashboard/", f"/projects/{pk}/list/",
]
for url in urls:
    r = c.get(url)
    body = r.content.decode("utf-8", "replace")
    print(url, r.status_code, "PS_PROJECT" in body, "PS_BOARD" in body, "PS_CALENDAR" in body, "PS_DASHBOARD" in body)
import re
r = c.get(f"/projects/{pk}/dashboard/")
print("dashboard values:", re.findall(r'PS_DASHBOARD = ({.*?})</script>', r.content.decode("utf8", "replace"), re.S)[0][:300])