###################
#### LIBRARIES ####
###################

import requests
import json
import os
from time import sleep
from datetime import datetime
import argparse
import telepot

import pyarrow.parquet as pq
import numpy as np
import pandas as pd
import pyarrow as pa

from influxdb import DataFrameClient

###############
#### CONST ####
###############

API_TRANSPORTE_URL = 'https://apitransporte.buenosaires.gob.ar'
CLIENT_ID = 'fb174c1cde604a999877a85f1e69c18c'
CLIENT_SECRET = 'd26E1dAb300B45DC9c752514AEf7C004'
FILENAME = 'reports/bus_position_'
COUNT = 1
INFLUXDB_HOST = 'qwerty.com.ar'
INFLUXDB_PORT = 8086
INFLUXDB_USER = 'admin'
INFLUXDB_PASS = ''
INFLUXDB_DBNAME = 'mim_tp1'
INFLUXDB_PROTOCOL = 'line'
TELEGRAM_TOKEN = '971551324:AAGz8COn-WvxBWbbr_0N5bjeJVyIAAu487A'

###################
#### FUNCTIONS ####
###################

def _url(path):
    return API_TRANSPORTE_URL + path

def get_transporte(endpoint):
    params = {
        'client_id': CLIENT_ID,
        'client_secret':CLIENT_SECRET
        }
    
    resp = requests.get(_url(endpoint),params=params)
    
    if resp.status_code != 200:
        raise ValueError('GET ' + endpoint + ' error')
        
    return resp.json()

def show_results_bus(data):
    for bus in data:
        print('#### BUS ' + str(bus['route_short_name'].encode('utf-8')) + ' ####')
        for key, value in bus.items():
            print('key: ' + str(key) + 'value: ' + str(value))

def show_results_bike(data):
    for key, value in data.items():
        print('key: ' + str(key))
        if 'data' in key:
            for key, value in value.items():
                print('key: ' + str(key))
                for station in value:
                    for key, value in station.items():
                        if 'station_id' in key:
                            print('#### STATION: ' + value + ' ####')
                        print(str(key) + ' - ' + 'value: ' + str(value))
        else:
            print('value: ' + str(value))

def write_json_file(data, filename):
    f= open(filename,"w+")
    f.write(str(json.dumps(data)))
    f.close()

def write_parquet_files(path):
    list = []
    tables = []

    files = os.listdir(path)

    for file in files: # json file to pandas
        list.append(pd.read_json(path + file))
        print(file)

    for element in list: # pandas to parquet
        print(element)
        tables.append(pa.Table.from_pandas(element))
    
    for table in tables: # .parquet file 
        now = datetime.now()
        #print(table)
        pq.write_table(table, 'reports_parquet/bus_position_' + str(now) + '.parquet')

def json_to_pandas(path, timestamp):
    list = []

    files = os.listdir(path)

    for file in files: # json file to pandas
        if str(timestamp) in file:
            list.append(pd.read_json(path + file))
        
    return list

def pandas_to_parquet(data):
    tables = []
    for element in data: # pandas to parquet
        print(element)
        tables.append(pa.Table.from_pandas(element))

    return tables

def write_parquet_file(path, timestamp):    
    list = []
    tables = []

    list = json_to_pandas(path, timestamp)

    tables = pandas_to_parquet(list)
    
    for table in tables: # .parquet file 
        now = datetime.now()
        #print(table)
        pq.write_table(table, 'reports_parquet/bus_position_' + str(now) + '.parquet')

def read_parquet_file(path):
    pass

def write_influxdb(host, port, user, password, dbname, protocol, filename):
    client = DataFrameClient(host, port, user, password, dbname)

    data = pd.read_json(filename)
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data = data.set_index('timestamp')
    # usar tag_columns=None para tags
    # print('#######################################')
    # print('printeamos data a impactar en influx: ' + str(data))

    print("Create database: " + dbname)
    if client.create_database(dbname):
        print('database created succesfully!')

    print("Write DataFrame")
    if client.write_points(data, 'transporte', protocol=protocol):
        print('data saved succesfully!')

    # print("Read DataFrame")
    # if client.query("select * from transporte"):
    #     print(client.query("select * from transporte"))

    #print("Delete database: " + dbname)
    #client.drop_database(dbname)

def telegram_sendMessage(json_name, parquet_name):
    TelegramBot = telepot.Bot(TELEGRAM_TOKEN)
    msg_counter = 0
    msg = TelegramBot.getUpdates()
    for element in msg:
        for key, value in element.items():
            #print('key: ' + str(key))
            #print('value: ' + str(value))
            if 'message' in key:
                chat_id = str(value['chat']['id'])
                print('mensaje ' + str(msg_counter) + ': ' + str(value['text']))
                msg_counter += 1
    TelegramBot.sendMessage(chat_id=chat_id, parse_mode = 'html', text='<b>Nuevo archivo json creado:</b> ' + str(json_name))
    TelegramBot.sendMessage(chat_id=chat_id, parse_mode = 'html', text='<b>Nuevo archivo parquet creado:</b> ' + str(parquet_name))

def show_loop(counter):
    #show_results_bus(data)
    print('#############')
    print('Query #' + str(counter))
    print('#############')

######################
#### MAIN PROGRAM ####
######################

INFLUXDB_PASS = input('Ingrese la password de influxdb: ')
threshold = input('Ingrese cantidad de iteraciones: ')

while True:
    data = get_transporte('/colectivos/vehiclePositionsSimple')
    now = datetime.now()

    print('Writing .json file for ' + FILENAME + '_' + str(now) + '.json....')
    write_json_file(data,FILENAME + '_' + str(now) + '.json') # json files
    print('Writing .parquet file for bus_position_' + str(now) + '.parquet....')
    write_parquet_file('reports/', now) # parquet files
    print('Sending telegram notification...')
    telegram_sendMessage(FILENAME + '_' + str(now) + '.json','bus_position_' + str(now) + '.parquet')    
    print('Writing data to influx...')
    write_influxdb(INFLUXDB_HOST, 
        INFLUXDB_PORT, 
        INFLUXDB_USER,
        INFLUXDB_PASS,
        INFLUXDB_DBNAME,
        INFLUXDB_PROTOCOL,
        FILENAME + '_' + str(now) + '.json'
    )

    show_loop(COUNT)
    COUNT += 1
    if COUNT > int(threshold):
        break
    sleep(30)