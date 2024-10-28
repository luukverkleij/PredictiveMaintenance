
#include "globals.h"
#include <Adafruit_PWMServoDriver.h>
#include <Wire.h>
#include <cstring>
#include "Oscillator.h"
#include "IMUSensor.h"

#include "Communications/PacketUtils.h"
#include "Communications/WiFiCommStream.h"
#include "Communications/SerialCommStream.h"

#include "TimingUtils.h"

// Timing variables
unsigned long lastTime = 0;
unsigned long timeStep = 10; // period used to update CPG state variables and servo motor control (do NOT modify!!)

const float MS_TO_S = 1.0f / 1000.0f;

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

bool pwmPresent = false;

void setup()
{
    SerialComms.init();
    SerialComms.bindPacketHandler(packetHandler);

    #if WIFI_SUPPORT == 1
      WifiComms.init();
      WifiComms.bindPacketHandler(packetHandler);
    #endif

    imu.init();

    pwmPresent = pwm.begin();

    if (pwmPresent)
    {
        pwm.setPWMFreq(50);
        delay(4);

        for (Oscillator &o : oscillators)
            o.setPWM(pwm);
    }
    pinMode(LED_BUILTIN, OUTPUT);
    analogWrite(LED_BUILTIN, 0);

    //TEMP - Make sure all oscillators are set to move slowly.
    /*OscillatorParams param;
    param.amp = 90;
    param.freq = 0.1;
    for (auto osc : oscillators)
      oscillators[0].setParams(param);
    */
    //TEMP - Making sure time is set right
    lastTime = millis();
}

uint8_t ledState = 0;
bool reversing = true;

void ledControl()
{
    const uint8_t fadeSpeed = 4;

    uint8_t newLedState = ledState + (reversing ? -fadeSpeed : fadeSpeed);

    if (newLedState == 0)
    {
        reversing = !reversing;
        return;
    }
    ledState = newLedState;

    analogWrite(LED_BUILTIN, ledState);
}

void loop()
{
    // Used as a visual indicator of functionality
    ledControl();

    // Reading input can happen regardless of whether CPG updates
    // This ensures that we don't waste time doing nothing and will maximize responsiveness
    SerialComms.update();
    #if WIFI_SUPPORT == 1
      WifiComms.update();
    #endif
    imu.update();

    unsigned long time = millis();
    unsigned long deltaTimeMS = time - lastTime;

    lastTime = time; // update the previous time step (do NOT modify!!)

    // Forcing deltaTimeS to be a max value to avoid jittering
    if(deltaTimeMS > 50)
      deltaTimeMS = 50;

    for (auto &oscillator : oscillators)
        oscillator.update(deltaTimeMS * MS_TO_S);

}

enum PacketInstructions
{
    IDENTIFY = 0,
    SESSION_START = 1,
    GET_TIME = 2,

    UPDATE_OSCILLATOR = 3,
    SEND_MOTOR_DATA = 4,
    SEND_IMU_DATA = 5,
};

