#pragma once
#include "../globals.h"

// Compare both buffers
static bool buffcmp(const char *const buffer, const char *const other, size_t length)
{
    for (int i = 0; i < length; ++i)
    {
        if (buffer[i] != other[i])
            return false;
    }

    return true;
}

static bool isCommHeader(const char *buffer)
{
    return buffcmp(buffer, commHeader, 2);
}

static bool isCommFooter(const char *buffer)
{
    return buffcmp(buffer, commFooter, 2);
}

// Count the size of the buffer needed to hold the data buffer with escape characters
static size_t countEscapedLength(const char *const buffer, size_t length)
{
    size_t countOccurances = 0;

    for (int i = 0; i < length; ++i)
    {
        if (buffer[i] == '\\')
            ++countOccurances;

        if ((i < length - 1) && (isCommHeader(&buffer[i]) || isCommFooter(&buffer[i])))
            ++countOccurances;
    }

    return length + countOccurances;
}

// In place removal of escape characters
static size_t unescapeBuffer(char *const buffer, size_t length)
{
    size_t j = 0; // The length of the buffer with all escape characters removed
    for (size_t i = 0; i < length; ++i)
    {
        if (buffer[i] == '\\') // Ignore any escape characters
            ++i;               // And take the next character immediately

        // string ends in an escape character, but there are no characters after
        if (i >= length)
            break;

        buffer[j] = buffer[i];
        ++j;
    }

    return j;
}

static void escapeData(const char *const originalBuffer, char *const outputBuffer, size_t originalLength)
{
    size_t j = 0;
    for (size_t i = 0; i < originalLength; ++i)
    {
        outputBuffer[j++] = originalBuffer[i];

        if (originalBuffer[i] == '\\')
            outputBuffer[j++] = '\\';

        if ((i < originalLength - 1) && (isCommHeader(&originalBuffer[i]) || isCommFooter(&originalBuffer[i])))
            outputBuffer[j++] = '\\';
    }
}
