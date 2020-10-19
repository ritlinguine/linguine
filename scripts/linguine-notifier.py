import math
import smtplib
import time
from datetime import datetime as DT
from datetime import timezone as TZ
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import pymongo
from bson.objectid import ObjectId
from bson.timestamp import Timestamp as TS


def get_to_addresses():
    """Loads destination addresses from text file.

    The current email file path is hard-coded. If the file is not present, this script will crash.

    Returns:
        List of email addresses.
    """
    email_file = Path("/", "home", "linguini", "emails.txt")
    with email_file.open() as file:
        emails = file.read().splitlines()
    return emails

FROM_ADDRESS = "linguine@nlp.rit.edu"
TO_ADDRESSES = get_to_addresses()
SUBJECT = "[Linguine] Long-Running Analyses"
TEMPLATE = ("| {a_id:24} | {a_type:24} | {u_name:24} | {u_id:7} | {time:11} |"
            " {db:4} |\n")
TYPE_MAP = {
    'nlp-ner': 'Named-Entity Recognition', 'nlp-pos': 'Parse Tree w/ POS',
    'nlp-coref': 'Coreference Resolution', 'nlp-sentiment': 'Sentiment',
    'nlp-relation': 'Relation Extraction', 'wordcloudop': 'Term Frequency',
    'splat-pronouns': 'Pronoun Frequency', 'splat-disfluency': 'Disfluency',
    'splat-syllables': 'Syllable Frequency', 'splat-ngrams': 'N-Gram Frequency',
    'splat-complexity': 'Complexity', 'splat-pos': 'POS Frequency',
    'char-ngrams': 'Character N-gram Frequency',
    'length-stats': 'Word and Sentence Length',
    'topic-model-10': 'Topic Modeling (10 Topics)',
    'topic-model-30': 'Topic Modeling (30 Topics)',
    'word-vector': 'Word Vectors',
    'unsup-morph': 'Morphology Induction',
    'bigram-array': 'Bigram Array',
}


def generate_email_message(analyses):
    """
    Given a list of dictionaries, where each dictionary represents an analysis,
    create a MIMEMultipart object (an email) and return it.
    """
    curr = DT.now(TZ.utc).astimezone()
    curr_time = curr.time().strftime("%H:%M:%S")
    curr_date = curr.date().strftime("%Y-%m-%d")
    pre = (
        "As of {:s} on {:s}, Linguine has {:d} analyses that have been running"
        " for more than 15 minutes:\n\n").format(
        str(curr_time), str(curr_date), len(analyses))

    post = "Note: This is an auto-generated email. Please do not reply."

    message = list()
    message.append(
        TEMPLATE.format(
            a_id='Analysis ID', a_type='Analysis Type', u_name='User Name',
            u_id='User ID', time='Time (mins)', db='DB'))
    message.append(
        "+--------------------------+--------------------------+--------------"
        "------------+---------+-------------+------+\n")
    for a in analyses:
        message.append(
            TEMPLATE.format(
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
        "</html>"
    )

    msg.attach(MIMEText(body, 'html'))

    return msg


def to_time(mongo_timestamp):
    """ Convert mongo NumberLong UNIX timestamp to something sane. """
    return TS(int(mongo_timestamp / 1000), inc=0).as_datetime()


def get_elapsed(time_str):
    """ Return the number of minutes elapsed between time_str and now. """
    return math.floor((DT.now(TZ.utc).astimezone() - time_str).total_seconds() / 60)


def get_user(user_hash, db):
    """
    Given a mongo user hash, return a dict containing the user's name and uid.
    """
    user = db.users.find_one({"_id": ObjectId(user_hash)})
    if user is None:
        return {'uid': None, 'name': None}
    else:
        return {'uid': user['dce'], 'name': user['name']}


def get_failing_analyses(client):
    """
    Given a database connection, iterate over all of the 'analyses' objects.
    For each analysis that has existed for more than 15 minutes, has no results,
    and has not completed -- create a dictionary representation and append it to
    a list. Return said list.
    """
    failing_analyses = list()

    db_names = {
        'linguine-development': 'dev',
        'linguine-production': 'prod',
    }

    for db_name, db_friendly_name in db_names.items():
        db = client[db_name]
        analyses = db.analyses.find()
        for analysis in analyses:
            ts = to_time(analysis['time_created'])
            status = analysis['complete']
            elapsed = get_elapsed(ts)
            result = analysis['result']
            if elapsed > 15 and not status and result == "":
                user = get_user(analysis['user_id'], db)
                failing_analyses.append(
                    {'id': str(analysis['_id']), 'created': str(ts),
                     'name': str(analysis['analysis_name']), 'db': db_friendly_name,
                     'user_uid': user['uid'], 'user_name': user['name'],
                     'elapsed': elapsed, 'type': str(analysis['analysis']),
                     'corpora_ids': str(analysis['corpora_ids']),
                     'complete': status, 'result': result})

    return failing_analyses


if __name__ == "__main__":
    already_notified = list()
    loop_count = 0
    while True:
        for _ in range(12):
            client = pymongo.MongoClient()
            analyses = get_failing_analyses(client)
            to_notify = list()
            dt = str(DT.now(TZ.utc).astimezone())
            print("{:s} | {:d} Failing Analyses:".format(dt, len(analyses)))
            for a in analyses:
                print("[{:d}] ({:s}) | [{:s}] ({:s})".format(
                    a['elapsed'], a['user_uid'], TYPE_MAP[a['type']], a['id']))
                if a['id'] not in already_notified:
                    already_notified.append(a['id'])
                    to_notify.append(a)

            if len(to_notify) > 0:
                # Start an SMTP server.
                server = smtplib.SMTP("localhost")

                message = generate_email_message(analyses)
                server.sendmail(FROM_ADDRESS, TO_ADDRESSES, message.as_string())
                print("Email sent at: " + str(DT.now(TZ.utc).astimezone()))
                server.quit()
            else:
                print("...")
            client.close()
            time.sleep(300)

        already_notified = list()
