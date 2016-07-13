#/usr/bin/env python3
# -*- coding: utf_8 -*-

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
        sunspec_id = master.execute(10, cst.READ_HOLDING_REGISTERS, 40000, 3)
        print('sunspec_id: ', getString(sunspec_id))
        test = master.execute(10, cst.WRITE_SINGLE_REGISTER, 40000, output_value=1234)
        test = master.execute(10, cst.WRITE_SINGLE_REGISTER, 40000, output_value=123)
        print(test)
        test2 = master.execute(10, cst.WRITE_SINGLE_REGISTER, 40001, output_value=123)
        print(test2)
        test2 = master.execute(10, cst.WRITE_SINGLE_REGISTER, 40002, output_value=200)
        sunspec_id = master.execute(10, cst.READ_HOLDING_REGISTERS, 40000, 3)
        print(sunspec_id)


    except modbus_tk.modbus.ModbusError as exc:
        logger.error("%s- Code=%d", exc, exc.get_exception_code())

if __name__ == "__main__":
    main()

