'''
	Chain routes into trips considering boarding time, vehicle and line of the busses
'''

from sys import argv
from datetime import datetime
import pandas as pd
import csv

payment_position_path = argv[1]
od_path = argv[2]

def read_payment_position(payment_position_path):
	#def read_bus_stop(bus_stop_path):
	dict_payment_pos = dict()

	try:
		with open(payment_position_path,'r') as csv_file:

			csv_reader = csv.reader(csv_file, delimiter = ',')

			# ['NUMEROCARTAO', 'CODVEICULO', 'CODLINHA', 'DATAUTILIZACAO', 'DTHR', 'LAT', 'LON', 'INTERVTEMPO']
			csv_headings = next(csv_reader)
			#print csv_headings

			for line in csv_reader:
				print line

				card_id = line[0]
				vehicle = line[1]
				bus_line = line[2]
				time_payment = datetime.strptime(line[3], '%Y-%m-%d %H:%M:%S')
				latitude = float(line[5].replace(',','.'))
				longitude = float(line[6].replace(',','.'))
				number_passengers = 1

				# group bus stops by line
			  	dict_payment_pos.setdefault(card_id, []).append((vehicle, bus_line, time_payment, latitude, longitude, number_passengers))

	except IOError:
				print 'Error file:', payment_position_path
	return dict_payment_pos

def group_who_boarded_together(interval_time, dict_payment_pos):

	# for each passenger
	for card_id, payment_pos in dict_payment_pos.iteritems():

		# passenger with more than one boarding may have consecutive boardings
		if len(payment_pos) > 1:

			# Get bus position until next boarding
			previous = payment_pos[0]
			list_index_consecutive_boardings = []

			# iterate over her boardings
			for index in range(1, len(payment_pos)):
				posterior = payment_pos[index]
				difftime = (posterior[2] - previous[2]).seconds

				# verify if trips can be merged considering time and vehicle of boarding
				if difftime <= interval_time and previous[1] == posterior[1]:
					# mark posterior boardings
					list_index_consecutive_boardings.append(index)

				# set previous as posterior
				previous = posterior

			# increment the number of passengers of the previous boarding for those who boarded together
			for boarding in reversed(list_index_consecutive_boardings):

				# increment number of passengers of the previous boarding
				payment_pos[boarding - 1] = (payment_pos[boarding-1][0], payment_pos[boarding-1][1], payment_pos[boarding-1][2],\
				 payment_pos[boarding-1][3], payment_pos[boarding-1][4],payment_pos[boarding-1][5] + payment_pos[boarding][-1])

			list_element_consecutive_boardings = []

			# remove posterior boardings for those who boarded together
			for boarding in list_index_consecutive_boardings:
				list_element_consecutive_boardings.append(payment_pos[boarding])
			for element in list_element_consecutive_boardings:
				payment_pos.remove(element)	

			dict_payment_pos[card_id] = payment_pos

	return dict_payment_pos

def chain_consecutive_boardings(dict_payment_pos, boarding_interval_time, integration_max_time):
	dict_chained = dict()

	# for each passenger
	for card_id, payment_pos in dict_payment_pos.iteritems():

		dict_chained.setdefault(card_id,[])

		# passenger with more than one boarding may have chained trips
		if len(payment_pos) > 1:

			# Get bus position until next boarding
			previous = payment_pos[0]
			chained = 0
			chain = []
			unchained = []

			# iterate over her boardings
			for index in range(1, len(payment_pos)):
				posterior = payment_pos[index]
				difftime = (posterior[2] - previous[2]).seconds
				#print 'difftime', difftime

				# verify if trips can be chained considering time between boardings and bus line boarding
				if difftime <= integration_max_time and previous[1] != posterior[1]:
				
					if chained == 0:

						# remove last trip from unchained ones
						if len(unchained) > 0 and previous == unchained[-1]:
							del unchained[-1]
							#print 'delete last unchained'

						chain.append(previous)
						chain.append(posterior)

					elif chained > 0:
						chain.append(posterior)

					chained += 1

				# if trip cannot be chained
				else:	

					# add to unchained ones
					if (len(chain) == 0 or chain[-1] != previous) and (len(unchained) == 0 or unchained[-1] != previous):
						unchained.append(previous)

					unchained.append(posterior)

					# save previous chain
					if len(chain) > 0:

						# save previous unchained
						list_saved = []
						for trip in unchained:
							if trip[2] < chain[0][2]:
								dict_chained[card_id].append(trip)
								list_saved.append(trip)

						# delete saved unchained
						for trip in list_saved:
							unchained.remove(trip)

						#save chained
						dict_chained[card_id].append(chain)
						chain = []
						chained = 0	

				previous = posterior


			if len(chain) > 0:
				for trip in unchained:
					if trip[2] < chain[0][2]:
						dict_chained[card_id].append(trip)

				dict_chained[card_id].append(chain)

				for trip in unchained:
					if trip[2] >= chain[0][2]:
						dict_chained[card_id].append(trip)
			else:
				for trip in unchained:
					dict_chained[card_id].append(trip)


			print dict_chained[card_id]
			#print 'unchained', unchained

		# add passengers with only one boarding
		else:
			dict_chained[card_id].append(payment_pos[0])

	return dict_chained

