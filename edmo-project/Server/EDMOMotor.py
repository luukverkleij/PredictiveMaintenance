import struct
from EDMOCommands import EDMOCommands, EDMOPacket

import math

class EDMOMotorState:
    def __init__(self, freq=0, amp=0, offset=90, phaseshift=0, phase=0, reverse=False, orders=False, output=-1):
        self.amp:float = amp
        self.offset:float = offset
        self.freq:float = freq
        self.phaseshift:float = phaseshift
        self.phase:float = phase
        self.reverse:bool = reverse
        self.orders:bool = orders
        self.output:int = output


    def __str__(self):
        return f"Angle: {self.getAngle()}, Frequency: {self.freq}, Amplitude: {self.amp}, Offset: {self.offset}, " \
                f"Phase Shift: {self.phaseshift}, Phase: {self.phase}, Reverse: {self.reverse}, Orders: {self.orders}"
    
    def tocsv(self):
        return f"{self.getAngle()}, {self.freq}, {self.amp}, {self.offset}, {self.phaseshift}, {self.phase}, {self.output}"
    
    def tolist(self):
        return [self.getAngle(), self.freq, self.amp, self.offset, self.phaseshift, self.phase, self.output]
    
    def getAngle(self):
        return (self.amp * (-1 if self.reverse else 1)) * math.sin(self.phase - self.phaseshift)

    def toPos(self, min=100, max=454):
        return self._mapr(self._constrain(self.getAngle() + self.offset, 0, 180), 0, 180, min, max)

    def _mapr(self, x, in_min, in_max, out_min, out_max):
        return (x - in_min) * (out_max - out_min) // (in_max - in_min) + out_min

    def _constrain(self, val, min_val, max_val):
        return min(max_val, max(min_val, val))

class EDMOMotor:
    def __init__(self, id: int) -> None:
        self._params = EDMOMotorState()
        self._id = id
        self.changed = True
        pass

    def adjustFrom(self, input: str):
        """Takes an input str, and adjusts the parameters of the associated motor"""
        splits = input.split(" ")
        command = splits[0].lower()
        value = float(splits[1])

        match (command):
            case "amp":
                #print("Amplitude set to ", value)
                self._params.amp = value
            case "off":
                self._params.offset = value
            case "freq":
                #print("Frequency set to ", value)
                self._params.freq = value
            case "phb":
                self._params.phaseshift = value
            case "rev":
                self._params.reverse = bool(value)
            case "ord":
                self._params.orders = bool(value)
            case _:
                pass

        self.changed = True

    @property
    def motorNumber(self):
        return self._id

    def __str__(self):
        return f"EDMOMotor(id={self._id}, "  + self._params.__str__()

    def asCommand(self):
        command = struct.pack(
            "<Bffffhh",
            self._id,
            self._params.freq,
            self._params.amp,
            self._params.offset,
            self._params.phaseshift,
            self._params.reverse,
            self._params.orders,
        )

        return EDMOPacket.create(EDMOCommands.UPDATE_OSCILLATOR, command)
