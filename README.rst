# PyPLC
The PyPLC tango device server for controlling Modbus based devices

This device server requires:

 - Tango cpp packages
 - PyTango library
 - Fandango library
 - Modbus Device Server

Information on how to obtain these packages is available at: www.tango-controls.org

See the /doc folder for more details

Notes on version 8.0
--------------------

8.0: Optimized to send events on ModbusMap update

    Added AverageModbusCycle attribute
    ModbusMap.trigger_callbacks filtered by changed address
    Use changed to keep array index that differ
    Added custom command to Regs call
    Added custom command to Maps
    Move mapping updates to SendModbusCommand
    Solve bug on Mapping periods (ms to s)
    Implement callbacks mechanism for maps (subscribe/trgger)

Other changes:

    Solve bug when states not updated at Init
    solve bug on empty SnapFile property
    Add InputStatus commands, set callbacks if UseEvents
    allow false to disable snapshots
    added Utils file for exporting conversion methods to GUI's
    Set Device to FAULT if communication is lost
    Refactor lambdas init, pep8 and shorter IeeeFloats
    Refactor IeeeFloat/Ints2Float, errors/slices
    Add export(filename) to ModbusMap
    Clean Modbus proxy on exit to avoid coredumps


