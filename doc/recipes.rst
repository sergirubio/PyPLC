Testing and Configuring a PyPLC Device
======================================

You must create a Modbus and a PyPLC device and set the following DEVICE properties::

  Modbus.Iphost        10.0.X.X
  Modbus.ModbusID      1
  Modbus.Protocol      TCP or RTU
  Modbus.Serialline    TCP or the name of a tango serial device
  Modbus.TCPPort       502
  
  PyPLC.Modbus_name        your/modbus/device
  PyPLC.ModbusTimeWait     50 
  PyPLC.ModbusCacheConfig  0
 
Launch your devices with Astor or from console and verify that you're able to read registers using Modbus commands::

  # ipython

  : import PyTango as pt

  : modbus = pt.DeviceProxy('your/plc/name-mbus')

  : pyplc = pt.DeviceProxy('your/plc/name')

  : start_address,n_registers = 0,10

  : print(modbus.ReadHoldingRegisters([start_address,n_registers]))

  # That should do the same than doing

  : print(pyplc.Regs([start_address,n_registers]))


Once modbus works, DynamicAttributes property can be defined directly pointing to the result of a Modbus command::

  ARRAY = DevVarLongArray(InputRegs(0,10))

  INTEGER = int(Reg(5))

  BIT = bool(Bit(Reg(5),3))

As long as you don't change the type of attributes a restart of the device is not needed. Just execute this command::

  : pyplc.updateDynamicAttributes()

  : pyplc.read_attribute('ARRAY').value

    [2,12,3,5,6,0,0,0,0,18]

  : pyplc.INTEGER

    0

But, each modbus command execution takes channel acces time from the rest, so it may be optimal to read as many values as possible in a single call and reference attributes between them::

  ARRAY = DevVarLongArray(Regs(0,120)) #All mapping is read here

  FLOATS = DevVarDoubleArray([i/10. for i in ARRAY])

  INTEGER = int(ARRAY[5]) #Just updates from the last mapping

  FLOAT = float(ARRAY[100])

  BIT_5_6 = bool(Bit(ARRAY[5],6))

Using Arrays to update the data will require you to put the attribute reading in polling to force the rest of values to be updated. In case of arrays bigger than 120 registers or when having big number of attributes it could lead to Tango timeouts.

To avoid that, use the Mappings property. It will automatically refresh the values periodically and reevaluate the contents of the related attributes::

  Mappings:

    ARRAY=0,+240

In case you have many memory areas to update at different rates, an additional period time can be added to force slower updates of the mapping::

    SLOW_ARRAY=3000,+240,/60 #Updated only every 60 seconds


DynamicCommands
---------------

For example, having a variable that toggles value when 1 is written, we can use 2 commands to do set() and clear()

Given this DynamicAttributes formula::

  ValueToToggle = DevBoolean(READ and Bit(DigitalsREAD[20],7) or WRITE and WriteFlag(21,7,VALUE))

We can convert it to 2 DynamicCommands::

  CmdDisableValue = str( not Bit(DigitalsREAD[20],7) and WriteFlag(21,7,1) )
  CmdEnableValue = str( Bit(DigitalsREAD[20],7) and WriteFlag(21,7,1) )

Si lo prefieres puedes usar esta sintaxis::

  CmdDisableValuep = str( WriteFlag(21,7,1) if not Bit(DigitalsREAD[20],7) else 'already disabled' )
  CmdEnableValue = str( WriteFlag(21,7,1) if Bit(DigitalsREAD[20],7) else 'already enabled' )
