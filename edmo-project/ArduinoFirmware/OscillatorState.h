#pragma once
#include <cstddef>
// This struct is the format used in serial communication.
// This struct allows users to change any oscillator parameter within 12 bytes
// It also allows us to cast 12 byte char* received from serial communication,
// saving parsing overhead

struct OscillatorParams
{
  float freq = 0;
  float amp = 0;
  float offset = 90;
  float phaseShift = 0;
  bool reverse = false;
  bool orders = false;
};

struct OscillatorState
{
  OscillatorState(const OscillatorParams &params)
  {
    freq = params.freq;
    amp = params.amp;
    offset = params.offset;
    phaseShift = params.phaseShift;
    phase = 0;
  }

  float freq = 0.05;
  float amp = 90;
  float offset = 90;
  float phaseShift = 0;
  float phase = 0;
  bool reverse = false;
  bool orders = false;
  int output = -1;
};

OscillatorState nextState(OscillatorState state, float dt, float ampdt, float phasedt, float offsetdt, float shiftdt, float freqdt) {
  state.amp += ampdt * dt;
  state.phase += phasedt * dt;
  state.offset += offsetdt * dt;
  state.phaseShift += shiftdt * dt;
  state.freq += freqdt * dt;

  return state;
}
