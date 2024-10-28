#pragma once
#include <Arduino.h>
#include <cstddef>

class TimingUtils
{
    static size_t referenceTimeStamp;
    static size_t offsetTime;

public:
    static size_t getTimeMillis();

    static void setReferenceTime(size_t time);

    static void setOffsetTime(size_t time);
};