// Takes parses a received packet, which contain an instruction and optionally additional data
// This method may write a response via the provided ICommStream pointer
// This method returns true if a response is written, false otherwise.
//
// Any invalid instruction is dropped silently
void packetHandler(char *packet, size_t packetSize, ICommStream *commStream)
{
    // Length of the packet without the header/footer
    size_t packetLength = packetSize - 4;

    // Packet without header
    char *packetBuffer = packet + 2;

    // Unescape packet contents in place
    unescapeBuffer(packetBuffer, packetLength);

    // The first byte of the packet contents is expected to be the instruction
    char &packetInstruction = packetBuffer[0];

    // The rest of the packet contain data/arguments associated with the instruction
    // The length of the data is always fixed based on the called instruction
    char *packetData = packetBuffer + 1;

    switch (packetInstruction)
    {
    // Simply announce the robots name
    // Also used during Wifi communication to indicate presence on the network (aka pinging)
    case IDENTIFY:
    {
        commStream->begin();
        commStream->write(commHeader, 2);
        commStream->write(IDENTIFY); // Write the instruction as a response
        commStream->write((uint8_t *)idCode.c_str(), idCode.length());
        commStream->write(commFooter, 2);
        commStream->end();
        break;
    }

    // The host has declared that a session has started/continued
    // This is required in order to align the IMU timestamps with the session timestamp
    // A manual time offset is provided as packet data,
    //    this is used to realign the timestamp if the device is reset while a session is active
    //    (otherwise the restarted device will report back with timestamp 0, causing serverside logging to be non-linear)
    case SESSION_START:
    {
        // Make sure all oscillators are reset to initial state
        for (auto osc : oscillators)
            osc.reset();

        auto currentTime = millis();

        TimingUtils::setReferenceTime(currentTime);

        size_t offsetTime{};
        std::memcpy(&offsetTime, packetData, sizeof(size_t));

        TimingUtils::setOffsetTime(offsetTime);
        break;
    }

    // Provides the current time based on the reference timestamp, used by the server to keep track of the last known arduino time
    //  (Probably could compute it themselves tbh)
    // The sent data is escaped as it may contain the header/footer bytes due to the variable nature of the time
    case GET_TIME:
    {
        auto returnedTime = TimingUtils::getTimeMillis();
        auto dataBytes = reinterpret_cast<const char *>(&returnedTime);

        // These data bytes may accidentally contain the header or footer, let's escape it to be safe
        size_t adjustedLength = countEscapedLength(dataBytes, 4);
        char escapedData[adjustedLength];

        escapeData(dataBytes, escapedData, adjustedLength);

        commStream->begin();
        commStream->write(commHeader, 2);
        commStream->write(GET_TIME);
        commStream->write(escapedData, adjustedLength);
        commStream->write(commFooter, 2);
        commStream->end();
        break;
    }

    // The host is sending updated oscillator parameters
    // The packet data contains 2 arguments, the first byte is the target oscillator
    // The rest of the packet data is the oscillator parameters
    case UPDATE_OSCILLATOR:
    {
        uint8_t targetOscillator = packetData[0];
        OscillatorParams updateCommand{};

        std::memcpy(&updateCommand, packetData + 1, sizeof(OscillatorParams));
        oscillators[targetOscillator].setParams(updateCommand);

        break;
    }

    /*case UPDATE_NEXTANGLE:
    {
        uint8_t targetOscillator = packetData[0];
        float angle

        std::memcpy(&angle, packetData + 1, sizeof(float));
        oscillators[targetOscillator].addNextAngle(angle)

        break;
    }*/

    // The host is requesting the current oscillator states (not to be confused with the oscillator params)
    // The sent data is escaped as it may contain the header/footer bytes due to the variable nature of the the state variables
    case SEND_MOTOR_DATA:
    {
        for (auto &osc : oscillators)
        {
            osc.updateOutput();

            auto &data = osc.getState();

            const char *bytes = reinterpret_cast<const char *>(&data);

            size_t escapedLength = countEscapedLength(bytes, sizeof(OscillatorState));

            char escapedBuffer[escapedLength];

            escapeData(bytes, escapedBuffer, sizeof(OscillatorState));

            commStream->begin();
            commStream->write(commHeader, 2);
            commStream->write(SEND_MOTOR_DATA);
            commStream->write(osc.id);
            commStream->write(escapedBuffer, escapedLength);
            commStream->write(commFooter, 2);
            commStream->end();
        }

        break;
    }

    // The host is requesting current IMU sensor data
    // The sent data is escaped as it may contain the header/footer bytes due to the variable nature of the the IMU variables
    case SEND_IMU_DATA:
    {
        commStream->begin();
        commStream->write(commHeader, 2);
        commStream->write(SEND_IMU_DATA);
        imu.printTo(commStream);
        commStream->write(commFooter, 2);
        commStream->end();
        break;
    }

    }
}
