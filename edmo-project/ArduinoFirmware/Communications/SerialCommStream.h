#pragma once
#include "ICommStream.h"

class SerialCommStream : virtual public ICommStream
{
private:
    char dataBuffer[512];
    size_t dataBufferLength = 0;

    bool receivingData = false;

public:
    void init() override
    {
        Serial.begin(115200);
    }

    void write(const uint8_t *const data, size_t length) override
    {
        Serial.write(data, length);
    }

    void write(uint8_t byte) override
    {
        write(&byte, 1);
    }

    void begin() override 
    {
    }

    void end() override
    {
    }

    void update() override
    {
        if (!Serial)
            return;

        // Read data if there is anything on the line
        // But we only take at most 1024 bytes at any time to not stall other items on the loop
        //   The excess data will be handled during the next update cycle
        for (int i = 0; i < 1024 && Serial.available(); ++i)
        {
            dataBuffer[dataBufferLength++] = Serial.read();

            auto dataBufferEnd = dataBuffer + dataBufferLength;

            // The communication header signals the start of a input/command packet, and we will store future bytes into a buffer for parsing
            //
            // Note that there we are checking for the header, even if the previous packet isn't complete yet
            // This is so that if ever a packet is interrupted, and a footer never arrives
            //    the header of the next message will guarantee that the system recovers from the interrupted packet
            //
            // If the header is part of the data transmitted, it should be escaped using forward slashes
            // i.e "EDMO" -> "\E\D\M\O" or "E\DM\O" (All you have to ensure is that ED and MO isn't adjacent)
            if (dataBufferLength >= 2 && isCommHeader(dataBufferEnd - 2))
            {
                receivingData = true;

                // We keep the first two bytes as it is already "ED"
                dataBufferLength = 2;
                continue;
            }

            // If we aren't actively receiving data, then we actually don't have to do anything with the data that comes in
            if (!receivingData)
            {
                // Make discard every two bytes to ensure we don't overflow the buffer
                // (We need at least two bytes to determine if a header is received)
                if (dataBufferLength > 2)
                    dataBufferLength = 0;
                continue;
            }

            // As long as we haven't received the data, we will not proceed with parsing
            if (!isCommFooter(dataBufferEnd - 2))
            {
                // SPECIAL CASE: Buffer overflow - Packet too large, we drop the transmission
                if (dataBufferLength == 512)
                {
                    receivingData = false;
                    dataBufferLength = 0;
                }
                continue;
            }

            // Data transmission successful at this point
            // Relinquish control to packet handler
            receivingData = false;

            parsePacket(dataBuffer, dataBufferLength, this);
            dataBufferLength = 0;
        }
    }
};

SerialCommStream SerialComms{};