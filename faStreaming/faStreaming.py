#! /usr/bin/python3
# Author: Emilio Figueras
# Usage:
#	 ./faStreaming.py -h
# for usage info and options
'''
EN: Gets the streaming platforms on which movies from an entered FilmAffinity list are available.
'''
import argparse
import csv
import sys
import time
import platform
import locale
import json

from termcolor import colored
from prettytable import PrettyTable
import requests
import bs4



def set_locale(lang):
	"""Attempts to set locale."""

	if platform.system() in {"Linux", "Darwin"}:
		loc = "es_ES.utf8" if lang == "es" else "en_US.utf8"
	elif platform.system() == "Windows":
		loc = "es-ES" if lang == "es" else "en-US"
	else:
		raise locale.Error()

	locale.setlocale(locale.LC_ALL, loc)
def normalize(s):
	"""Remove the accents."""
	replacements = (
		("á", "a"),
		("é", "e"),
		("í", "i"),
		("ó", "o"),
		("ú", "u"),
		)
	for a, b in replacements:
		s = s.replace(a, b).replace(a.upper(), b.upper())
	return s

def get_data(link):
	"""Get all titles films of the list"""

	if(("user_id" not in link) or ("list_id" not in link) or ("userlist" not in link)):
		print(colored("Error: El enlace debe contener los argumentos user_id y list_id y la ruta userlist.php", "red"))
		sys.exit(1)

	link = link.split("&", 2)[0] + "&" + link.split("&", 2)[1]
	FA = link + "&page={n}"
	new_data = []
	eof = False
	n = 1

	while not eof:
		request = requests.get(FA.format(n=n))
		request.encoding = "utf-8"

		page = bs4.BeautifulSoup(request.text, "lxml")
		tags = page.find_all(class_ = "mc-title")
		for tag in tags:
			film = {
				"title": tag.a["title"],
				"jw_title": "",
				"stream": "",
				"rent": "",
				"buy": ""
			}
			new_data.append(film)

		eof = request.status_code != 200
		if not eof:
			print(colored("Página {n}...".format(n=n), "blue", attrs=['bold']), end = "\r")
		else:
			print(colored("Página {n}. Se han obtenido todos los títulos".format(n=n-1), "green", attrs=['bold']))
		n += 1
	return new_data

def convert_data(data_in):
	"""Convert all titles to justwatch nomenclature"""
	i = 0
	for film in data_in:
		new_title = film["title"]
		new_title = new_title.lower()
		new_title = new_title.split("(")[0]
		new_title = new_title.replace(":", "")
		new_title = new_title.strip()
		new_title = new_title.replace(" ", "-")
		new_title = new_title.replace("&", "y")
		new_title = new_title.replace(",", "")
		new_title = normalize(new_title)

		new_title = new_title.replace("-", "+")

		film["jw_title"] = new_title
		data_in[i] = film
		i+=1

	return data_in

