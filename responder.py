import praw
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import bmemcached
from re import compile, search, IGNORECASE
import time
import os
import json

ARTIST_COL = 1
ALBUM_COL = 2
SCORE_COL = 3

SUBREDDITS = 'fantanoforever+hiphopheads'
COMMAND = compile('!fantanobot (.*)', IGNORECASE)

URL = 'https://docs.google.com/spreadsheets/d/1GbGyWVtePH8RZCZd7N3RPDh8m-K6hgO6AyKsAHZpbeQ/edit#gid=0'
ACCOUNT = 'fantanobot@fantanobot.iam.gserviceaccount.com'

print('INITIALISING ...')

# Connect to google spreadsheet
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_dict(
    json.loads(os.environ.get('CREDENTIALS')),
    scope
)
gc = gspread.authorize(credentials)
sheet = gc.open_by_url(URL).worksheet('All Reviews')

# Connect to Memcached DB (stores comment IDs)
db = bmemcached.Client(
    os.environ.get('MEMCACHEDCLOUD_SERVERS').split(','),
    os.environ.get('MEMCACHEDCLOUD_USERNAME'),
    os.environ.get('MEMCACHEDCLOUD_PASSWORD')
)

FOOTER = (
    "\n\nAll scores sourced from [here]({link}).\n\n"
    "---\n"
    "^(I am a bot and this action was performed automatically)  \n"
    "^(Send me a PM to provide feedback)"
).format(link = URL)

# Try album then artist
def retrieve(term):
    regex = compile(term, IGNORECASE)
    print('retrieving album', term, '...')
    response = retrieve_album(regex)
    if response is None:
        print('retrieving artist', term, '...')
        response = retrieve_artist(regex)
    return response

def retrieve_album(album_name):
    try:
        cell = sheet.find(album_name)
        assert(cell.col == ALBUM_COL)
        values = sheet.row_values(cell.row)
        print('success')
        return "Artist: *{artist}*  \nAlbum: {album}  \nScore: **{score}**".format(
            artist = values[ARTIST_COL - 1],
            album  = values[ALBUM_COL - 1],
            score  = values[SCORE_COL - 1]
        )
    except Exception as e:
        print('fail')
        print(e)
        return None

def retrieve_artist(artist_name):
    try:
        albums = []
        found = sheet.findall(artist_name)
        assert(len(found) > 0)

        # Artist name, always smallest because of collaborative albums
        artist = sheet.cell(found[0].row, ARTIST_COL).value

        for cell in found:
            if cell.col != ARTIST_COL:
                continue
            values = sheet.row_values(cell.row)

            temp_artist = values[ARTIST_COL - 1]
            if len(temp_artist) < len(artist):
                artist = temp_artist

            albums.append('{album} - **{score}**'.format(
                album = values[ALBUM_COL - 1],
                score = values[SCORE_COL - 1]
            ))

        assert(len(albums) > 0)
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

def login():
    print('logging in ...')
    client = praw.Reddit(
        username      = os.environ.get('REDDIT_USER'),
        password      = os.environ.get('REDDIT_PASS'),
        client_id     = os.environ.get('CLIENT_ID'),
        client_secret = os.environ.get('CLIENT_SECRET'),
        user_agent    = 'FantanoBot responder'
    )
    return client

def run(client):
    print('running ...')
    check_comments(client)
    check_messages(client)

def check_comments(client):
    print('Checking comments ...')
    for comment in client.subreddit(SUBREDDITS).comments(limit=None):

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
        db.set(str(comment.id), "True")
        print("replied")

def check_messages(client):
    print('Checking messages ...')
    for item in client.inbox.all(limit=None):
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
            item.author.message(item.body, response)
            db.set(str(item.id),, "True")
            print("replied")


client = login()
run(client)

print("COMPLETE")