# ModbusSim
Fork of Modbus RTU/TCP simulator with a REST api attached with additional read registers (instantaneous_registers, meter_registers, tariff_data_registers, current_data_registers, prev1_data_registers). For now, this additional registers can be imported only by using '/dump' endpoint.

Looked for a long time for a modbus RTU simulator that could do single server multi-slave simulations and couldn't find anything quite suitable. Something that could be used to rapidly stand-up and teardown various multi-slave setups programatically in modern distributed REST API based systems. Most tools seemed to be written for non-software developers and mostly for windows users.

Got a lot of inspiration, especially from [Luc Jean](https://github.com/ljean) and his work on modbus-tk!

Pretty basic but more updates/improvements coming soon - especially documentation!

If you have docker-compose installed, this is the fast way to get going:
```
docker-compose up
```

Assumptions made below:

1. The simulator server will use `/dev/ttyS0` - can be adjusted in `config/test.conf`
2. The example client will use `/dev/ttyUSB0` - can also be adjust but is currently hardcoded in the slightly modified version of the example client written by Luc Jean and included with modbus-tk.
3. REST api served on port `5002`.

Using a null modem emulator works as well.

To start the simulators REST server:

```sh
git clone https://github.com/emdem/ModbusSim.git
cd ModbusSim/src
sudo python3 server.py
```

Due to some funky threading related issues, currently, the simulator doesn't start until you visit the base url. Open your second terminal window and curl the root to setup the slave devices and start the modbus RTU server:

```sh
emre@nv-emre-lnx-1 ~ $ curl 0.0.0.0:5002
200 OKemre@nv-emre-lnx-1 ~ $ 
```

If you get a 200 OK, in the other terminal window you should see the following in the logs:

```sh
127.0.0.1 - - [13/Jul/2016 11:22:28] "GET / HTTP/1.1" 200 -
modbus_tk.simulator is running...
```

To interact with the API via browser, navigate to:

```sh
http://127.0.0.1:5002/api
```

It is possible to interact with the simulator via the console here to issue commands to add slaves/changes values/add blocks.

You can dump/load the state of all slaves or individual slaves or even registers all via the REST API. You can confirm this by visiting the following url in your browser:
```
http://127.0.0.1:5002/dump
```

Observe the values for the first slave. Saving the output with `curl -o` will allow you to restore all the registers with all the values for all slaves at that time. Then, you can load an sample simulator state from a json file like so:

```sh
# Assuming you are still in the ModbusSim/src directory
curl -X POST -H "Content-Type:application/json" http://127.0.0.1:5002/dump -d@test/simulator_dump.json
```
Upon checking the values for the holding registers of the first slave, they should have changed to those included with the file. You can also verify by using a modbus RTU client/master to read the values over the wire.

To dump/load individual slave devices:

```sh
curl -X POST -H "Content-Type:application/json" http://127.0.0.1:5002/dump/slave/10 -d@test/slave_dump.json
```

To write to invidivual register:

```sh
curl -X POST -H "Content-Type:text/plain" -d "<INT_VALUE>" http://127.0.0.1:5002/slave/10/40001
```

To read from individual register:

```sh
curl http://127.0.0.1:5002/slave/10/40001
```
