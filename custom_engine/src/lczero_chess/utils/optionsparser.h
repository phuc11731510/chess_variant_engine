#pragma once
#include <string>
#include <vector>
#include <memory>
#include "utils/optionsdict.h"

namespace lczero {

class OptionsParser {
 public:
  OptionsParser() : values_(defaults_) {}

  class Option {
   public:
    Option(const OptionId& id) : id_(id) {}
    virtual ~Option() {}
    virtual void SetValue(const std::string& value, OptionsDict* dict) = 0;
   protected:
    const OptionId& id_;
  };

  template <typename Option, typename... Args>
  typename Option::ValueType& Add(Args&&... args) {
    // Trích xuất OptionId từ đối số đầu tiên
    auto extract_id = [](const OptionId& id, auto&&...) -> const OptionId& { return id; };
    const OptionId& id = extract_id(std::forward<Args>(args)...);
    return defaults_.GetRef<typename Option::ValueType>(id);
  }

  const OptionsDict& GetOptionsDict(const std::string& context = {}) { return values_; }
  OptionsDict* GetMutableOptions(const std::string& context = {}) { return &values_; }
  OptionsDict* GetMutableDefaultsOptions() { return &defaults_; }

 private:
  OptionsDict defaults_;
  OptionsDict& values_;
};

class StringOption : public OptionsParser::Option {
 public:
  using ValueType = std::string;
  StringOption(const OptionId& id) : Option(id) {}
  void SetValue(const std::string& value, OptionsDict* dict) override {}
};

class IntOption : public OptionsParser::Option {
 public:
  using ValueType = int;
  IntOption(const OptionId& id, int min, int max) : Option(id) {}
  void SetValue(const std::string& value, OptionsDict* dict) override {}
};

class FloatOption : public OptionsParser::Option {
 public:
  using ValueType = float;
  FloatOption(const OptionId& id, float min, float max) : Option(id) {}
  void SetValue(const std::string& value, OptionsDict* dict) override {}
};

class BoolOption : public OptionsParser::Option {
 public:
  using ValueType = bool;
  BoolOption(const OptionId& id) : Option(id) {}
  void SetValue(const std::string& value, OptionsDict* dict) override {}
};

class ButtonOption : public OptionsParser::Option {
 public:
  using ValueType = Button;
  ButtonOption(const OptionId& id) : Option(id) {}
  void SetValue(const std::string& value, OptionsDict* dict) override {}
};

class ChoiceOption : public OptionsParser::Option {
 public:
  using ValueType = std::string;
  ChoiceOption(const OptionId& id, const std::vector<std::string>& choices) : Option(id) {}
  void SetValue(const std::string& value, OptionsDict* dict) override {}
};

} // namespace lczero
