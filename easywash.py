#!/usr/bin/python2
# coding=utf-8

import requests
import time
import json
import os
import sys
import traceback
import dominate
import argparse
from dominate.tags import *


def main():
	roomNumber, verbose = getRoomNumber()
	if verbose:
		print "fetching room: {}".format(roomNumber)
	while(True):
		currentState = ""
		try:
			currentState = fetchCurrentState(roomNumber)
			writeToLog(currentState, "room-{}.log".format(roomNumber))
			writeToFile(json.dumps(currentState), "serve/{}.json".format(roomNumber))
			html = createHtml(currentState['result']['body']['objekt']['raum'])
			writeToFile(html, "serve/{}.html".format(roomNumber))
			if verbose:
				print ".",
				sys.stdout.flush()
		except:
			print(time.strftime("%H:%M") + " Exception:---------------------")
			traceback.print_exc(file=sys.stdout)
			print(currentState)
			print("-------------------------------------")
			sys.stdout.flush()
		time.sleep(60)


def getRoomNumber():
	parser = argparse.ArgumentParser()
	parser.add_argument("roomNumber", nargs='?', type=int, default=5015)
	parser.add_argument("--verbose", dest="verbose", action="store_true")
	options = parser.parse_args()
	return options.roomNumber, options.verbose


def fetchCurrentState(roomNumber):
	# adapted from github.com/xchrdw. Thanks to him for reverse-engineering the api!
	url = "http://ewnt.schneidereit-trac.com/api"

	authRequest = { "request": { "head": { "credentials": { "user": "api", "pass": "***REMOVED***" }, "requesttype": "authentication" } } }
	authResult = requests.post(url, json=authRequest, timeout=200)
	token = authResult.json()["result"]["head"]["credentials"]["token"]

	time.sleep(1) # prevents "ungültiges token" error

	contentRequest = { "request": { "head": { "credentials": { "token": token },
						"requesttype": "getRaum",  "api": "0.0.1"  },  "body": {  "parameter": {  "raumnr": str(roomNumber) } } } }
	contentResult = requests.post(url, json=contentRequest, timeout=200)
	return contentResult.json()


def createHtml(room):
	title = "Waschmaschinen in " + room["bezeichnung"]

	doc = dominate.document(title=title)

	with doc.head:
		link(rel='stylesheet', href='style.css', type='text/css')
		script(src='refresh.js')
		meta(charset="UTF-8")
		meta(name="viewport", content="width=device-width, initial-scale=0.75")

	with doc:
		h1(title)
		p(time.strftime("%H:%M") + u" Uhr aktualisiert")
		for machine in room['maschinen']:
			if(machine['typ'] == "Waschmaschine"):
				machineHtml(machine)

	return doc.render()


def machineHtml(machine):
	classList = "machine"
	if machine['fehler'] > 0 or machine['status'] == -1:
		classList += ' error'
	else:
		if machine['waschgang'] > 0:
			classList += ' inUse'
		else:
			classList += ' free'
	mouseoverText = machineSummary(machine)
	with div(cls=classList, title=mouseoverText):
		if machine['waschgang'] > 0:
			span(str(machine['restzeit']) + u" min", cls="timeRemaining")


def machineSummary(machine):
	summary = ""
	summary += "Waschmaschine {}".format(machine['mnr'])
	summary += "\nID: {}".format(machine['id'])
	summary += "\nStatus: {}".format(statusText(machine['status']))
	summary += u"\nRestzeit: {} min".format(machine['restzeit'])
	summary += "\n" + failureText(machine['fehler'])
	summary += u"\nLetztes Signal: {} Uhr".format(machine['zeitstempel']['date'][11:-7])
	summary += "\nWaschgang: {}".format(machine['waschgang'])
	summary += "\nPosition: ({},{},{})".format(machine['positionx'], machine['positiony'], machine['positionz'])
	summary += u"\nTür {}".format(doorText(machine['tuer'], machine['locked']))
	summary += "\nProgramm: {}".format(machine['programm'])
	summary += "\nSolltemperatur: {}".format(machine['solltemperatur'])
	summary += "\nIsttemperatur: {}".format(machine['isttemperatur'])
	return summary


_failureTexts = ['Kein Fehler', u'Türfehler', 'Abflussfehler', 'Zulauffehler',
				'Aufheizfehler', 'Temperatursensorfehler', 'Motorfehler',
				'Balancefehler', u'Überlauffehler']


def failureText(failureInt):
	return _failureTexts[failureInt]


def statusText(statusInt):
	if statusInt == -1:
		return "Keine Daten"
	if statusInt == 0:
		return "Aus"
	if statusInt == 1:
		return "An"
	raise RuntimeError("invalid status: {}".format(statusInt))


def doorText(isOpen, isLocked):
	if isLocked:
		return 'verriegelt'
	if isOpen:
		return 'auf'
	return 'zu'


def writeToFile(text, filename):
	with open(filename, 'wb') as f:
		f.write(text.encode('utf-8'))


def writeToLog(currentState, filename):
	with open(filename, 'a') as f:
		t = time.strftime("%Y-%m-%d %H:%M:%S")
		f.write("{},{}\n".format(t,json.dumps(currentState)))


if __name__ == "__main__":
	main()
