import praw
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import bmemcached
import re
import time
import os
import json
import threading

ARTIST_COL = 0
ALBUM_COL  = 1
SCORE_COL  = 2

SUBREDDITS = 'fantanoforever+hiphopheads'
COMMAND = re.compile('!fantanobot (.*)', re.IGNORECASE)

URL = 'https://docs.google.com/spreadsheets/d/1GbGyWVtePH8RZCZd7N3RPDh8m-K6hgO6AyKsAHZpbeQ/edit#gid=0'
ACCOUNT = 'fantanobot@fantanobot.iam.gserviceaccount.com'

print('INITIALISING ...')

# Connect to google spreadsheet
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_dict(
    json.loads(os.environ['CREDENTIALS']),
    scope
)
gc = gspread.authorize(credentials)
sheet = gc.open_by_url(URL).worksheet('All Reviews')
data = sheet.get_all_values()

# Connect to Memcached DB (stores comment IDs)
db = bmemcached.Client(
    os.environ['MEMCACHEDCLOUD_SERVERS'].split(','),
    os.environ['MEMCACHEDCLOUD_USERNAME'],
    os.environ['MEMCACHEDCLOUD_PASSWORD']
)

FOOTER = (
    "\n\nAll scores sourced from [here]({data_link}).\n\n"
    "---\n"
    "^(I am a bot and this action was performed automatically)  \n"
    "^(Send [my creater a PM]({pm_link}) to provide feedback)"
).format(data_link = URL, pm_link = "https://www.reddit.com/message/compose/?to=NobleLordOfLaziness")

# Try album then artist
def retrieve(term):
    try:
        regex = re.compile(term, re.IGNORECASE)
    except:
        return None
    print('retrieving album', term, '...')
    response = retrieve_album(regex)
    if response is None:
        print('retrieving artist', term, '...')
        response = retrieve_artist(regex)
    return response

def retrieve_album(album_name):
    global data
    try:
        values = None
        for album in data:
            if album_name.match(album[1]):
                values = album
        assert(values is not None)
        print('success')
        return "Artist: *{artist}*  \nAlbum: {album}  \nScore: **{score}**".format(
            artist = values[ARTIST_COL],
            album  = values[ALBUM_COL],
            score  = values[SCORE_COL]
        )
    except Exception as e:
        print('fail')
        print(e)
        return None

def retrieve_artist(artist_name):
    global data
    try:
        albums = []
        artist = None
        for album in data:
            if artist_name.match(album[ARTIST_COL]):
                albums.append('{album} - **{score}**'.format(
                    album = album[ALBUM_COL],
                    score = album[SCORE_COL]
                ))

                temp_artist = album[ARTIST_COL]
                if artist is None or len(temp_artist) < len(artist):
                    artist = temp_artist

        assert(artist is not None and len(albums) > 0)
        print('success')
        return "Fantano's album scores for *{artist}*:\n\n{albums}".format(
            artist = artist,
            albums = '  \n'.join(albums)
        )
    except Exception as e:
        print('fail')
        print(e)
        return None

def ampersand_replacement(term):
    # Make replacements for ampersand usage
    if 'and' in term:
        term = term.replace('and', '(and|&)')
    elif '&' in term:
        term = term.replace('&', '(and|&)')
    return term

def check_comments(client):
    for comment in client.subreddit(SUBREDDITS).stream.comments():
        # Check if replied to
        if db.get(str(comment.id)) is not None or comment.author == client.user.me():
            continue

        # search for bot command in comment
        bot_call = COMMAND.search(comment.body)

        if bot_call is None:
            continue

        print('found comment: https://reddit.com' + comment.permalink)
        print('term:', bot_call.group(1))
        term = bot_call.group(1).strip()

        new_term = ampersand_replacement(term)
        response = retrieve(new_term)

        if response is None:
            response = "Could not find anything for *{term}*".format(term = term)
        print(response)
        comment.reply(response + FOOTER)
        db.set(str(comment.id), 'True')
        print('replied')

def check_messages(client):
    for item in client.inbox.stream():
        if db.get(str(item.id)) is not None:
            continue

        if type(item) == praw.models.Message and '!fantanobot' in item.subject:
            print("Message found: **{subject}** - {body}".format(
                subject = item.subject,
                body    = item.body
            ))
            term = ampersand_replacement(item.body)
            response = retrieve(term)
            if response is None:
                response = "Could not find anything for *{term}*".format(term = item.body)
            print(response)
            item.reply(response + FOOTER)
            db.set(str(item.id), 'True')
            print('replied')

def login():
    print('logging in ...')
    client = praw.Reddit(
        username      = os.environ['REDDIT_USER'],
        password      = os.environ['REDDIT_PASS'],
        client_id     = os.environ['CLIENT_ID'],
        client_secret = os.environ['CLIENT_SECRET'],
        user_agent    = 'FantanoBot responder'
    )
    return client

def run(client):
    print('running ...')
    comment_thread = threading.Thread(target=check_comments, args=(client,))
    message_thread = threading.Thread(target=check_messages, args=(client,))
    comment_thread.start()
    message_thread.start()


if __name__ == '__main__':
    client = login()
    run(client)
