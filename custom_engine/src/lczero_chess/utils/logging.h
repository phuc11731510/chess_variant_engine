#pragma once
#include <sstream>
#include <iostream>
#include <string>

namespace lczero {

class LogMessage : public std::ostringstream {
 public:
  LogMessage(const char* file, int line) {}
  ~LogMessage() {
    // Write to a logfile or do nothing.
  }
};

class StderrLogMessage : public std::ostringstream {
 public:
  StderrLogMessage(const char* file, int line) {}
  ~StderrLogMessage() {
    std::cerr << this->str() << std::endl;
  }
};

class StdoutLogMessage : public std::ostringstream {
 public:
  StdoutLogMessage(const char* file, int line) {}
  ~StdoutLogMessage() {
    std::cout << this->str() << std::endl;
  }
};

class Logging {
 public:
  static Logging& Get() {
    static Logging instance;
    return instance;
  }
  void SetFilename(const std::string& filename) {}
};

} // namespace lczero

#define LOGFILE ::lczero::LogMessage(__FILE__, __LINE__)
#define CERR ::lczero::StderrLogMessage(__FILE__, __LINE__)
#define COUT ::lczero::StdoutLogMessage(__FILE__, __LINE__)
