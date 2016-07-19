#!/usr/bin/env python2
# -*- coding: utf_8 -*-

##############################################
## This class is the interface implementation
##############################################
import argparse
import logging
import serial
import struct
import sys

from threading import Thread

from configparser import ConfigParser
from modbus_tk import modbus

from modbussim.modbussim import ModbusSim
from flask import json
from flask import Flask, request
app = Flask(__name__)
app.config['DEBUG'] = True
app.config['PORT'] = 8082
app.config['HOST'] = '0.0.0.0'


LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.StreamHandler())
LOGGER.setLevel(logging.DEBUG)

thread = None
sim = None


def init_sim():
    global thread
    global config
    global sim
    if sim is None:
        LOGGER.info("Sim was not setup so configuring sim")
        slave_count = config.getint('slaves','slave_count')
        slave_start_id = config.getint('slaves', 'slave_start_id')
        input_register_count = config.getint('slave-config', 'input_register_count')
        holding_register_count = config.getint('slave-config', 'holding_register_count')

        if config.mode == 'rtu':
            sim = ModbusSim(mode=config.mode, port=config.serial, baud=config.rtu_baud)
        else:
            sim = ModbusSim(mode=config.mode, port=config.port, hostname=config.hostname)


        for slave_id_offset in range(0, slave_count):
            sim.add_slave(slave_start_id + slave_id_offset, input_register_count, holding_register_count)
    if thread is None:
        thread = Thread(target=sim.start)
        thread.start()


@app.route('/')
def index():
    return "200 OK"

@app.route('/slaves')
def slaves():
    global sim
    return str(sim.slaves)


@app.route('/dump')
def dump():
    global sim
    return sim.dump_simulator()

@app.route('/dump', methods=['POST'])
def load_dump():
    global sim
    if request.headers['Content-Type'] == 'application/json':
        sim.load_simulator_dump(request.json)
        return "Finished loading dump"
    return "Expected JSON message"


@app.route('/slave/<int:slave_id>')
def slave(slave_id):
    global sim
    if slave_id in sim.slaves:
        return str(sim.slaves[slave_id])
    else:
        return "Slave ID: " + str(slave_id) + " does not exist."

@app.route('/slave/dump/<int:slave_id>', methods=['POST'])
def load_slave_dump(slave_id):
    global sim
    if request.headers['Content-Type'] == 'application/json':
        sim.load_slave_dump(request.json)
        return "Finished loading dump"
    return "Expected JSON message"


@app.route('/slave/dump/<int:slave_id>')
def slave_dump(slave_id):
    global sim
    slave = sim.server.get_slave(slave_id)
    values = slave.get_values('holding_registers', 40000, 200)
    return sim.dump_slave(slave_id)

@app.route('/slave/<int:slave_id>/<int:address>')
def slave_read(slave_id, address):
    global sim
    if slave_id not in sim.slaves:
        return "Slave does not exist"
    slave = sim.server.get_slave(slave_id)
    if address < 40000 or address > 40200:
        return "Address is out of range"
    value = slave.get_values('holding_registers', address, 1)
    return str(value)

@app.route('/slave/<int:slave_id>/<int:address>', methods=['POST'])
def slave_write(slave_id, address):
    global sim
    if slave_id not in sim.slaves:
        return "Slave does not exist"
    slave = sim.server.get_slave(slave_id)
    if address < 40000 or address > 40200:
        return "Address is out of range"

    if request.headers['Content-Type'] == 'text/plain':
        value = None
        try:
            value = int(request.data)
        except Exception as asdf:
            return "Could not convert to integer"
        slave.set_values('holding_registers', address, value)
        return "Success"
    elif request.header['Content-Type'] == 'application/json':
        return "JSON message: " + str(json.dumps(request.json))
    else:
        return "415 Unsupported Media Type"



def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--slave_id', type=str, default=1, help='slave id for the modbus device')
    parser.add_argument('-m', '--mode', type=str, choices=('rtu', 'tcp'), default='rtu', help='modbus mode')
    parser.add_argument('-P', '--port', type=int, default=5005, help='IP port if using TCP mode')
    parser.add_argument('-p', '--rtu_parity', type=str, choices=('even','odd','none'), default='none', help='modbus over serial parity')
    parser.add_argument('-b', '--rtu_baud', type=int, default=9600, help='baud rate for modbus')
    parser.add_argument('-t', '--hostname', type=str, default='127.0.0.1', help='IP hostname or address')
    parser.add_argument('-c', '--config', type=str, default='../config/test.conf', help='modbus simulator configuration file')
    parser.add_argument('-s', '--serial', type=str, default='/dev/ttyS0', help='serial port on which to sim')
    parser.add_argument('-n', '--slave_count', type=int, default=0, help='Number of slave devices to create')
    parser.add_argument('-d', '--slave_start_id', type=int, default=1, help='Starting id of slaves')

    args = parser.parse_args()
    return args

def load_config(args):
    config = ConfigParser(allow_no_value=True)
    config.read(args.config)
    if args.slave_id:
        config.slave_id = args.slave_id
    if args.mode:
        config.mode = args.mode
    if args.port:
        config.port = args.port
    if args.rtu_parity:
        config.rtu_parity = args.rtu_parity
    if args.rtu_baud:
        config.rtu_baud = args.rtu_baud
    if args.hostname:
        config.hostname = args.hostname
    if args.serial:
        config.serial = args.serial

    if not 'slaves' in config.sections():
        config.add_section('slaves')
        config.set('slaves', 'slave_count', str(args.slave_count))
        config.set('slaves', 'slave_start_id', str(args.slave_start_id))

    if not 'slave-config' in config.sections():
        config.add_section('slave-config')
        config.set('slave-config', 'input_register_count', '0')
        config.set('slave-config', 'holding_register_count', '200')

    return config


def main():
    global config
    args = parse_args()
    config = load_config(args)
    init_sim()


if __name__ == '__main__':
    main()
    app.run(host=config.get('server','host'),port=config.getint('server','port'),debug=config.getboolean('server','debug'))