def justwatch(data_in):
	"""Get info from each film"""
	final_data = []
	#url_base = "https://apis.justwatch.com/content/urls?include_children=true&path=%2Fes%2Fpelicula%2F{title}"
	url_base = "https://apis.justwatch.com/content/titles/es_ES/popular?body=%7B%22page_size%22:5,%22page%22:1,%22query%22:%22{title}%22,%22content_types%22:[%22show%22,%22movie%22]%7D"
	url_film_base = "https://apis.justwatch.com/content/titles/movie/{id}/locale/es_ES?language=es"
	#url_base = "https://www.justwatch.com/es/pelicula/{title}"
	for film in data_in:
		url = url_base.format(title=film["jw_title"])
		request = requests.get(url, headers = {'User-agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:68.0) Gecko/20100101 Firefox/68.0'})
		request.encoding = "utf-8"
		words = film["jw_title"].split("+")
		film_found_title = True
		film_found_path = True
		prev_page = json.loads(request.text)
		if prev_page["items"]:
			for word in words:
				if word not in normalize(prev_page["items"][0]["title"]).lower():
					film_found_title = False
				if word not in normalize(prev_page["items"][0]["full_path"]).lower():
					film_found_path = False
		else:
			film_found_title = False
			film_found_path = False
		film_found = bool(film_found_title or film_found_path)

		if not film_found:
			pass #To-do
		else:
			id_film = prev_page["items"][0]["id"]
			url = url_film_base.format(id=id_film)
			#print(url)
			request = requests.get(url, headers = {'User-agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:68.0) Gecko/20100101 Firefox/68.0'})
			request.encoding = "utf-8"
			film_content = json.loads(request.text)

			#Puntuacion IMDB
			imdb = 0
			tmdb = 0
			popularity = 0.0
			for score in film_content["scoring"]:
				if "imdb:score" in score["provider_type"]:
					imdb = score["value"]
				if "tmdb:popularity" in score["provider_type"]:
					popularity = score["value"]
				if "tmdb:score" in score["provider_type"]:
					tmdb = score["value"]

			#Edad
			try:
				age_certification = film_content["age_certification"]
			except KeyError:
				age_certification = 0

			#Streamings
			filmin = False
			movistar = False
			hbo = False
			netflix = False
			amazon = False
			disney = False
			flixole = False
			atres = False
			try:
				for offer in film_content["offers"]:
					#Solo miramos las plataformas de streamings
					if "flatrate" in offer["monetization_type"]:
						if "filmin" in offer["urls"]["standard_web"]:
							filmin = True
						if "primevideo" in offer["urls"]["standard_web"]:
							amazon = True
						if "netflix" in offer["urls"]["standard_web"]:
							netflix = True
						if "hboespana" in offer["urls"]["standard_web"]:
							hbo = True
						if "movistarplus" in offer["urls"]["standard_web"]:
							movistar = True
						if "disneyplus" in offer["urls"]["standard_web"]:
							disney = True
						if "flixole" in offer["urls"]["standard_web"]:
							flixole = True
						if "atresplayer" in offer["urls"]["standard_web"]:
							atres = True
			except KeyError:
				continue


			streamings = " | "
			if filmin:
				streamings += "Filmin | "
			if amazon:
				streamings += "Amazon | "
			if netflix:
				streamings += "Netflix | "
			if hbo:
				streamings += "HBO | "
			if movistar:
				streamings += "Movistar | "
			if disney:
				streamings += "DisneyPlus | "
			if flixole:
				streamings += "FlixOLE | "
			if atres:
				streamings += "AtresPlayer | "
			streamings = streamings.strip()

			film_st = {
				"Title": film["title"],
				"Year": film_content["original_release_year"],
				"Duration": film_content["runtime"],
				"Age": age_certification,
				"imdb": imdb,
				"tmdb": tmdb,
				"popularity": popularity,
				"streamings": streamings
			}
			final_data.append(film_st)
	return final_data

def show_info(data_in):
	"""Displays the information in the terminal"""
	x = PrettyTable()

	x.field_names = ["Title", "Streamings", "Duration", "Year", "IMDB", "TMDB", "Age", "Popularity"]
	print(colored("Se muestran las películas disponibles en alguna plataforma según JustWatch: ", "green", attrs=['bold']))

	for row in data_in:
		if row["streamings"] != "|":
			x.add_row([row["Title"], row["streamings"], row["Duration"], row["Year"], row["imdb"], row["tmdb"], row["Age"], row["popularity"]])
	print(colored(x, "cyan"))


def save_to_csv(data_in, filename):
	"""Save list of films in a csv file"""
	with open(filename, 'w', newline = '') as csvfile:
		writer = csv.writer(csvfile)
		writer.writerow(list(data_in[0]))

		for film in data_in:
			writer.writerow(list(film.values()))
	print(colored("Archivo {} creado con la información de la lista de FA".format(filename), "green", attrs=['bold']))

if __name__ == "__main__":
	parser = argparse.ArgumentParser(
		description =
		"Shows available streaming platforms for each movies in a Filmaffinity list")
	parser.add_argument("url", help = "Link to FilmAffinity List")
	parser.add_argument(
		"--csv", nargs = 1, help = "Name of export FILE", metavar = "FILE")
	parser.add_argument(
		"--lang",
		nargs = 1,
		help = "Language for exporting",
		metavar = "LANG",
		default = ["es"],
		choices = {"es"})

	args = parser.parse_args()
	export_file = args.csv[0] if args.csv else "filmAffinity_streaming_list_{time}.csv".format(
		time=int(time.time()))

	try:
		set_locale(args.lang[0])
	except locale.Error:
		print(colored(
			"Could not set locale for \'{lang}\' and UTF-8 encoding.".format(
				lang = args.lang[0]), "red"))
		manual_locale = input("locale (empty for default): ").strip()
		if manual_locale:
			try:
				locale.setlocale(locale.LC_ALL, manual_locale)
			except locale.Error as e:
				print(colored("Error: {}".format(e), "red"))
				sys.exit(1)

	try:
		data = get_data(args.url) #Se obtienen todos los titulos de la lista
		data = convert_data(data) #Se obtiene el titulo listo para justwatch
		data = justwatch(data)



	except ValueError as v:
		print(colored("Error: {}".format(v), "red"))
		sys.exit(1)
	show_info(data)
	save_to_csv(data, export_file)
	