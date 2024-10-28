/*
 * This file contains variables and defines related to the configuration of the robot.
 */

#pragma once
#include <string>
#include "Oscillator.h"

// Name of the device
const std::string idCode{"Athena"};

// Packet headers and footers
const char commHeader[]{'E', 'D'};
const char commFooter[]{'M', 'O'};

// WiFi support stuff

#define WIFI_SUPPORT 0

#if WIFI_SUPPORT == 1
const std::string hostname{"EDMO: " + idCode};
const char ssid[]{"EDMO"};     //  your network SSID (name)
const char pass[]{"edmotest"}; // your network password
#endif

// Oscilator specifications
const unsigned int NUM_OSCILLATORS = 4; // this number has to match entries in array osc[] (do NOT modify!!)
Oscillator oscillators[NUM_OSCILLATORS] = {
    Oscillator(100, 510, A0),
    Oscillator(120, 540, A1),    
    Oscillator(100, 450, A2),
    Oscillator(110, 480, A3)
};


// SPI has faster throughput, but more wires
#define IMU_SPI 1