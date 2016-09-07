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
            LOGGER.info('Initializing modbus %s simulator: baud = %d port = %s parity = %s' % (self.mode, baud, port, self.rtu.parity))
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

    def add_slave(self, slave_id, input_register_count, holding_register_count):
        if slave_id in self.slaves:
            raise ModbusSimError('Slave with slaveID: %s already exists...' % (slave_id, ))

        LOGGER.info('Generating slave with slave_id: %d having %d input registers and %d holding registers' %
                    (slave_id, input_register_count, holding_register_count))

        slave = self.server.add_slave(slave_id)
        self.slaves.update({slave_id:
                            {'input_register_count': input_register_count,
                             'holding_register_count': holding_register_count}})
        if input_register_count > 0:
            slave.add_block('input_registers', 4,
                            30001, input_register_count)
        if holding_register_count > 0:
            slave.add_block('holding_registers', 3,
                            40001, holding_register_count)

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
        input_register_count = self.slaves[slave_id]['input_register_count']
        holding_register_count = self.slaves[slave_id]['holding_register_count']
        input_registers = []
        holding_registers = []
        if input_register_count > 0:
            input_registers = slave.get_values('input_registers', 30001,
                                               input_register_count)
        if holding_register_count > 0:
            holding_registers = slave.get_values('holding_registers', 40001,
                                                 holding_register_count)
        toReturn = '{"slave_id":' + str(slave_id)
        toReturn += ',"input_register_count":'+str(input_register_count)
        toReturn += ',"input_registers":'+str(list(input_registers))
        toReturn += ',"holding_register_count":'+str(holding_register_count)
        toReturn += ',"holding_registers":'+str(list(holding_registers))
        toReturn += '}'
        return toReturn

    def load_slave_dump(self, dump):
        slave_id = dump['slave_id']
        input_register_count = dump['input_register_count']
        input_registers = dump['input_registers']
        holding_register_count = dump['holding_register_count']
        holding_registers = dump['holding_registers']
        slave = None
        if dump['slave_id'] in self.slaves:
            slave = self.server.get_slave(slave_id)
            if self.slaves[slave_id]['input_register_count'] > 0:
                slave.remove_block('input_registers')
            if self.slaves[slave_id]['holding_register_count'] > 0:
                slave.remove_block('holding_registers')
        else:
            slave = self.server.add_slave(slave_id)

        if input_register_count > 0:
            slave.add_block('input_registers',
                            4, 30001, input_register_count)
            slave.set_values('input_registers', 30001, input_registers)
        if holding_register_count > 0:
            slave.add_block('holding_registers',
                            3, 40001, holding_register_count)
            slave.set_values('holding_registers', 40001, holding_registers)

        self.slaves.update({slave_id:
                            {'input_register_count': input_register_count,
                             'holding_register_count': holding_register_count}})
