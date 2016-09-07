#/usr/bin/env python3
# -*- coding: utf_8 -*-
import struct
import serial
import logging
import modbus_tk
import modbus_tk.defines as cst
from modbus_tk import modbus_rtu

PORT = '/dev/ttyUSB0'


def getString(int_tuple):
    '''
    so ugly... refactor
    '''
    return "".join([x.decode('cp437') for x in [(x.to_bytes((x.bit_length()+7)//8, 'big') or b'\0') for x in int_tuple]])


def main():
    logger = modbus_tk.utils.create_logger("console")
    logger.setLevel(logging.ERROR)
    try:
        #Connect to the slave
        master = modbus_rtu.RtuMaster(
            serial.Serial(port=PORT, baudrate=9600, bytesize=8, parity='N', stopbits=1, xonxoff=0)
        )
        master.set_timeout(1.0)
        master.set_verbose(True)
        logger.info("connected")


        sunspec_id = master.execute(10, cst.READ_HOLDING_REGISTERS, 40000, 4)
        print(sunspec_id)
        print(getString(sunspec_id))

        test = master.execute(10, cst.WRITE_SINGLE_REGISTER, 40000, output_value=21365)
        test = master.execute(10, cst.WRITE_SINGLE_REGISTER, 40001, output_value=28243)
        test = master.execute(10, cst.WRITE_SINGLE_REGISTER, 40002, output_value=0)
        test = master.execute(10, cst.WRITE_SINGLE_REGISTER, 40003, output_value=0)
        sunspec_id = master.execute(10, cst.READ_HOLDING_REGISTERS, 40000, 4)
        print(sunspec_id)
        print(getString(sunspec_id))



    except modbus_tk.modbus.ModbusError as exc:
        logger.error("%s- Code=%d", exc, exc.get_exception_code())



BYTES_PER_REGISTER = 2

def number_to_byte(number):
    return chr(number)

def number_to_bytes(number, number_decimals=0, little_endian=False, signed=False):
    factor = 10 ** number_decimals
    integer = int(float(number) * factor)
    format_code = ''
    if little_endian:
        format_code += '<'
    else:
        format_code += '>'

    if signed:
        format_code += 'h'
    else:
        format_code += 'H'

    try:
        bytestring = struct.pack(format_code, integer)
    except Exception as e:
        print(str(e))
    return bytestring

def bytes_to_number(bytestring, number_decimals=0, signed=False):
    '''
    Assumes:
    - always big endian since this is used from modbus->python
    '''
    format_code = '>'
    if signed:
        format_code += 'h'
    else:
        format_code += 'H'

    try:
        number = struct.unpack(formatstring, bytestring)[0]
    except Exception as e:
        print(str(e))

    if number_decimals == 0:
        return number
    factor = 10 ** number_decimals
    return number / float(factor)


def string_to_bytestring(inputstring, number_registers=16):
    max_chars = BYTES_PER_REGISTER * number_registers
    bytestring = inputstring.ljust(max_chars)
    bytestring = bytestring.encode(encoding='UTF-8')
    return bytestring

def bytestring_to_string(bytestring, number_registers=16):
    max_chars = BYTES_PER_REGISTER * number_registers
    return_string = bytestring.decode(encoding='UTF-8')
    return return_string


if __name__ == "__main__":
    main()
