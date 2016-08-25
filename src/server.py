#!/usr/bin/env python2
# -*- coding: utf_8 -*-

##############################################
# This class is the interface implementation
##############################################
import argparse
import logging
import os
import signal

from threading import Thread

from configparser import ConfigParser

from modbussim.modbussim import ModbusSim
from flask import Flask, request, json, jsonify, redirect
from flasgger import Swagger
app = Flask(__name__)
app.config['SWAGGER'] = {
    "swagger_version": "2.0",
    "specs": [
        {
            "version": "1.0.0",
            "title": "ModbusSim API",
            "description": "An API for interacting with ModbusSim",
            "endpoint": 'spec',
            "route": '/spec',
        }
    ]
}
Swagger(app)

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

    # in debug mode, this will get called twice. run only after reload
    if config.getboolean('server', 'debug') and not os.environ.get('WERKZEUG_RUN_MAIN'):
        LOGGER.info("Running in debug mode, will initialize after reload")
        return

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

@app.route('/api')
def swagger():
    return redirect("/apidocs/index.html", code=302)

@app.route('/slaves')
def slaves():
    """
        ModbusSim API / Get Slaves
        ---
        tags:
          - modbus-sim
        summary: "Returns Slaves of known to Modbus Sim"
        produces:
          - "application/json"
        responses:
          200:
            description: A list of slaves and their configuration
            schema:
                    id: SlavesDictionary
                    type: object
                    description: "Slaves Dictionary"
                    required:
                    - "1"
                    properties:
                        "1":
                            type: object
                            description: "Slave Configuration"
                            schema:
                                id: SlaveConfiguration
                                type: object
                                properties:
                                    holding_register_count:
                                        type: integer
                                        description: "Metric Value"
                                        example: 9999
                                    input_register_count:
                                        type: integer
                                        description: "Metric Value"
                                        example: 9999
                        "2":
                            type: object
                            description: "Slave Configuration"
                            schema:
                                id: SlaveConfiguration
                                type: object
                                properties:
                                    holding_register_count:
                                        type: integer
                                        description: "Metric Value"
                                        example: 9999
                                    input_register_count:
                                        type: integer
                                        description: "Metric Value"
                                        example: 9999

    """
    global sim
    return jsonify(sim.slaves)


@app.route('/dump')
def dump():
    """
        ModbusSim API / Dump Slave Configurations
        ---
        tags:
          - modbus-sim
        summary: "Returns JSON Configuration of Slaves known to Modbus Sim"
        produces:
          - "application/json"
        responses:
          200:
            description: A dump of all slave configurations
            schema:
                    id: SlaveConfigList
                    type: array
                    description: "Slave Configuration List"
                    items:
                        id: SlaveConfiguration
                        type: object
                        required:
                            - "slave_id"
                        properties:
                            slave_id:
                                type: integer
                                example: 1
                            input_register_count:
                                type: integer
                                description: "Metric Value"
                                example: 9999
                            input_registers:
                                type: array
                                description: "Array of Input Register Values"
                                example: [ 0, 0, 0 ]
                            holding_register_count:
                                type: integer
                                description: "Metric Value"
                                example: 9999
                            holding_registers:
                                type: array
                                description: "Array of Holding Register Values"
                                example: [ 0, 0, 0 ]
    """
    global sim
    return sim.dump_simulator()


