# -*- coding: utf_8 -*-
import logging
import serial

from modbus_tk import modbus
from modbus_tk.hooks import call_hooks
from modbus_tk.modbus_rtu import RtuServer
from modbus_tk.modbus_tcp import TcpServer
from modbus_tk.simulator import Simulator
from modbus_tk.utils import calculate_rtu_inter_char


LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.StreamHandler())
LOGGER.setLevel(logging.DEBUG)


class ModbusSimError(Exception):
    pass


class ModbusDatabank(modbus.Databank):
    def handle_request(self, query, request):
        request_pdu = ''
        try:
            (slave_id, request_pdu) = query.parse_request(request)
            if slave_id == 0:
                for key in self._slaves:
                    self._slaves[key].handle_request(request_pdu,
                                                     broadcast=True)
                return
            else:
                slave = self.get_slave(slave_id)
                response_pdu = slave.handle_request(request_pdu)
                response = query.build_response(response_pdu)
                return response
        except Exception as e:
            call_hooks('modbus.Databank.on_error', (self, e, request_pdu))
            LOGGER.error('handle_request failed: ' + str(e))
        except:
            LOGGER.error('handle_request failed: unknown exception')


class ModbusRtuServer(RtuServer):
    '''
    RTU server implementation with custom handle/init methods
    '''
    _serial = None

    def __init__(self, serial, databank=None):
        self._serial = serial
        modbus.Server.__init__(self, databank if databank else ModbusDatabank())
        LOGGER.info('RtuServer alt %s is %s' % (self._serial.portstr,
                                                'opened' if self._serial.isOpen() else 'closed'))
        self._t0 = calculate_rtu_inter_char(self._serial.baudrate)
        self._serial.interCharTimeout = 1.5 * self._t0
        self._serial.timeout = 10*self._t0
        LOGGER.info('interchar timeout = %f' % (self._serial.interCharTimeout,))
        LOGGER.info('timeout = %f' % (self._serial.timeout,))

    def _handle(self, request):
        LOGGER.debug(self.get_log_buffer('-->', request))

        query = self._make_query()
        retval = call_hooks('modbus.Server.before_handle_request', (self, request))
        if retval:
            request = retval
        response = self._databank.handle_request(query, request)
        retval = call_hooks('modbus.Server.after_handle_request', (self, response))
        if retval:
            response = retval
        if response:
            LOGGER.debug(self.get_log_buffer('<--', response))
        return response

    def get_log_buffer(self, prefix, buff):
        log = prefix
        for i in buff:
            log += str(hex(i)) + ' '
        return log[:-1]


class ModbusSim(Simulator):

    slaves = {}

    def __init__(self, mode, port, baud=None, hostname=None, verbose=None):
        self.rtu = None
        self.mode = mode
        if self.mode == 'rtu' and baud and port:
            self.rtu = serial.Serial(port=port, baudrate=baud)
            Simulator.__init__(self, ModbusRtuServer(self.rtu))
            # timeout is too fast for 19200 so increase a little bit
            self.server._serial.timeout *= 2
            self.server._serial.interCharTimeout *= 2
            LOGGER.info('Initializing x modbus %s simulator: baud = %d port = %s parity = %s' % (self.mode, baud, port, self.rtu.parity))
            LOGGER.info('stop bits = %d xonxoff = %d' % (self.rtu.stopbits, self.rtu.xonxoff))
        elif self.mode == 'tcp' and hostname and port:
            Simulator.__init__(self, TcpServer(address=hostname, port=port))
            LOGGER.info('Initializing modbus %s simulator: addr = %s port = %s' % (self.mode, hostname, port))
        else:
            raise ModbusSimError('Unknown mode: %s' % (mode))

        self.server.set_verbose(True)

    def start(self):
        self.server.start()
        self.rpc.start()
        LOGGER.info('modbus_tk.simulator is running...')
        self._handle()

    def close(self):
        self.rpc.close()
        self.server.stop()

    def add_slave(self, slave_id, registers_array):
        if slave_id in self.slaves:
            raise ModbusSimError('Slave with slaveID: %s already exists...' % (slave_id))
        LOGGER.info('Generating slave with slave_id: %s' %(slave_id))
        slave = self.server.add_slave(slave_id)
        registers_dict = {}

        for register_config in registers_array:
            register_name = register_config['register_section_name']
            register_count = register_config['register_count']
            start_address = register_config['start_address']
            register_type = register_config['register_type']
            LOGGER.info('Slave id: %s has section %s with %d registers' %(slave_id, register_name, register_count))
            registers_dict.update({register_name : {
                register_name + '_register_count': register_count,
                register_name + '_start_address': start_address,
                register_name + '_register_type': register_type
            }})
            if register_count > 0:
                slave.add_block(register_name + '_registers', register_type, start_address, register_count)

        self.slaves.update({slave_id: registers_dict})


    def dump_simulator(self):
        if not self.slaves:
            return ""
        toReturn = "["
        for slave in self.slaves:
            if not toReturn.endswith('['):
                toReturn += ","
            toReturn += self.dump_slave(slave)
        toReturn += "]"
        return toReturn

    def load_simulator_dump(self, dump):
        for slave in self.slaves:
            self.server.remove_slave(slave)
        self.slaves = {}
        for slave in dump:
            self.load_slave_dump(slave)

    def dump_slave(self, slave_id):
        if slave_id not in self.slaves:
            return 'Specified slave with slave_id %d does not exist.' % (slave_id,)
        slave = self.server.get_slave(slave_id)

        toReturn = '{"slave_id":' + str(slave_id)
        toReturn += ',"registers":['
        for register_name in self.slaves[slave_id]:
            LOGGER.info('Register: %s' %(register_name))
            register_section = self.slaves[slave_id][register_name]
            register_count = register_section[register_name + '_register_count']
            start_address = register_section[register_name + '_start_address']
            register_type = register_section[register_name + '_register_type']
            registers = []

            if register_count > 0:
                registers = slave.get_values(register_name + '_registers', start_address, register_count)

            if not toReturn.endswith('['):
                toReturn += ','
            toReturn += '{"name": "' + register_name + '"'
            toReturn += ',"register_count": '+str(register_count)
            toReturn += ',"register_type": '+str(register_type)
            toReturn += ',"start_address": '+str(start_address)
            toReturn += ',"register_data": '+str(list(registers))
            toReturn += '}'

        toReturn += ']}'
        return toReturn

    def load_slave_dump(self, dump):
        registersDict = {}
        slave_id = dump['slave_id']
        registers = dump['registers']
        for register in registers:
            self.load_register(slave_id, register, registersDict)
        self.slaves.update({slave_id: registersDict})

    def load_register(self, slave_id, register, registers_dict):
        print(register)
        register_name = register['name']
        register_count = register['register_count']
        register_type = register['register_type']
        start_address = register['start_address']
        register_data = register['register_data']
        if slave_id in self.slaves:
            slave = self.server.get_slave(slave_id)
            slaveDict = self.slaves[slave_id]
            if register_name in slaveDict and slaveDict[register_name + '_register_count'] > 0:
                slave.remove_block(register_name)
        else:
            slave = self.server.add_slave(slave_id)
        
        if register_count > 0:
            slave.add_block(register_name + '_registers',
                            register_type, start_address, register_count)
            slave.set_values(register_name + '_registers', start_address, register_data)

        registers_dict.update({register_name : {
                register_name + '_register_count': register_count,
                register_name + '_start_address': start_address,
                register_name + '_register_type': register_type
            }})
