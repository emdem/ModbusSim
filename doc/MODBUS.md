# ModBus

** [Modbus Spec](#modbus-spec) **
* [Abbreviations](#abbreviations)
* [Flavors of ModBus](#flavors-of-modbus)
* [Basics](#basics)
* [Transactions in Modbus](#transactions-in-modbus)

** [Dev and Testing Setups](#dev-and-testing-setups) **
* [Single Box Dev Environment](#single-box-dev-environment)

## Modbus Spec

More detailed information can be found in a few different places. Here is summarized what was gathered from all the blaces listed below:

[ModBus](http://www.modbus.org)

[Simply ModBus](http://www.simplymodbus.ca/)

[ModBus Test Kit](https://github.com/ljean/modbus-tk)

[Sunspec](http://www.sunspec.org)

[Sunspec Simulator](https://github.com/emdem/sunspec-sim)

[PySunSpec](https://github.com/sunspec/pysunspec)

## Abbreviations

ADU  Application Data Unit

HDLC High level Data Link Control

MB   ModBus

MDAP ModBus Application Protocol

PDU  Protocol Data Unit

PLC  Programmable Logic Controller

## Flavors of ModBus

There are many ways to use ModBus. Most inverters/batteries are ModBus RTU on RS485.

![modbus architecture](doc/images/modbus_architecture.png)

## Basics

Modbus is master/slave with the master running the Client and the slaves running Servers. So long as the slaves are on the same bus and have seperate addresses, the master can transact with them.


Error free transactions between client and server:



![error free transaction](doc/images/modbus_error_free_transaction.png)




More on Modbus exceptions later... However, if an exception occured at some point during the transaction and it did not time-out it looks like this:



![exceptional transaction](doc/images/modbus_error_transaction.png)


## Transactions in ModBus

Modbus defines a PDU independent of the underlying communication layer. On specific networks/buses, there may be additional fields in the ADU we have to deal with.

![ADU vs PDU](doc/images/modbus_ADU_PDU.png)

The ADU is built by the client that initiates a transaction. The Function Code determines what action to take. We will mostly deal with 0x01 and 0x04 primarily (read coil and read input register respectively) for reading and 0x05, 0x06 and 0x10 (write coil, write register and write registers respectively).

Modbus uses big-Endian notation, so this may be confusing at first. The most significant byte always gets sent first and bytes are 8 bits typically.

Coils can be thought of as booleans - a single bit.

Registers can be thought of as words and their size can vary. For most of our applications, it seems to be two 8 bit values per register. So integers from 0 ... 65536.


## Dev and Testing setups


Initially, there will only be single box modbus RTU over RS485. But there will need to be greater flexibility and potentially long running test server implementations for clients.


## Single Box Dev Environment


If you don't have a RS485 cable for development, that's ok, we can convert a normal CAT5 cable into an adequate RS485 cable for short distances. You can use 2 serial to RS485 connectors or one serial and one USB RS485 connector. I used one USB and one serial com port based RS485 connector on my dev box.

To make the cable, cut the ends off the CAT5 cable if it has them. Strip all the smaller wires inside. There should be 8 total. Take care not to remove any of the copper fibers with the stripper. After all of them are stripped, twist together the solid with the corresponding stripe.

This is what it should look like:
![cat5 to rs485](doc/images/cat5_to_rs485.jpg)

Since we are doing Modbus RTU, we only need 4 of the ports. I connected mine as follows on the USB RS485 connector:
![modbus rtu into usb rs485 connector](doc/images/modbus_rtu_usb.jpg)

I connected the com port based RS485 connector to the only serial port on my dev box:
![modbus rtu into com port rs485 connector](doc/images/modbus_rtu_serial.jpg)

### Setting up the test server

Clone [this](https://github.com/emdem/sunspec-sim) repository containing a simple sunspec simulator written by some badass.

Since it requires a serial port, you will have to run with sudo. I connected my RS485 connector to the first serial port, which is `/dev/ttyS0` on my dev box.

Start the simulator like so:
```
sudo python modsim.py -s /dev/ttyS0 -v 1 -m rtu -i 1 mbmap_test_device.xml
```

To adjust the baud/parity/slave id/base address/etc, modify the sim code - this will all be configurable eventually. Once the simulator is running, if there were no issues, you should see something like this:
```
Initialized modbus rtu simulator: baud = 9600  parity = N  slave id = 1  base address = 40000
Modbus map loaded from mbmap_test_device.xml
Added modbus map block:  address = 40000  count = 939
'quit' for closing the simulator
modbus_tk.simulator is running...
```

If not, something went wrong. If so you can start connecting with a client.

### Running the test client
The test client that works currently is in the client/ subdirectory and can be run like so:
```
emre@nv-emre-lnx-1 ~/projects/power/modbus/client $ sudo python3 modbustk-client.py 
sunspec_id:  SunS
sunspec_did:  1
sunspec_length:  65
manufacterer:  SunSpecText
model:  TestInverter
options:  opt_a_b_c
version:  1.2.3
serial:  sn-123456789
slave_id:  0
device_length:  0
```
If everything was successful, you should see something similar. The values are being read over the RS485 bus. You can confirm with a multimeter by connecting the ground and either the T/R- or the T/R+.

This is what the traffic (in hex) looks like on the wire between client/server:
```
-->0x1 0x3 0x9c 0x40 0x0 0x2 0xeb 0x8f
<--0x1 0x3 0x4 0x53 0x75 0x6e 0x53 0x96 0xf0
-->0x1 0x3 0x9c 0x42 0x0 0x1 0xa 0x4e
<--0x1 0x3 0x2 0x0 0x1 0x79 0x84
-->0x1 0x3 0x9c 0x43 0x0 0x1 0x5b 0x8e
<--0x1 0x3 0x2 0x0 0x41 0x78 0x74
-->0x1 0x3 0x9c 0x44 0x0 0x10 0x2a 0x43
<--0x1 0x3 0x20 0x53 0x75 0x6e 0x53 0x70 0x65 0x63 0x54 0x65 0x78 0x74 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x33 0x9c
-->0x1 0x3 0x9c 0x54 0x0 0x10 0x2b 0x86
<--0x1 0x3 0x20 0x54 0x65 0x73 0x74 0x49 0x6e 0x76 0x65 0x72 0x74 0x65 0x72 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x4a 0xeb
-->0x1 0x3 0x9c 0x64 0x0 0x8 0x2b 0x83
<--0x1 0x3 0x10 0x6f 0x70 0x74 0x5f 0x61 0x5f 0x62 0x5f 0x63 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x4c 0x66
-->0x1 0x3 0x9c 0x6a 0x0 0x8 0x4a 0x40
<--0x1 0x3 0x10 0x0 0x0 0x0 0x0 0x31 0x2e 0x32 0x2e 0x33 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0xf1 0x67
-->0x1 0x3 0x9c 0x72 0x0 0x10 0xca 0x4d
<--0x1 0x3 0x20 0x0 0x0 0x0 0x0 0x73 0x6e 0x2d 0x31 0x32 0x33 0x34 0x35 0x36 0x37 0x38 0x39 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x0 0x73 0xb1
-->0x1 0x3 0x9c 0x82 0x0 0x1 0xa 0x72
<--0x1 0x3 0x2 0x0 0x0 0xb8 0x44
-->0x1 0x3 0x9c 0x83 0x0 0x1 0x5b 0xb2
<--0x1 0x3 0x2 0x0 0x0 0xb8 0x44
```