@app.route('/dump', methods=['POST'])
def load_dump():
    """
        ModbusSim API / Load Slave Configurations
        ---
        tags:
          - modbus-sim
        summary: "Loads JSON Configuration of Slaves known to Modbus Sim"
        consumes:
          - "application/json"
        parameters:
          - name: "SlaveConfigList"
            in: body
            required: true
            description: The JSON configuration
            schema:
                    id: SlaveConfigList
                    type: array
                    description: "Slave Configuration List"
                    items:
                        id: SlaveConfiguration
                        type: object
                        required:
                            - "slave_id"
                        properties:
                            slave_id:
                                type: integer
                                example: 1
                            input_register_count:
                                type: integer
                                description: "Metric Value"
                                example: 9999
                            input_registers:
                                type: array
                                description: "Array of Input Register Values"
                                example: [ 1, 2, 3 ]
                            holding_register_count:
                                type: integer
                                description: "Metric Value"
                                example: 9999
                            holding_registers:
                                type: array
                                description: "Array of Holding Register Values"
                                example: [ 1, 2, 3 ]
        responses:
            200:
                description: The result of the load operation
    """
    global sim
    if request.headers['Content-Type'] == 'application/json':
        sim.load_simulator_dump(request.json)
        return "Finished loading dump", 200
    return "Unsupported Media Type", 415


@app.route('/slave/<int:slave_id>')
def slave(slave_id):
    """
        ModbusSim API / Get Slave Info
        ---
        tags:
          - modbus-sim
        summary: "Returns JSON info for Slave"
        produces:
          - "application/json"
        parameters:
          - name: slave_id
            in: path
            type: integer
            required: true
            description: the slave ID
        responses:
          200:
            description: The slave configuration
            schema:
                type: object
                description: "Slave Configuration"
                schema:
                    id: SlaveConfiguration
                    type: object
                    properties:
                        holding_register_count:
                            type: integer
                            description: "Metric Value"
                            example: 9999
                        input_register_count:
                            type: integer
                            description: "Metric Value"
                            example: 9999
    """
    global sim
    if slave_id in sim.slaves:
        return jsonify(sim.slaves[slave_id])
    else:
        return "Slave ID: " + str(slave_id) + " does not exist.", 400

@app.route('/slave/dump/<int:slave_id>', methods=['POST'])
def load_slave_dump(slave_id):
    """
        ModbusSim API / Load Slave Configurations
        ---
        tags:
          - modbus-sim
        summary: "Loads JSON Configuration of Slaves known to Modbus Sim"
        consumes:
          - "application/json"
        parameters:
          - name: slave_id
            in: path
            type: integer
            required: true
            description: the slave ID
          - name: "SlaveConfiguration"
            in: body
            required: true
            description: The JSON configuration
            schema:
                id: SlaveConfiguration
                type: object
                required:
                    - "slave_id"
                schema:
                    properties:
                        slave_id:
                            type: integer
                            example: 1
                        input_register_count:
                            type: integer
                            description: "Metric Value"
                            example: 9999
                        input_registers:
                            type: array
                            description: "Array of Input Register Values"
                            example: [ 1, 2, 3 ]
                        holding_register_count:
                            type: integer
                            description: "Metric Value"
                            example: 9999
                        holding_registers:
                            type: array
                            description: "Array of Holding Register Values"
                            example: [ 1, 2, 3 ]
        responses:
            200:
                description: The result of the load operation
    """
    global sim
    if request.headers['Content-Type'] == 'application/json':
        sim.load_slave_dump(request.json)
        return "Finished loading dump", 200
    return "Unsupported Media Type", 415


@app.route('/slave/dump/<int:slave_id>')
def slave_dump(slave_id):
    """
        ModbusSim API / Dump Slave Configuration
        ---
        tags:
          - modbus-sim
        summary: "Returns JSON Configuration of Slaves known to Modbus Sim"
        produces:
          - "application/json"
        parameters:
          - name: slave_id
            in: path
            type: integer
            required: true
            description: the slave ID
        responses:
          200:
            description: The slave configuration dump
            schema:
                id: SlaveConfiguration
                type: object
                required:
                    - "slave_id"
                required:
                    - "slave_id"
                schema:
                    properties:
                        slave_id:
                            type: integer
                            example: 1
                        input_register_count:
                            type: integer
                            description: "Metric Value"
                            example: 9999
                        input_registers:
                            type: array
                            description: "Array of Input Register Values"
                            example: [ 1, 2, 3 ]
                        holding_register_count:
                            type: integer
                            description: "Metric Value"
                            example: 9999
                        holding_registers:
                            type: array
                            description: "Array of Holding Register Values"
                            example: [ 1, 2, 3 ]
    """
    global sim
    slave = sim.server.get_slave(slave_id)
    return sim.dump_slave(slave_id)


