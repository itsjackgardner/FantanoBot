import praw
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from re import search
import time
import os

sheet_url = 'https://docs.google.com/spreadsheets/d/1GbGyWVtePH8RZCZd7N3RPDh8m-K6hgO6AyKsAHZpbeQ/edit?usp=sharing'

print('INITIALISING ...')
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_p12_keyfile('fantanobot@fantanobot.iam.gserviceaccount.com', 'securecret.p12', os.environ['CERT_PASS'])
gc = gspread.authorize(credentials)
sheet = gc.open_by_url(sheet_url).worksheet('All Reviews')

footer = "\n\n---\n^(I am a bot and this action was performed automatically)  \n^(Send me a PM to provide feedback)"

def retrieve_album(album_name):
    print('retrieving album', album_name, '...')
    try:
        cell = sheet.find(album_name)
        assert(cell.col == 2)
        values = sheet.row_values(cell.row)
        print('success')
        return 'Artist: *{0}*  \nAlbum: {1}  \nScore: **{2}**'.format(values[0], values[1], values[2])
    except:
        print('fail')
        return None

def retrieve_artist(artist_name):
    print('retrieving artist', artist_name, '...')
    try:
        albums = []
        for cell in sheet.findall(artist_name):
            if cell.col != 1:
                continue
            values = sheet.row_values(cell.row)
            albums.append('{0} - **{1}**'.format(values[1], values[2]))
        assert(len(albums) > 0)
        print('success')
        return 'Album scores for *{0}*:\n\n{1}'.format(artist_name, '  \n'.join(albums))
    except:
        print('fail')
        return None

def login():
    print('logging in ...')
    client = praw.Reddit(username=os.environ['REDDIT_USER'],
                         password=os.environ['REDDIT_PASS'],
                         user_agent='FantanoBot responder')
    return client

def run(client, replied):
    print('running ...')

    for comment in client.subreddit('test').comments(limit=None):
        if comment.id in replied or comment.author == client.user.me():
            continue

        find = search('!fantanobot (.*)', comment.body)
        if find is not None:
            print('found comment: ', find.group(1))
            term = find.group(1)
            response = retrieve_album(term)
            if response is None:
                response = retrieve_artist(term)

            if response is not None:
                print(response)
                try:
                    comment.reply(response + footer)
                    replied.append(comment.id)
                    with open('replied.txt', 'a') as f:
                        f.write(comment.id + '\n')
                except:
                    # ratelimit causes a failure
                    print('comment failed')

    print('sleeping ...')
    time.sleep(5)

def get_replied():
    with open('replied.txt', 'r') as f:
        return [i for i in f.read().split('\n') if i != '']

client = login()
replied = get_replied()
print(replied)
while True:
    run(client, replied)
    print(replied)