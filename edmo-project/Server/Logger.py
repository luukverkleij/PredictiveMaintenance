from datetime import datetime
import aiofiles
import os
import pandas as pd
import warnings

from time import perf_counter

#TODO Turn into pandas logger


class SessionLogger:
    def __init__(self, name: str):
        self.name = name
        self.dfs = dict[str, pd.DataFrame()]()
        #self.channels = dict[str, [str]]()
        self.sessionStartTime = perf_counter()
        self.lastFlushTime = self.sessionStartTime
        path = self.directoryName = f'./SessionLogs/{datetime.now().strftime(f"%Y.%m.%d/{self.name}/%H.%M.%S")}'

        if not os.path.exists(path):
            os.makedirs(path)

    def create(self, channel: str, columns:list[str]):
        #print(f"Created channel {channel} with columns {columns}")
        self.dfs[channel] = pd.DataFrame(columns=columns)
        self.dfs[channel].to_csv(f"{self.directoryName}/{channel}.csv", mode="a", index=False)


    def write(self, channel: str, msg: list[str], time=None):
        if channel not in self.dfs:
            raise ValueError(f"{channel} not yet created! Available channels: \n {self.dfs.keys()}")
        
        #
        df = self.dfs[channel]
        
        if len(msg) != len(df.columns) - 1:
            raise ValueError(f"message has {len(msg)} entries, expected {len(df.columns) - 1}")
        
        #Adding datetime to from of the message
        if not time:
            time = perf_counter() - self.sessionStartTime
        msg = [time] + msg

        #Create a row in dict form
        row = {}
        for colname, value in zip(df.columns, msg):
            row[colname] = value

        self.dfs[channel].loc[len(df)] = row

    def writes(self, channel: str, msgs: list[list[str]], time=None):
        #print(msgs)

        if channel not in self.dfs:
            raise ValueError(f"{channel} not yet created! Available channels: \n {self.dfs.keys()}")
        
        #Adding datetime to from of the message
        if not time:
            time = perf_counter() - self.sessionStartTime
        msgs = [[time] + msg for msg in msgs]

        #Create a row in dict form
        rows = {}
        for colname, values in zip(self.dfs[channel].columns, [list(i) for i in zip(*msgs)]):
            rows[colname] = values

        self.dfs[channel] = pd.concat([self.dfs[channel], pd.DataFrame(rows)])
        
    async def flush(self):
        for key in list(self.dfs.keys()):
            #Select the dataframe
            df = self.dfs[key]

            #Save the dataframe to a file
            df.to_csv(f"{self.directoryName}/{key}.csv", mode="a", header=False, index=False)

            # Clear the dataframe
            self.dfs[key] = self.dfs[key][0:0]

