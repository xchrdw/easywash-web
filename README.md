# Easywash-Webapp

Queries `http://ewnt.schneidereit-trac.com/api` for washing machine status every 60 seconds, and on success updates `serve/<roomNumber>.html`.

## Setup 

Install dependencies: 

`pip install -r requirements.txt`

Copy credentials.py.example to credentials.py and enter a valid api key.

Tested with python 3.5.

## Usage

Run with room number (defaults to 5015):

`python easywash.py [roomnumber] [--verbose]`
