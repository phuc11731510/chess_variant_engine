#pragma once

#include <algorithm>
#include <random>
#include <string>
#include "utils/mutex.h"

namespace lczero {

class Random {
 public:
  static Random& Get() {
    static Random rand;
    return rand;
  }

  int GetInt(int min, int max) {
    Mutex::Lock lock(mutex_);
    std::uniform_int_distribution<> dist(min, max);
    return dist(gen_);
  }

  bool GetBool() { return GetInt(0, 1) != 0; }

  double GetDouble(double maxval) {
    Mutex::Lock lock(mutex_);
    std::uniform_real_distribution<> dist(0.0, maxval);
    return dist(gen_);
  }

  float GetFloat(float maxval) {
    Mutex::Lock lock(mutex_);
    std::uniform_real_distribution<> dist(0.0, maxval);
    return dist(gen_);
  }

  std::string GetString(int length) {
    std::string result;
    for (int i = 0; i < length; ++i) {
      result += 'a' + GetInt(0, 25);
    }
    return result;
  }

  double GetGamma(double alpha, double beta) {
    Mutex::Lock lock(mutex_);
    std::gamma_distribution<double> dist(alpha, beta);
    return dist(gen_);
  }

  template <class RandomAccessIterator>
  void Shuffle(RandomAccessIterator s, RandomAccessIterator e) {
    Mutex::Lock lock(mutex_);
    std::shuffle(s, e, gen_);
  }

 private:
  Random() : gen_(std::random_device()()) {}

  Mutex mutex_;
  std::mt19937 gen_;
};

}  // namespace lczero
