import asyncio
import EDMOSession
from EDMOMotor import EDMOMotorState

from datetime import datetime, timedelta
from time import sleep

class EDMOProgram:
    def __init__(self, session : EDMOSession):
        self.session = session

    async def run(self, anomaly="?", num=1):

        print(f"Starting the run {anomaly}, running {num} times. Estimated finished time is "\
              f"{(datetime.now() + timedelta(seconds=91 * num)).strftime('%Y-%m-%d %H:%M:%S')}")

        for x in range(num):
            #Start Logging
            self.session.startLog()
            self.session.reset()

            sleep(0.1)

            self.session.sessionLog.write("program", [anomaly, "run0"])

            # Start & wait for motor run 0
            mtrprg0 = EDMOMotorProgram(0, self.session)
            await mtrprg0.run()    
        
            self.session.sessionLog.write("program", [anomaly, "run1"])

            # Start & wait for motor run 1
            mtrprg1 = EDMOMotorProgram(1, self.session)
            await mtrprg1.run()

            self.session.sessionLog.write("program", [anomaly, "run2"])

            # Start & wait for motor run 2
            mtrprg2 = EDMOMotorProgram(2, self.session)
            await mtrprg2.run()

            self.session.sessionLog.write("program", [anomaly, "run012"])

            await asyncio.gather(mtrprg0.setup().run(), mtrprg1.setup().run(), mtrprg2.setup().run())

            #Stop Logging
            await self.session.stopLog()

             #Printing information
            if (num-x-1) > 0:
                totalsecs = (num-x-1)*91
                td = timedelta(seconds=totalsecs)
                print(f'Run {x+1} done, {(num-x-1)} left, estimated time left {str(td) if totalsecs >= 3600 else str(td)[2:]}')

            sleep(2)

           
        print(f"start {anomaly} {num} has finished")



class EDMOMotorProgram:
    def __init__(self, mid : int, session : EDMOSession):
        self.mid = mid
        self.session = session

        self.setup()

    def setup(self):
        self.zeropass = [False, False]
        self.endpass = [False, False]
        self.reverse = None
        self.flag = asyncio.Event()

        return self

    async def run(self, freq=0.05, amp=90, reset=False, sleep=2):

        #Adding Callback
        self.session.onMotorUpdate[self.mid] = self.onMotorUpdate

        #print(f"Start running motor {self.mid}")
        # Start Motor
        self.session.updateMotor(self.mid, f"freq {freq}")
        self.session.updateMotor(self.mid, f"amp {amp}")

        #print("Waiting for motor to the 0 points")

        # Wait for all(self.zeropass) to be true.
        await self.flag.wait()

        #print(f"Motor {self.mid} is done, sending stop")

        # Stop Motor
        self.session.updateMotor(self.mid, "freq 0")
        self.session.updateMotor(self.mid, "amp 0")

        await asyncio.sleep(sleep)

        #Removing Callback
        del self.session.onMotorUpdate[self.mid]
    
    async def onMotorUpdate(self, mid, s1 : EDMOMotorState, s2 : EDMOMotorState):
        a1 = s1.getAngle()
        a2 = s2.getAngle()

        if mid != self.mid or a1 == a2:
            return
        
        if self.reverse == None:
            self.reverse = a1 < a2

        if self.reverse != (a1 < a2):
            self.reverse = (a1 < a2)
            if(a1 >= 80):
                #print(f"Motor {self.mid} reached end+")
                self.endpass[0] = True
            elif a1 <= -80:
                #print(f"Motor {self.mid} reached end-")
                self.endpass[1] = True

        if ((s1.getAngle() <= 0 and s2.getAngle() >= 0) or (s1.getAngle() >= 0 and s2.getAngle() <= 0)) \
            and all(self.endpass):
            self.flag.set()
            
        