#!/usr/bin/python2
#coding=utf-8

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
	roomNumber = getRoomNumber()
	while(True):
		currentState = ""
		try:
			currentState = fetchCurrentState(roomNumber)
			html = createHtml(currentState['result']['body']['objekt']['raum'])
			writeToFile(html, "serve/{}.html".format(roomNumber))
		except:
			print(time.strftime("%H:%M") + " Exception:---------------------")
			traceback.print_exc(file=sys.stdout)
			print(currentState)
			print("-------------------------------------")
			sys.stdout.flush()
		time.sleep(60)

def getRoomNumber():
	parser = argparse.ArgumentParser()
	parser.add_argument("roomNumber", nargs='?', default=5015)
	options = parser.parse_args()
	return options.roomNumber

def fetchCurrentState(roomNumber):
	# adapted from github.com/xchrdw. Thanks to him for reverse-engineering the api!
	url = "http://ewnt.schneidereit-trac.com/api"

	authRequest = { "request": { "head": { "credentials": { "user": "api", "pass": "***REMOVED***" }, "requesttype": "authentication" } } }
	authResult = requests.post(url, json=authRequest, timeout=60)
	token = authResult.json()["result"]["head"]["credentials"]["token"]

	time.sleep(1) # prevents "ungültiges token" error

	contentRequest = { "request": { "head": { "credentials": { "token": token },
						"requesttype": "getRaum",  "api": "0.0.1"  },  "body": {  "parameter": {  "raumnr": str(roomNumber) } } } }
	contentResult = requests.post(url, json=contentRequest, timeout=60)
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
	machineSummary = ""
	machineSummary += "Waschmaschine {}".format(machine['mnr'])
	machineSummary += "\nID: {}".format(machine['id'])
	machineSummary += "\nStatus: {}".format(statusText(machine['status']))
	machineSummary += u"\nRestzeit: {} min".format(machine['restzeit'])
	machineSummary += "\n" + failureText(machine['fehler'])
	machineSummary += u"\nLetztes Signal: {} Uhr".format(machine['zeitstempel']['date'][11:-7])
	machineSummary += "\nWaschgang: {}".format(machine['waschgang'])
	machineSummary += "\nPosition: ({},{},{})".format(machine['positionx'], machine['positiony'], machine['positionz'])
	machineSummary += u"\nTür {}".format(doorText(machine['tuer'], machine['locked']))
	machineSummary += "\nProgramm: {}".format(machine['programm'])
	machineSummary += "\nSolltemperatur: {}".format(machine['solltemperatur'])
	machineSummary += "\nIsttemperatur: {}".format(machine['isttemperatur'])
	return machineSummary

def failureText(failureInt):
	failureTexts = ['Kein Fehler', u'Türfehler', 'Abflussfehler', 'Zulauffehler',
	                'Aufheizfehler', 'Temperatursensorfehler', 'Motorfehler', 
	                'Balancefehler', u'Überlauffehler']
	return failureTexts[failureInt]

def statusText(statusInt):
	if statusInt == -1:
		return "Keine Daten"
	if statusInt == 0:
		return "Aus"
	if statusInt == 1:
		return "An"

def doorText(isOpen, isLocked):
	if isLocked:
		return 'verriegelt'
	if isOpen:
		return 'auf'
	return 'zu'

def writeToFile(text, filename):
	with open(filename, 'wb') as f:
		f.write(text.encode('utf-8'))

if __name__ == "__main__":
	main()
