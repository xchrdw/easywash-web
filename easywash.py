#!/usr/bin/env python3
# coding=utf-8

import requests
import time
import datetime
import json
import os
import sys
import traceback
import dominate
import argparse
from dominate.tags import *
from credentials import user, api_key

def main():
	roomNumber, verbose = parseArguments()
	if verbose:
		print('fetching room: {}'.format(roomNumber))
	while True:
		currentState = ''
		try:
			currentState = fetchCurrentState(roomNumber)
			writeToLog(currentState, 'logs/{}-room-{}.log'.format(time.strftime('%Y-%m-%d'), roomNumber))
			writeToFile(json.dumps(currentState), 'serve/{}.json'.format(roomNumber))
			html = createHtml(currentState['result']['body']['objekt']['raum'])
			writeToFile(html, 'serve/{}.html'.format(roomNumber))
			if verbose:
				print('.', end='')
				sys.stdout.flush()
		except:
			print(time.strftime('%H:%M') + ' Exception:---------------------')
			traceback.print_exc(file=sys.stdout)
			print(currentState)
			print('-------------------------------------')
			sys.stdout.flush()
		time.sleep(60)


def parseArguments():
	parser = argparse.ArgumentParser()
	parser.add_argument('roomNumber', nargs='?', type=int, default=5015)
	parser.add_argument('--verbose', dest='verbose', action='store_true')
	options = parser.parse_args()
	return options.roomNumber, options.verbose


def fetchCurrentState(roomNumber):
	# adapted from github.com/xchrdw. Thanks to him for reverse-engineering the api!
	url = 'http://ewnt.schneidereit-trac.com/api'

	authRequest = { 'request': { 'head': { 'credentials': { 'user': user, 'pass': api_key }, 'requesttype': 'authentication' } } }
	authResult = requests.post(url, json=authRequest, timeout=200)
	token = authResult.json()['result']['head']['credentials']['token']

	time.sleep(1)  # prevents 'ungültiges token' error

	contentRequest = {'request': {'head': {'credentials': {'token': token},
										   'requesttype': 'getRaum',
										   'api': '0.0.1'},
								  'body': {'parameter': {'raumnr': str(roomNumber)}}}}
	contentResult = requests.post(url, json=contentRequest, timeout=200)
	return contentResult.json()


def createHtml(room):
	title = 'Waschmaschinen in {}'.format(room['bezeichnung'])

	doc = dominate.document(title=title)

	with doc.head:
		link(rel='stylesheet', href='style.css', type='text/css')
		script(src='refresh.js')
		meta(charset='UTF-8')
		meta(name='viewport', content='width=device-width, initial-scale=0.75')

	with doc:
		h1(title)
		p('{} Uhr aktualisiert'.format(time.strftime('%H:%M')))

		washingMachines = []
		dryers = []
		for machine in room['maschinen']:
			if machine['typ'] == 'Waschmaschine':
				washingMachines.append(machine)
			else:
				dryers.append(machine)
		if washingMachines:
			for machine in washingMachines:
				machineHtml(machine)
		if dryers:
			h2('Trockner')
			for machine in dryers:
				machineHtml(machine)
		p('Diese Seite wird von Studenten als inoffizielle Alternative zur EasyWash-App betrieben und ist kein Teil des Angebots von Schneidereit GmbH. Alle Angaben ohne Gewähr.',
			cls='disclaimer')

	return doc.render()


MAX_TIMESTAMP_AGE = 60*36 #assume a machine is broken if it didn’t wash in 36 hours


def machineHtml(machine):
	classList = 'machine'
	if machine['fehler'] > 0 or machine['status'] == -1:
		classList += ' error'
	elif timestampAge(machine) > MAX_TIMESTAMP_AGE:
		classList += ' error noSignal'
	else:
		if machine['waschgang'] > 0:
			classList += ' inUse'
		else:
			classList += ' free'
	mouseoverText = machineSummary(machine)
	with div(cls=classList, title=mouseoverText):
		span(machine['mnr'], cls="machine-id")
		if machine['waschgang'] > 0:
			span('{} min'.format(remainingTime(machine)), cls='timeRemaining')


