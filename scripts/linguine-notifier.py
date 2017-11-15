#!/usr/bin/env python3

import pymongo
import pprint
import json
import email
import smtplib
import unicodedata
import time
import math

from bson.objectid import ObjectId
from bson.timestamp import Timestamp as TS
from datetime import datetime as DT
from datetime import timezone as TZ
from email.message import EmailMessage as EMAIL
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

FROM_ADDRESS = "linguine@nlp.rit.edu"
TO_ADDRESSES = "bsm9339@rit.edu"
SUBJECT = "[Linguine] Long-Running Analyses"
TEMPLATE = "| {a_id:24} | {a_type:24} | {u_name:24} | {u_id:7} | {time:11} | {db:4} |\n"
TYPE_MAP = {'nlp-ner': 'Named-Entity Recognition',
            'nlp-coref': 'Coreference Resolution',
            'nlp-relation': 'Relation Extraction', 
            'nlp-sentiment': 'Sentiment',
            'nlp-pos': 'Parse Tree w/ POS',
            'splat-pronouns': 'Pronoun Frequency',
            'splat-disfluency': 'Disfluency',
            'splat-syllables': 'Syllable Frequency',
            'splat-ngrams': 'N-Gram Frequency',
            'splat-complexity': 'Complexity',
            'splat-pos': 'POS Frequency',
            'wordcloudop': 'Term Frequency'}

# Analysis Keys:
# _id, user_id, analysis, eta, analysis_name, time_created, result, complete,
# cleanup_ids, tokenizer, corpora_ids

def generate_email_message(failing_analyses):
    global TEMPLATE, TYPE_MAP, TO_ADDRESSES, FROM_ADDRESS, SUBJECT
    curr = DT.now(TZ.utc).astimezone()
    curr_time = curr.time().strftime("%H:%M:%S")
    curr_date = curr.date().strftime("%Y-%m-%d")
    pre = ("As of " + str(curr_time) + " on " + str(curr_date) +
           ", Linguine has " + str(len(failing_analyses)) +
           " analyses that have been running for more than 15 minutes:\n\n")

    post = "\nNote: This is an auto-generated email. Please do not reply."

    message = list()
    message.append(TEMPLATE.format(
        a_id='Analysis ID', a_type='Analysis Type', u_name='User Name',
        u_id='User ID', time='Time (mins)', db='DB'))
    message.append("+--------------------------+--------------------------"
                   "+--------------------------+---------+-------------"
                   "+------+\n")
    for a in failing_analyses:
        message.append(TEMPLATE.format(
            a_id=a['id'], a_type=TYPE_MAP[a['type']], u_name=a['user_name'],
            u_id=a['user_uid'], time=a['elapsed'], db=a['db']))

    msg = MIMEMultipart()
    msg['Subject'] = SUBJECT
    msg['From'] = FROM_ADDRESS
    msg['To'] = TO_ADDRESSES
    body = (
        "<html>"
          "<head>"
            "<style>"
              "div { font-family: monospace; white-space: pre; }"
            "</style>"
          "</head>"
          "<body>"
            "<div>"
              "<b>" + pre.replace("\n", "<br>") + "<br>"
            "</div>"
            "<div style='font-family: monospace'>" +
              "".join(message).replace("\n", "<br>") +
            "</div>"
            "<div>" +
              post.replace("\n", "<br>") +
            "</div>"
          "</body>"
        "</html>")

    msg.attach(MIMEText(body, 'html'))

    return msg

def to_time(mongo_timestamp):
    return TS(int(mongo_timestamp/1000), inc=0).as_datetime()

def get_elapsed(time_str):
    return math.floor((DT.now(TZ.utc).astimezone() - time_str).total_seconds() / 60)

def get_user(user_hash, db):
    user = db.users.find_one({"_id":ObjectId(user_hash)})
    if user is None:
        return {'uid': None, 'name': None}
    else:
        return {'uid': user['dce'], 'name': user['name']}

def get_failing_analyses(client):
    failing_analyses = list()

    db_dev = client['linguine-development']
    analyses = db_dev.analyses.find()
    for analysis in analyses:
        ts = to_time(analysis['time_created'])
        status = analysis['complete']
        elapsed = get_elapsed(ts)
        if elapsed > 15 and status == False:
            user = get_user(analysis['user_id'], db_dev)
            failing_analyses.append(
                {'id': str(analysis['_id']), 'created': str(ts),
                 'name': str(analysis['analysis_name']), 'db': 'dev',
                 'user_uid': user['uid'], 'user_name': user['name'],
                 'elapsed': elapsed, 'type': str(analysis['analysis'])})

    db_prod = client['linguine-production']
    analyses = db_prod.analyses.find()
    for analysis in analyses:
        ts = to_time(analysis['time_created'])
        status = analysis['complete']
        elapsed = get_elapsed(ts)
        if elapsed > 15 and status == False:
            user = get_user(analysis['user_id'], db_prod)
            failing_analyses.append(
                {'id': str(analysis['_id']), 'created': str(ts),
                 'name': str(analysis['analysis_name']), 'db': 'prod',
                 'user_uid': user['uid'], 'user_name': user['name'],
                 'elapsed': elapsed, 'type': str(analysis['type'])})

    return failing_analyses

if __name__ == "__main__":
    # Connect to MongoDB.
    client = pymongo.MongoClient()

    # Start an SMTP server.
    email_server = smtplib.SMTP("localhost")
    email_server.set_debuglevel(1)

    already_notified = list()
    while(True):
        failing_analyses = get_failing_analyses(client)
        to_notify = list()
        for a in failing_analyses:
            if a['id'] not in already_notified:
                already_notified.append(a['id'])
                to_notify.append(a)

        if len(to_notify) > 0:
            email_message = generate_email_message(failing_analyses)
            print(email_message)
            email_server.sendmail(FROM_ADDRESS, TO_ADDRESSES, email_message.as_string())
        else:
            print("...")

    email_server.quit()

