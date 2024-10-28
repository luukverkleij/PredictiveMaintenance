# Handles everything

import asyncio
import aioconsole
from aiohttp import web
from aiohttp.web_middlewares import normalize_path_middleware
from aiohttp_middlewares import cors_middleware  # type: ignore
from FusedCommunication import FusedCommunication, FusedCommunicationProtocol
from aiortc.contrib.signaling import object_from_string, object_to_string
from aiortc import RTCSessionDescription

from WebRTCPeer import WebRTCPeer
import traceback

from EDMOSession import EDMOSession
from EDMOProgram import EDMOProgram, EDMOMotorProgram

from time import perf_counter, sleep
from datetime import datetime
import numpy as np

# flake8: noqa: F811
class EDMOBackend:
    def __init__(self):
        self.activeEDMOs: dict[str, FusedCommunicationProtocol] = {}
        self.activeSessions: dict[str, EDMOSession] = {}

        self.fusedCommunication = FusedCommunication()
        self.fusedCommunication.onEdmoConnected.append(self.onEDMOConnected)
        self.fusedCommunication.onEdmoDisconnected.append(self.onEDMODisconnect)

        self.simpleViewEnabled = False

        #temp
        self.closed = False

        #aioconsole
        self.consoleOn = True

        self.mainSession = None

        self.updateHz = 40

        self.lastUpdate = perf_counter()

        #counter
        self.counter = 0
        self.countertime = perf_counter()

    # region EDMO MANAGEMENT

    def onEDMOConnected(self, protocol: FusedCommunicationProtocol):
        # Assumption: protocol is non null
        identifier = protocol.identifier
        self.activeEDMOs[identifier] = protocol
        
        # Luuk - adding
        print("Edmo " + identifier + " connected") 
        self.activeSessions[identifier] = EDMOSession(
            protocol, 3, self.removeSession
        )

        # self.activeSessions[identifier].updateMotor(0, "amp 0")
        # self.activeSessions[identifier].updateMotor(0, "freq 0.05")

    def onEDMODisconnect(self, protocol: FusedCommunicationProtocol):
        # Assumption: protocol is non null
        identifier = protocol.identifier
        print("Edmo " + identifier + " disconnected")

        # Remove session from candidates
        if identifier in self.activeEDMOs:
            del self.activeEDMOs[identifier]

    # endregion

    # region SESSION MANAGEMENT

    def getEDMOSession(self, identifier):
        if identifier in self.activeSessions:
            return self.activeSessions[identifier]

        if identifier not in self.activeEDMOs:
            return None

        protocol = self.activeEDMOs[identifier]
        session = self.activeSessions[identifier] = EDMOSession(
            protocol, 4, self.removeSession
        )

        session.setSimpleView(self.simpleViewEnabled)

        return session

    def removeSession(self, session: EDMOSession):
        identifier = session.protocol.identifier
        if identifier in self.activeSessions:
            del self.activeSessions[identifier]

    # endregion

    async def onPlayerConnect(self, request: web.Request):
        """Attempts to handle a connecting player. Will establish a Websocket response if valid attempt."""
        """Otherwise it'll return 404 or 401 depending on what is wrong"""
        identifier = request.match_info["identifier"]

        if identifier not in self.activeEDMOs:
            return web.Response(status=404)

        ws = web.WebSocketResponse()
        await ws.prepare(request)

        async for msg in ws:
            if msg.type != web.WSMsgType.TEXT:
                continue

            data = msg.json()

            username = data["playerName"]
            sessionDescription = object_from_string(data["handshake"])

            if isinstance(sessionDescription, RTCSessionDescription):
                player = WebRTCPeer(request.remote)

                session = self.getEDMOSession(identifier)

                if session is not None:
                    if not session.registerPlayer(player, username):
                        return web.Response(status=401)

                answer = await player.initiateConnection(sessionDescription)

                await ws.send_str(object_to_string(answer))

        return ws
    
    async def update(self):
        # Get the current time
        start_time = perf_counter()

        """Standard update loop to be performed at most updateHz times a second"""
       # Update the serial stuff
        serialUpdateTask = self.fusedCommunication.update()

        # Update all sessions
        sessionUpdates = [self.activeSessions[sessionID].update() for sessionID in self.activeSessions]

        # Gather all tasks and wait for them to complete
        await asyncio.gather(serialUpdateTask, *sessionUpdates)

        # Measure the total execution time
        execution_time = perf_counter() - start_time

        # Calculate the time remaining to sleep
        sleeptime = max(0, (1/self.updateHz) - execution_time)
        sleep(sleeptime)

        # Update the last update time
        self.lastUpdate = perf_counter()

        # Counter for how many loops
        # self.counter += 1
        # if (perf_counter() - self.countertime) > 1:
        #     print(f'Hz: {self.counter}')
        #     self.counter = 0
        #     self.countertime = perf_counter()


    # async def update(self):

    #     # Make sure we are not too fast
    #     deltatime = perf_counter() - self.lastUpdate
    #     #print((1/self.updateHz) - deltatime.total_seconds())
    #     sleeptime = np.max([0, (1/self.updateHz) - deltatime])
    #     #print(f"Sleeping {sleeptime} seconds")
        
    #     await asyncio.sleep(sleeptime)
        

    #     """Standard update loop to be performed at most updateHz times a second"""
    #     self.lastUpdate = perf_counter()

    #     # Update the serial stuff
    #     serialUpdateTask = asyncio.create_task(self.fusedCommunication.update())

    #     # Update all sessions
    #     sessionUpdates = []

    #     for sessionID in self.activeSessions:
    #         session = self.activeSessions[sessionID]
    #         sessionUpdates.append(asyncio.create_task(session.update()))

    #     await serialUpdateTask
    #     if len(sessionUpdates) > 0:
    #         await asyncio.wait(sessionUpdates)

    #     #Counter for how many loops
    #     self.counter += 1
    #     if (perf_counter() - self.countertime) > 1:
    #         print(f'Hz: {self.counter}')
    #         self.counter = 0
    #         self.countertime = perf_counter()

        



    async def run(self) -> None:
        asyncio.get_event_loop().create_task(self.console())

        await self.fusedCommunication.initialize()

        try:
            while not self.closed:
                await self.update()
        except (asyncio.exceptions.CancelledError, KeyboardInterrupt):
            pass
        finally:
            await self.onShutdown()

    async def onShutdown(self):
        """Shuts down existing connections gracefully to prevent a minor deadlock when shutting down the server"""
        self.consoleOn = False
        self.fusedCommunication.close()
        for s in [sess for sess in self.activeSessions]:
            session = self.activeSessions[s]
            await session.close()
        pass

    async def console(self):
        while self.consoleOn:
            [response] = await asyncio.gather(
                aioconsole.ainput(),
            )
            session = next(iter(self.activeSessions.values()))
            try:
                match response:
                    case "sessions":
                        print(self.activeSessions)

                    case "getHz":
                        print(self.updateHz)

                    case "kill":
                        self.closed=True

                    case "startlog":
                        session.startLog()

                    case "stoplog":
                        await session.stopLog()

                    case s if s.startswith("start "):
                        prg = EDMOProgram(session)
                        await prg.run(s.split()[1], int(s.split()[2]))

                    case s if s.startswith("run "):
                        mtrprg = EDMOMotorProgram(int(s.split()[1]), session)
                        await mtrprg.run()

                    case "stop":
                        for motor in session.motors:
                            motor.adjustFrom(0, "freq 0")

                    case "reset":
                        for motor in session.motors:
                            motor.adjustFrom("amp 0")
                            motor.adjustFrom("freq 0")

                    case s if s.startswith(("freq ", "off ", "amp", "phb ", "rev", "ord")):
                        strs = s.split()
                        session.updateMotor(int(strs[2]), strs[0] + " " + strs[1])

                    case _:
                        print(response, " is not a command")

            except Exception:
                traceback.print_exc()



            
            
