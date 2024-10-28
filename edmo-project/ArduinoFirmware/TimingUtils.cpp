#include "TimingUtils.h"

size_t TimingUtils::referenceTimeStamp{};
size_t TimingUtils::offsetTime{};

size_t TimingUtils::getTimeMillis()
{
    return millis() - referenceTimeStamp + offsetTime;
}

void TimingUtils::setReferenceTime(size_t time)
{
    referenceTimeStamp = time;
    offsetTime = 0;
}

void TimingUtils::setOffsetTime(size_t t)
{
    offsetTime = t;
}