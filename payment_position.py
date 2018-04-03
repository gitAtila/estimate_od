'''
	Find bus position at the moment when payment happened
'''

import gzip
import csv
from datetime import datetime
import pandas as pd
from sys import argv, maxint
from collections import defaultdict

buscard_path = argv[1]
busposition_path = argv[2]
result_path = argv[3]

# create a dictionary which the key is the vehicle and the bus line
dict_line_vehicle = dict()

try:
	with open(busposition_path,'r') as csv_file:

		csv_reader = csv.reader(csv_file, delimiter=';')
		# ['ID_POSONIBUS', 'COD_LINHA', 'VEIC', 'LAT', 'LON', 'DTHR']
		csv_headings = next(csv_reader)
		for line in csv_reader:
			dict_card = dict(zip(csv_headings, line))

			busline_code = dict_card['LINHA'] #COD_LINHA
			vehicle_code = dict_card['PREFIXO'] #VEIC
			latitude = dict_card['LAT']
			longitude = dict_card['LON'] 
			bus_datetime = datetime.strptime(dict_card['DATA'] + ' ' + dict_card['HORA'], '%Y-%m-%d %H:%M:%S') #DTHR

			dict_line_vehicle.setdefault((busline_code, vehicle_code), []).append((bus_datetime, latitude, longitude))
		# print len(dict_line_vehicle)
		# stop
except IOError:
	print 'Error file:', busposition_path

# read buscard file
df_buscard = pd.read_csv(buscard_path)
payment_position_file = open(result_path, 'w')
csv_writer = csv.writer(payment_position_file)
csv_writer.writerow(('NUMEROCARTAO', 'CODVEICULO', 'CODLINHA', 'DATAUTILIZACAO', 'DTHR', 'LAT', 'LON', 'INTERVTEMPO'))

# for each boarding
count = 0
print 'quantity of boradings:', len(df_buscard)
count = len(df_buscard)
for index, current_card in df_buscard.iterrows():
	count -=1 
	# print current_card
	# stop
	#get_previous_busposition(busposition_path, current_card[1]['DATAUTILIZACAO'], current_card[1]['CODVEICULO'], current_card[1]['CODLINHA'], 6000)

	card_datetime = datetime.strptime(current_card['DATAUTILIZACAO'], '%Y-%m-%d %H:%M:%S')

	vehicle = current_card['CODVEICULO']
	bus_line = current_card['CODLINHA']
	card_code = current_card['NUMEROCARTAO']

	# verify if pair (line, vehicle) is in busposition file
	if (bus_line, vehicle) in dict_line_vehicle:
		# print bus_line, vehicle
		
		datepos_list = dict_line_vehicle[(bus_line, vehicle)]

		best_diff_time = maxint
		best_position = ""

		# find the position that best fits
		for datepos in datepos_list:
			bus_date = datepos[0]
			diff_time = abs((card_datetime - bus_date).total_seconds())
			if diff_time < best_diff_time:
				best_diff_time = diff_time
				best_position = datepos
			elif diff_time > best_diff_time:
				break

		# print card_code, vehicle, bus_line, card_datetime, best_position[0], best_position[1], best_position[2], best_diff_time
		csv_writer.writerow((card_code, vehicle, bus_line, card_datetime, best_position[0], best_position[1], best_position[2], best_diff_time))

	print count
payment_position_file.close()
	#break