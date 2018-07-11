# FantanoBot

This is a basic reddit bot that provides users with album scores from Anthony Fantano's youtube channel [theneedledrop](https://www.youtube.com/channel/UCt7fwAhXDy3oNFTAzF2o8Pw).

`!fantanobot [Album Name]` will provide the score for that album (e.g. `!fantanobot The Money Store`).

`!fantanobot [Artist Name]` will list the scores for that artist's albums (e.g. `!fantanobot Kanye West`).

All scores sourced from [here](https://docs.google.com/spreadsheets/d/1GbGyWVtePH8RZCZd7N3RPDh8m-K6hgO6AyKsAHZpbeQ/edit#gid=0).

## Requirements

- gspread
- oauth2client
- praw
- pyOpenSSL
- python-binary-memcached