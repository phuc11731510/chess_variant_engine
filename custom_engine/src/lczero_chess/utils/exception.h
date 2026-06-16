#pragma once
#include <stdexcept>
#include <iostream>

namespace lczero {

class Exception : public std::runtime_error {
 public:
  Exception(const std::string& what) : std::runtime_error(what) {
    std::cerr << "Exception: " << what << std::endl;
  }
};

} // namespace lczero