@app.route('/slave/<int:slave_id>/<int:address>')
def slave_read(slave_id, address):
    """
        ModbusSim API / Read Register
        ---
        tags:
          - modbus-sim
        summary: "Returns register value"
        produces:
          - "text/plain"
        parameters:
          - name: slave_id
            in: path
            type: integer
            required: true
            description: the slave ID
          - name: address
            in: path
            type: integer
            required: true
            description: the register address
        responses:
          200:
            description: The register value
            schema:
                type: integer
                description: "Register Value"
                example: 10
    """
    global sim
    if slave_id not in sim.slaves:
        return "Slave does not exist", 400
    slave = sim.server.get_slave(slave_id)
    if 30000 <= address < 30001 + config.getint('slave-config', 'input_register_count'):
        block = 'input_registers'
    elif 40000 <= address < 40001 + config.getint('slave-config', 'holding_register_count'):
        block = 'holding_registers'
    else:
        return "Address is out of range", 400
    value = slave.get_values(block, address, 1)

    return str(value[0])


@app.route('/slave/<int:slave_id>/<int:address>', methods=['POST'])
def slave_write(slave_id, address):
    """
        ModbusSim API / Write Register
        ---
        tags:
          - modbus-sim
        summary: "Returns register value"
        consumes:
          - "text/plain"
        parameters:
          - name: slave_id
            in: path
            type: integer
            required: true
            description: the slave ID
          - name: address
            in: path
            type: integer
            required: true
            description: the register address
          - name: "RegisterValue"
            in: body
            required: true
            description: The register value
            schema:
                id: RegisterValue
                type: int
                example: 10
        responses:
            200:
                description: The result of the write operation
    """
    global sim
    if slave_id not in sim.slaves:
        return "Slave does not exist", 400
    slave = sim.server.get_slave(slave_id)

    if 30000 <= address < 30001 + config.getint('slave-config', 'input_register_count'):
        block = 'input_registers'
    elif 40000 <= address < 40001 + config.getint('slave-config', 'holding_register_count'):
        block = 'holding_registers'
    else:
        return "Address is out of range", 400

    if request.headers['Content-Type'] == 'text/plain':
        value = None
        try:
            value = int(request.data)
        except Exception as asdf:
            return "Could not convert to integer", 400
        slave.set_values(block, address, value)
        return "Success", 200
    elif request.header['Content-Type'] == 'application/json':
        return "JSON message: " + str(json.dumps(request.json)), 200
    else:
        return "Unsupported Media Type", 415

@app.errorhandler(Exception)
def unhandled_exception(e):
    LOGGER.error('Unhandled Exception: %s', e)
    return str(e), 500


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
        config.set('slave-config', 'input_register_count', '9999')
        config.set('slave-config', 'holding_register_count', '9999')

    if not 'server' in config.sections():
        config.add_section('server')
        config.set('server', 'host', '0.0.0.0')
        config.set('server', 'port', '5002')
        config.set('server', 'debug', 'True')

    return config


def signal_handler(signm, frame):
    global sim
    log.info('Got Signal %s, exiting now.' % (str(signm)))
    sim.close() 
    log.info('Stopped modbus simulator.')
    sys.exit(0)



def main():
    global config
    args = parse_args()
    config = load_config(args)
    init_sim()


if __name__ == '__main__':
    signal.signal(signal.SIGABRT, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGQUIT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    main()
    app.run(host=config.get('server','host'),port=config.getint('server','port'),debug=config.getboolean('server','debug'))
