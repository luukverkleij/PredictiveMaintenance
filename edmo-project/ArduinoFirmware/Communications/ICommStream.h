#pragma once

#include <functional>
#include "PacketUtils.h"

class ICommStream
{
public:
    virtual void init() = 0;
    virtual void update() = 0;
    virtual void write(const uint8_t *constdata, size_t length) = 0;
    virtual void write(uint8_t byte) = 0;
    virtual void write(const char *const data, size_t length)
    {
        this->write((uint8_t *)data, length);
    }

    virtual void begin() = 0;
    virtual void end() = 0;

    using PacketHandler = std::function<void(char *, size_t, ICommStream *)>;

    PacketHandler handler;
    bool packetHandlerBound;

    void bindPacketHandler(PacketHandler handler)
    {
        ICommStream::handler = handler;
        packetHandlerBound = true;
    }

protected:
    void parsePacket(char *packet, size_t length, ICommStream *commStream)
    {
        if (!packetHandlerBound)
            return;

        handler(packet, length, commStream);
    }
};