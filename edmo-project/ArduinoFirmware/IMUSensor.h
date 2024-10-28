#pragma once

#include <Adafruit_BNO08x.h>
#include <cstddef>
#include <array>
#include "Communications/ICommStream.h"
#include "DebugUtils.h"

#include "TimingUtils.h"

#if IMU_SPI == 1
#define BNO08X_CS 10
#define BNO08X_INT 9
#define BNO08X_RESET 5
#else
#define BNO08X_RESET -1
#endif

template <typename T>
struct SensorInfo
{
    uint32_t timestamp;
    uint8_t accuracy;
    // There is 3 padding bytes here

    T value;
};

typedef struct vec3
{
    vec3()
    {
        x = y = z = 0;
    }

    // Conversion template for similar looking structs
    template <typename T>
    vec3(const T &t)
    {
        x = t.x;
        y = t.y;
        z = t.z;
    }

    float x, y, z;
} vec3;

typedef struct quarternion
{
    quarternion()
    {
        i = j = k = real = 0;
    }

    // Conversion template for similar looking structs
    template <typename T>
    quarternion(const T &t)
    {
        i = t.i;
        j = t.j;
        k = t.k;
        real = t.real;
    }

    float i, j, k, real;
} quarternion;

class IMUSensor
{
private:
    // This is measured in microseconds (1000µs == 1ms)
    // Smaller intervals => More sensor data, but may take up too much CPU time to process
    //  The default here is set to 500ms
    const uint32_t REPORT_INTERVAL = 1000;

    Adafruit_BNO08x bno08x = Adafruit_BNO08x(BNO08X_RESET);

    bool sensorPresent = false;
    bool initialized = false;
    uint32_t lastUpdateTime = 0;

    struct
    {
        SensorInfo<vec3> gyroscope{}; // We are getting this
        SensorInfo<vec3> accelerometer{};
        SensorInfo<vec3> magneticField{}; // We are getting this
        SensorInfo<vec3> gravity{};
        SensorInfo<quarternion> rotation{};
    } rawData;

public:
    void init()
    {
#if IMU_SPI == 1
        sensorPresent = bno08x.begin_SPI(BNO08X_CS, BNO08X_INT);
#else
        sensorPresent = bno08x.begin_I2C();
#endif

        enableReports();
        initialized = true;
    }

    void update()
    {
        if (!initialized || !sensorPresent)
            return;

        if (bno08x.wasReset())
        {
            Debug::write("Sensor was reset");
            enableReports();
        }

        sh2_SensorValue_t sensorData;
        for (int i = 0; i < 5; ++i)
        {
            if (!bno08x.getSensorEvent(&sensorData))
                break;

            switch (sensorData.sensorId)
            {
            case SH2_GYROSCOPE_CALIBRATED:
                Debug::write("Getting gyro");
                rawData.gyroscope = createSensorInfoWith<vec3>(sensorData, sensorData.un.gyroscope);
                break;
            case SH2_MAGNETIC_FIELD_CALIBRATED:
                Debug::write("Getting mag");
                rawData.magneticField = createSensorInfoWith<vec3>(sensorData, sensorData.un.magneticField);
                break;
            case SH2_LINEAR_ACCELERATION:
                Debug::write("Getting linacc");
                rawData.accelerometer = createSensorInfoWith<vec3>(sensorData, sensorData.un.linearAcceleration);
                break;
            case SH2_ROTATION_VECTOR:
                Debug::write("Getting rot");
                rawData.rotation = createSensorInfoWith<quarternion>(sensorData, sensorData.un.rotationVector);
                break;
            case SH2_GRAVITY:
                Debug::write("Getting grav");
                rawData.gravity = createSensorInfoWith<vec3>(sensorData, sensorData.un.gravity);
                break;
            default:
                break;
            }
        }
        Debug::write("Getting sensor data complete\n");
    }

    void printTo(ICommStream *commStream)
    {
        char *dataBytes = reinterpret_cast<char *>(&rawData);

        // These data bytes may accidentally contain the header or footer, let's escape it to be safe
        auto adjustedLength = countEscapedLength(dataBytes, sizeof(rawData));
        char escapedData[adjustedLength];

        escapeData(dataBytes, escapedData, sizeof(rawData));

        commStream->write(escapedData, adjustedLength);
    }

private:
    void enableReports()
    {
        bno08x.enableReport(SH2_LINEAR_ACCELERATION);
        bno08x.enableReport(SH2_GYROSCOPE_CALIBRATED);
        bno08x.enableReport(SH2_MAGNETIC_FIELD_CALIBRATED);
        bno08x.enableReport(SH2_GRAVITY);
        bno08x.enableReport(SH2_ROTATION_VECTOR);
    }

    template <typename T, typename Y>
    SensorInfo<T> createSensorInfoWith(const sh2_SensorValue_t &sensorData, const Y &dataField)
    {
        return SensorInfo<T>{
            TimingUtils::getTimeMillis(),
            sensorData.status,
            dataField};
    }
};

IMUSensor imu{};