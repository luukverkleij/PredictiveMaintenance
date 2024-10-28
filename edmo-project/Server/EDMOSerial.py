import asyncio
from typing import Callable, Optional, cast
import serial_asyncio
from serial.tools.list_ports_common import ListPortInfo
from serial.tools.list_ports import comports
from serial_asyncio import SerialTransport
from typing import Self

from EDMOCommands import EDMOCommand, EDMOCommands, EDMOPacket


class SerialProtocol(asyncio.Protocol):
    def __init__(self):
        self.connectionCallbacks = list[Callable[[Self], None]]()
        self.disconnectCallbacks = list[Callable[[Self], None]]()
        self.identifying = True
        self.receivedData = list[bytes]()
        self.identifier = ""
        self.closed = False
        self.device = ""
        
        self.receivingData = False
        self.receiveBuffer = bytearray()

        self.onMessageReceived: Optional[Callable[[EDMOCommand], None]] = None

    def connection_made(self, transport: SerialTransport):  # type: ignore
        self.transport = transport

        # Send out the identification command
        transport.write(EDMOPacket.create(EDMOCommands.IDENTIFY))

        print("port opened: ", transport)

    def deviceIdentified(self):
        for callback in self.connectionCallbacks:
            callback(self)

    def data_received(self, data):
        for i in range(0, len(data)):
            self.receiveBuffer.append(data[i])

            # Do we have a header?
            if len(self.receiveBuffer) >= 2 and self.receiveBuffer.endswith(EDMOPacket.HEADER):
                self.receiveBuffer = self.receiveBuffer[:2]
                self.receivingData = True

            # If we aren't actively receiving data, then we actually don't have to do anything with the data that comes in
            if not self.receivingData:
                # Make discard every two bytes to ensure we don't overflow the buffer
                # (We need at least two bytes to determine if a header is received)
                if len(self.receiveBuffer) >= 2:
                    self.receiveBuffer = bytearray()
                continue

            # As long as we haven't received the data, we will not proceed with parsing
            if not self.receiveBuffer.endswith(EDMOPacket.FOOTER):
                continue

            # Data transmission successful at this point
            # Relinquish control to packet handler
            self.receivingData = False

            self.handlePacket(bytes(self.receiveBuffer))
            self.receiveBuffer = bytearray()

    def handlePacket(self, data: bytes):
        command = EDMOPacket.tryParse(data)

        if self.identifying:
            if command.Instruction == EDMOCommands.IDENTIFY:
                self.identifier = command.Data.decode()
                self.identifying = False
                self.deviceIdentified()
            return

        if self.onMessageReceived is not None:
            self.onMessageReceived(command)

    def connection_lost(self, exc):
        print("port closed")
        self.closed = True
        # Identification never occured in time
        # We don't need to inform subscribers
        if self.identifier == "":
            return

        for callback in self.disconnectCallbacks:
            callback(self)

    def pause_writing(self):
        print("pause writing")

    def resume_writing(self):
        print("resume writing")

    def pause_reading(self):
        print("Reading paused")
        self.transport.pause_reading()

    def resume_reading(self):
        self.transport.resume_reading()
        print("reading resumed")

    def write(self, data: bytes):
        if self.closed:
            return

        self.transport.write(data)

    def close(self):
        self.closed = True
        self.transport.serial.close()  # type: ignore


class EDMOSerial:
    devices: dict[str, SerialProtocol] = {}

    onConnect: list[Callable[[SerialProtocol], None]] = []
    onDisconnect: list[Callable[[SerialProtocol], None]] = []

    def __init__(self):
        pass

    async def update(self):
        await self.searchForConnections()

    async def searchForConnections(self):
        ports: list[ListPortInfo] = comports(True)  # type: ignore

        connectionTasks = []

        for port in ports:
            # We only care about M0's at the moment
            # This can be expanded if we ever use other boards
            #if port.description == "Feather M0":
            connectionTasks.append(
                    asyncio.create_task(self.initializeConnection(port))
                )

        if len(connectionTasks) > 0:
            await asyncio.wait(connectionTasks)

    async def initializeConnection(self, port: ListPortInfo):
        # This device is still being used, we don't need to init
        if port.device in self.devices:
            return

        # This creates a serial connection for the port
        # The port will run asynchorously in the background
        # SerialProtocol contains the general management code
        loop = asyncio.get_event_loop()
        _, protocol = await serial_asyncio.create_serial_connection(
            loop, SerialProtocol, port.device, baudrate=115200
        )

        # For typing purposes, no actual effect
        serialProtocol = cast(SerialProtocol, protocol)

        # We need to keep track of the device used
        #  so we don't create a new connection later
        serialProtocol.device = port.device
        self.devices[port.device] = serialProtocol

        serialProtocol.disconnectCallbacks.append(self.onConnectionLost)
        serialProtocol.connectionCallbacks.append(self.onConnectionEstablished)

    def onConnectionEstablished(self, protocol: SerialProtocol):
        # Notify subscribers of the change
        for callback in self.onConnect:
            callback(protocol)

    def onConnectionLost(self, protocol: SerialProtocol):
        # We remove the device from the list
        del self.devices[protocol.device]

        # Notify subscribers of the change
        for callback in self.onDisconnect:
            callback(protocol)

    def close(self):
        devices = self.devices.copy()
        for device in devices:
            devices[device].close()