def machineSummary(machine):
	summary = ''
	summary += machineName(machine)
	summary += '\nID: {}'.format(machine['id'])
	#summary += '\nStatus: {}'.format(statusText(machine['status']))
	summary += '\nRestzeit: {} min'.format(machine['restzeit'])
	summary += '\n' + failureText(machine['fehler'])
	if timestampAge(machine) < MAX_TIMESTAMP_AGE:
		summary += '\nLetztes Signal: {} Uhr'.format(machine['zeitstempel']['date'][11:-7])
	else:
		summary += '\nLetztes Signal: {}'.format(machine['zeitstempel']['date'][:-7])
	summary += '\nWaschgang: {}'.format(machine['waschgang'])
	summary += '\nProgramm: {}'.format(programText(machine['programm']))
	summary += '\nPosition: ({},{},{})'.format(machine['positionx'], machine['positiony'], machine['positionz'])
	#summary += '\nTür {}'.format(doorText(machine['tuer'], machine['locked']))
	#summary += '\nSolltemperatur: {}'.format(machine['solltemperatur'])
	#summary += '\nIsttemperatur: {}'.format(machine['isttemperatur'])
	return summary


def machineName(machine):
	return '{} {}'.format(machine['typ'], machine['mnr'])


_failureTexts = ['Kein Fehler', 'Türfehler', 'Abflussfehler', 'Zulauffehler',
				'Aufheizfehler', 'Temperatursensorfehler', 'Motorfehler',
				'Balancefehler', 'Überlauffehler']


def failureText(failureInt):
	return _failureTexts[failureInt]


def statusText(statusInt):
	if statusInt == -1:
		return 'Keine Daten'
	if statusInt == 0:
		return 'Aus'
	if statusInt == 1:
		return 'An'
	raise RuntimeError('invalid status: {}'.format(statusInt))


def doorText(isOpen, isLocked):
	if isLocked:
		return 'verriegelt'
	if isOpen:
		return 'auf'
	return 'zu'

def remainingTime(machine):
	restzeit = machine['restzeit']
	if currentTimezoneOffset() == -120:
		restzeit -= 60
	if restzeit > 100:
		restzeit = programDuration(machine['programm']) - timestampAge(machine)
	return max(0, restzeit)

def timestampAge(machine):
	timestring = machine['zeitstempel']['date'][:-7]
	timestamp = datetime.datetime.strptime(timestring, '%Y-%m-%d %H:%M:%S')
	diff = datetime.datetime.now() - timestamp
	return round(diff.total_seconds() / 60)

_programDurations = {5: 70,
					 6: 60,
					 7: 55,
					10: 26,
					11: 30}

def programDuration(program):
	if program in _programDurations.keys():
		return _programDurations[program]
	return 100

def currentTimezoneOffset():
	import time
	import calendar
	offsetSeconds = calendar.timegm(time.gmtime()) - calendar.timegm(time.localtime())
	return round(offsetSeconds/60)

_programTexts = {5: 'Koch 90°',
				 6: 'Normal 60°',
				 7: 'Normal 40°',
				10: 'Fein 30°',
				11: 'Wolle 30°'}

def programText(programInt):
	if programInt in _programTexts.keys():
		return _programTexts[programInt]
	return str(programInt)

def writeToFile(text, filename):
	with open(filename, 'wb') as f:
		f.write(text.encode('utf-8'))


def writeToLog(currentState, filename):
	with open(filename, 'a') as f:
		t = time.strftime('%Y-%m-%d %H:%M:%S')
		f.write('{},{}\n'.format(t,json.dumps(currentState)))


if __name__ == '__main__':
	main()
