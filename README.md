# mastodon_followers_backup
Simple script to backup accounts followed on Mastodon
=========
This is very simple script to backup followers on given Mastodon account.
Intended to use while doing backup in command line.

Requirements
---------
* Python 3
* requests
* followers must be visible publicly

Usage
---------
* python3 mastodon_backup.py -u <ACCOUNT_URL>
* example: `python3 mastodon_backup.py -u https://mastodon.online/@rozie | tee mastodon_followers_backup.txt`