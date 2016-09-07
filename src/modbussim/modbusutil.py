import struct

BYTES_PER_REGISTER = 2


def number_to_byte(number):
    return chr(number)


def number_to_bytes(number, number_decimals=0,
                    little_endian=False, signed=False):
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
        number = struct.unpack(format_code, bytestring)[0]
    except Exception as e:
        print(str(e))

    if number_decimals == 0:
        return number
    factor = 10 ** number_decimals
    return number / float(factor)


def string_to_bytestring(inputstring, number_registers=16):
    max_chars = BYTES_PER_REGISTER * number_registers
    bytestring = inputstring.ljust(max_chars)
    bytestring = inputstring.encode(encoding='UTF-8')
    return bytestring


def bytestring_to_string(bytestring, number_registers=16):
    return_string = bytestring.decode(encoding='UTF-8')
    return return_string
