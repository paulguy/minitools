#!/usr/bin/env python3

import sys
import re

timestamp_re = re.compile("^\\[([^\\]]+)\\] ")
appid_re = re.compile("^\\[AppID ([^\\]]+)\\] ")
subscribe_re = re.compile("^Subscribed to item ([^ ]+)")
unsubscribe_re = re.compile("^Unsubscribed from item ([^ ]+)")

url = "https://steamcommunity.com/sharedfiles/filedetails/?id="

subscriptions = dict()
unsubscriptions = dict()

for filename in sys.argv[1:]:
    with open(filename, 'r') as infile:
        for line in infile.readlines():
            line = line.strip()
            if len(line) == 0:
                continue

            timestamp_match = timestamp_re.match(line)
            timestamp = timestamp_match.group(1)
            line = line[timestamp_match.end():].lstrip()
            appid_match = appid_re.match(line)
            if appid_match is None:
                continue
            appid = int(appid_match.group(1))
            line = line[appid_match.end():].lstrip()

            subscribe_match = subscribe_re.match(line)
            if subscribe_match is not None:
                if appid not in subscriptions:
                    subscriptions[appid] = set()
                subscriptions[appid].add(int(subscribe_match.group(1)))
                continue

            unsubscribe_match = unsubscribe_re.match(line)
            if unsubscribe_match is not None:
                if appid not in unsubscriptions:
                    unsubscriptions[appid] = set()
                unsubscriptions[appid].add(int(unsubscribe_match.group(1)))

subscribed = dict()
for appid in subscriptions.keys():
    if appid not in subscribed:
        subscribed[appid] = set()
for appid in unsubscriptions.keys():
    if appid not in subscribed:
        subscribed[appid] = set()
for appid in subscribed.keys():
    if appid in unsubscriptions:
        subscribed[appid] = subscriptions[appid].difference(unsubscriptions[appid])
    else:
        subscribed[appid] = subscriptions[appid]

print("All time subscribed")
for appid in subscriptions.keys():
    print(f"AppID {appid}")
    for item in subscriptions[appid]:
        print(f"{url}{item}")
print("All time unsubscribed")
for appid in unsubscriptions.keys():
    print(f"AppID {appid}")
    for item in unsubscriptions[appid]:
        print(f"{url}{item}")
print("Subscribed to")
for appid in subscribed.keys():
    if len(subscribed[appid]) == 0:
        continue
    print(f"AppID {appid}")
    for item in subscribed[appid]:
        print(f"{url}{item}")
