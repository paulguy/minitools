#!/usr/bin/env python3

import sys
import re
import time
from datetime import datetime
from dataclasses import dataclass

@dataclass
class AddonEntry:
    subscribed_ts : int
    unsubscribed_ts : int

timestamp_re = re.compile("^\\[([^\\]]+)\\] ")
appid_re = re.compile("^\\[AppID ([^\\]]+)\\] ")
subscribe_re = re.compile("^Subscribed to item ([^ ]+)")
unsubscribe_re = re.compile("^Unsubscribed from item ([^ ]+)")

url = "https://steamcommunity.com/sharedfiles/filedetails/?id="

subscriptions = dict()

for filename in sys.argv[1:]:
    with open(filename, 'r') as infile:
        for line in infile.readlines():
            line = line.strip()
            if len(line) == 0:
                continue

            timestamp_match = timestamp_re.match(line)
            timestamp = datetime.strptime(timestamp_match.group(1), "%Y-%m-%d %H:%M:%S").timestamp()
            line = line[timestamp_match.end():].lstrip()
            appid_match = appid_re.match(line)
            if appid_match is None:
                continue
            appid = int(appid_match.group(1))
            line = line[appid_match.end():].lstrip()

            subscribe_match = subscribe_re.match(line)
            if subscribe_match is not None:
                subscription = int(subscribe_match.group(1))
                if appid not in subscriptions:
                    subscriptions[appid] = dict()
                if subscription not in subscriptions[appid]:
                    subscriptions[appid][subscription] = (AddonEntry(timestamp, -1))
                else:
                    if timestamp > subscriptions[appid][subscription].subscribed_ts:
                        subscriptions[appid][subscription].subscribed_ts = timestamp
                continue

            unsubscribe_match = unsubscribe_re.match(line)
            if unsubscribe_match is not None:
                unsubscription = int(unsubscribe_match.group(1))
                if appid not in subscriptions:
                    subscriptions[appid] = dict()
                if unsubscription not in subscriptions[appid]:
                    subscriptions[appid][unsubscription] = (AddonEntry(-1, timestamp))
                else:
                    if timestamp > subscriptions[appid][unsubscription].unsubscribed_ts:
                        subscriptions[appid][unsubscription].unsubscribed_ts = timestamp

#for appid in subscriptions.keys():
#    subscriptions[appid] = sorted(subscriptions[appid], key=lambda x: x.subscribed_ts)

print("All time subscribed")
for appid in subscriptions.keys():
    print(f"AppID {appid}")
    for addon_id in subscriptions[appid]:
        item = subscriptions[appid][addon_id]
        if item.subscribed_ts < 0:
            print(f"{datetime.fromtimestamp(item.unsubscribed_ts).isoformat()}* {url}{addon_id}")
        else:
            print(f"{datetime.fromtimestamp(item.subscribed_ts).isoformat()} {url}{addon_id}")

print("All time unsubscribed")
for appid in subscriptions.keys():
    print(f"AppID {appid}")
    for addon_id in subscriptions[appid]:
        item = subscriptions[appid][addon_id]
        if item.unsubscribed_ts > item.subscribed_ts:
            print(f"{datetime.fromtimestamp(item.unsubscribed_ts).isoformat()} {url}{addon_id}")

print("Currently subscribed to")
for appid in subscriptions.keys():
    for addon_id in subscriptions[appid]:
        item = subscriptions[appid][addon_id]
        if item.unsubscribed_ts < item.subscribed_ts:
            print(f"{datetime.fromtimestamp(item.subscribed_ts).isoformat()} {url}{addon_id}")
