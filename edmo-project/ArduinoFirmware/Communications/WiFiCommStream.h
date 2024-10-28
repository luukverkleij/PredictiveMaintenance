#pragma once

#include "../globals.h"
#include <WiFi101.h>
#include <WiFiUdp.h>

#include "ICommStream.h"

#if WIFI_SUPPORT == 1
class WiFiCommStream : public virtual ICommStream
{
private:
    WiFiUDP udp{};
    IPAddress remoteIP;
    uint16_t remotePort;

public:
    void init() override
    {
        WiFi.setPins(8, 7, 4, 2);
        WiFi.hostname(hostname.c_str());
        WiFi.begin(ssid, pass);

        udp.begin(2121);
    }

    void write(const uint8_t *const data, size_t length) override
    {
        udp.write(data, length);
    }

    void write(uint8_t byte) override
    {
        udp.write(byte);
    }

    void begin() override
    {
        udp.beginPacket(remoteIP, remotePort);
    }

    void end() override
    {
        udp.endPacket();
    }

    void update() override
    {
        int packetSize = udp.parsePacket();

        if (packetSize == 0)
            return;

        remoteIP = udp.remoteIP();
        remotePort = udp.remotePort();

        char packetBuffer[packetSize];

        int length = udp.read(packetBuffer, packetSize);

        if (!buffcmp(packetBuffer, commHeader, 2) || !buffcmp(packetBuffer + length - 2, commFooter, 2))
            return;

        parsePacket(packetBuffer, packetSize, this);
    }
};
#else
// A dummied out version of WiFiCommStream
class WiFiCommStream : public virtual ICommStream
{
public:
    void init() override
    {
    }

    void write(const uint8_t *data, size_t length)
    {
    }
    
    void write(const uint8_t byte)
    {
    }

    void write(const char *const data, size_t length) override
    {
    }

    void update() override
    {
    }

    void begin() override
    {
    }

    void end() override
    {
    }
};
#endif

WiFiCommStream WifiComms;