def frequency_route(dict_chained):
	dict_len_boarding = dict()
	for card_id, boardings in dict_chained.iteritems():
		#print card_id, len(boardings)
		dict_len_boarding.setdefault(len(boardings), []).append(card_id)

	for len_boardings, frequency in dict_len_boarding.iteritems():
		print len_boardings, len(frequency)

# estimate origin and destination considering routes chained
def get_origin_destination(dict_chained):
	df_origin_destination = pd.DataFrame(columns=['card_id', 'vehicle', 'bus_line', 'date_time', 'lat_origin', 'lon_origin',\
	 'num_passengers', 'lat_destination', 'lon_destination'])
	count_iteration =  len(dict_chained)
	for card_id, boardings in dict_chained.iteritems():
		if len(boardings) > 1:

			# get the first origin
			first_origin = boardings[0]
			if type(boardings[0]) == tuple:
				origin = boardings[0]
			else:
				origin = boardings[0][0]

			for index in range(1, len(boardings)):
				if type(boardings[index]) == tuple:
					destination = boardings[index]
				else:
					destination = boardings[index][0]

				#print destination
				od = [card_id, origin[0], origin[1], origin[2], origin[3], origin[4], origin[5], destination[3], destination[4]]
				#print od
				df_origin_destination = df_origin_destination.append(pd.DataFrame([od], columns=['card_id', 'vehicle', 'bus_line',\
				 'date_time', 'lat_origin', 'lon_origin', 'num_passengers', 'lat_destination', 'lon_destination']),ignore_index=True)

				# set the next origin as the destination
				origin = destination

			# check if passenger returns to her origin, through bus lines
			if type(first_origin) == tuple:
				if origin[1] == first_origin[1]:
					od = [card_id, origin[0], origin[1], origin[2], origin[3], origin[4], origin[5], first_origin[3], first_origin[4]]
					df_origin_destination = df_origin_destination.append(pd.DataFrame([od], columns=['card_id', 'vehicle', 'bus_line',\
				 	 'date_time', 'lat_origin', 'lon_origin', 'num_passengers', 'lat_destination', 'lon_destination']),ignore_index=True)
					#print '=t',od
					
			else: # verify every boarding in origin chaining
				for boarding in reversed(first_origin):
					if origin[1] == boarding[1]:
						od = [card_id, origin[0], origin[1], origin[2], origin[3], origin[4], origin[5], boarding[3], boarding[4]]
						df_origin_destination = df_origin_destination.append(pd.DataFrame([od], columns=['card_id', 'vehicle',\
						 'bus_line','date_time', 'lat_origin', 'lon_origin', 'num_passengers', 'lat_destination', 'lon_destination']),\
						 ignore_index=True)

		print count_iteration
		count_iteration -= 1	

	return df_origin_destination

# read payment position
dict_payment_pos = read_payment_position(payment_position_path)

# add number of people who boarded together to the sabe boarding
boarding_interval_time = 60 * 1 # one minute
dict_payment_pos = group_who_boarded_together(boarding_interval_time, dict_payment_pos)

# chain consecutive boardings
integration_max_time = (3600 * 1.5) # considering a trip has one hour and a half of duration
dict_chained = chain_consecutive_boardings(dict_payment_pos, boarding_interval_time, integration_max_time)

# print frequence
df_origin_destination = get_origin_destination(dict_chained)
df_origin_destination.to_csv(od_path, quoting=csv.QUOTE_NONNUMERIC, index=False)
frequency_route(dict_chained)
print df_origin_destination