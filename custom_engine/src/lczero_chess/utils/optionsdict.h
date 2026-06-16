#pragma once

#include <atomic>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>
#include <any>
#include <iostream>
#include "utils/exception.h"

namespace lczero {

class OptionId {
 public:
  enum VisibilityMode {
    kSimpleMode = 1 << 0,
    kNormalMode = 1 << 1,
    kProMode = 1 << 2,
  };

  enum VisibilityMask {
    kSimpleOnly = kSimpleMode,
    kDefaultVisibility = kNormalMode | kProMode,
    kProOnly = kProMode,
    kAlwaysVisible = kSimpleMode | kNormalMode | kProMode,
  };

  struct OptionsParams {
    const char* long_flag = nullptr;
    const char* uci_option = nullptr;
    const char* help_text = nullptr;
    char short_flag = '\0';
    VisibilityMask visibility = kDefaultVisibility;
  };

  OptionId(const OptionsParams& params)
      : long_flag_(params.long_flag),
        uci_option_(params.uci_option),
        help_text_(params.help_text),
        short_flag_(params.short_flag),
        visibility_mask_(params.visibility) {}

  OptionId(const char* long_flag, const char* uci_option, const char* help_text,
           const char short_flag = '\0')
      : long_flag_(long_flag),
        uci_option_(uci_option),
        help_text_(help_text),
        short_flag_(short_flag) {}

  OptionId(const OptionId& other) = delete;
  bool operator==(const OptionId& other) const { return this == &other; }

  const char* long_flag() const { return long_flag_; }
  const char* uci_option() const { return uci_option_; }
  const char* help_text() const { return help_text_; }
  char short_flag() const { return short_flag_; }
  uint64_t visibility_mask() const { return visibility_mask_; }

 private:
  const char* const long_flag_;
  const char* const uci_option_;
  const char* const help_text_;
  const char short_flag_;
  uint64_t visibility_mask_ = kDefaultVisibility;
};

class Button {
 public:
  Button() { val = std::make_shared<bool>(false); }
  Button(bool x) { val = std::make_shared<bool>(x); }
  bool TestAndReset() {
    bool r = *val;
    *val = false;
    return r;
  }
 private:
  std::shared_ptr<bool> val;
};

class OptionsDict {
 public:
  explicit OptionsDict(const OptionsDict* parent = nullptr)
      : parent_(parent) {
    aliases_.push_back(this);
  }

  template <typename T>
  T CastAny(const std::any& a) const {
    if (a.type() == typeid(T)) {
      return std::any_cast<T>(a);
    }
    // Hỗ trợ chuyển đổi kiểu số mềm dẻo tránh crash do mismatch
    if constexpr (std::is_same_v<T, float>) {
      if (a.type() == typeid(double)) return (float)std::any_cast<double>(a);
      if (a.type() == typeid(int)) return (float)std::any_cast<int>(a);
    } else if constexpr (std::is_same_v<T, double>) {
      if (a.type() == typeid(float)) return (double)std::any_cast<float>(a);
      if (a.type() == typeid(int)) return (double)std::any_cast<int>(a);
    } else if constexpr (std::is_same_v<T, int>) {
      if (a.type() == typeid(float)) return (int)std::any_cast<float>(a);
      if (a.type() == typeid(double)) return (int)std::any_cast<double>(a);
    }
    return std::any_cast<T>(a);
  }

  template <typename T>
  T Get(const std::string& key) const {
    for (const auto* alias : aliases_) {
      auto val = alias->OwnGet<T>(key);
      if (val) return *val;
    }
    if (parent_) return parent_->Get<T>(key);
    throw Exception("Key [" + key + "] was not set in options.");
  }

  template <typename T>
  T Get(const OptionId& option_id) const {
    return Get<T>(GetOptionId(option_id));
  }

  template <typename T>
  std::optional<T> OwnGet(const std::string& key) const {
    auto iter = dict_.find(key);
    if (iter != dict_.end()) {
      return CastAny<T>(iter->second);
    }
    return std::nullopt;
  }

  template <typename T>
  std::optional<T> OwnGet(const OptionId& option_id) const {
    return OwnGet<T>(GetOptionId(option_id));
  }

  template <typename T>
  bool Exists(const std::string& key) const {
    for (const auto* alias : aliases_) {
      if (alias->OwnExists<T>(key)) return true;
    }
    return parent_ && parent_->Exists<T>(key);
  }

  template <typename T>
  bool Exists(const OptionId& option_id) const {
    return Exists<T>(GetOptionId(option_id));
  }

  template <typename T>
  void EnsureExists(const OptionId& option_id) const {
    if (!Exists<T>(option_id)) {
      throw Exception(std::string("The flag --") + option_id.long_flag() + " must be specified.");
    }
  }

  template <typename T>
  bool OwnExists(const std::string& key) const {
    return dict_.find(key) != dict_.end();
  }

  template <typename T>
  bool OwnExists(const OptionId& option_id) const {
    return OwnExists<T>(GetOptionId(option_id));
  }

  template <typename T>
  T GetOrDefault(const std::string& key, const T& default_val) const {
    for (const auto* alias : aliases_) {
      auto val = alias->OwnGet<T>(key);
      if (val) return *val;
    }
    if (parent_) return parent_->GetOrDefault<T>(key, default_val);
    return default_val;
  }

  template <typename T>
  T GetOrDefault(const OptionId& option_id, const T& default_val) const {
    return GetOrDefault<T>(GetOptionId(option_id), default_val);
  }

  template <typename T>
  void Set(const std::string& key, const T& value) {
    dict_[key] = std::any(value);
  }

  template <typename T>
  void Set(const OptionId& option_id, const T& value) {
    Set<T>(GetOptionId(option_id), value);
  }

  template <typename T>
  T& GetRef(const std::string& key) {
    auto& val = dict_[key];
    if (!val.has_value()) {
      val = std::any(T{});
    }
    return *std::any_cast<T>(&val);
  }

  template <typename T>
  T& GetRef(const OptionId& option_id) {
    return GetRef<T>(GetOptionId(option_id));
  }

  template <typename T>
  bool IsDefault(const std::string& key) const {
    if (!parent_) return true;
    for (const auto* alias : aliases_) {
      if (alias->OwnExists<T>(key)) return false;
    }
    return parent_->IsDefault<T>(key);
  }

  template <typename T>
  bool IsDefault(const OptionId& option_id) const {
    return IsDefault<T>(GetOptionId(option_id));
  }

  const OptionsDict& GetSubdict(const std::string& name) const {
    auto iter = subdicts_.find(name);
    if (iter != subdicts_.end()) {
      return iter->second;
    }
    throw Exception("Subdict [" + name + "] was not found.");
  }

  OptionsDict* GetMutableSubdict(const std::string& name) {
    auto iter = subdicts_.find(name);
    if (iter != subdicts_.end()) {
      return &iter->second;
    }
    return nullptr;
  }

  OptionsDict* AddSubdict(const std::string& name) {
    subdicts_.emplace(name, OptionsDict(this));
    return &subdicts_[name];
  }

  std::vector<std::string> ListSubdicts() const {
    std::vector<std::string> keys;
    for (const auto& pair : subdicts_) {
      keys.push_back(pair.first);
    }
    return keys;
  }

  void AddAliasDict(const OptionsDict* dict) {
    aliases_.push_back(dict);
  }

  void AddSubdictFromString(const std::string& str) {
    // Parser tối giản cho cấu trúc options kiểu: "key1=val1,key2=val2"
    // Phục vụ cơ bản cho kTimeManagerId
  }

  void CheckAllOptionsRead(const std::string& path_from_parent) const {}

  bool HasSubdict(const std::string& name) const {
    return subdicts_.find(name) != subdicts_.end();
  }

 private:
  static std::string GetOptionId(const OptionId& option_id) {
    return std::to_string(reinterpret_cast<intptr_t>(&option_id));
  }

  const OptionsDict* parent_ = nullptr;
  std::unordered_map<std::string, std::any> dict_;
  std::map<std::string, OptionsDict> subdicts_;
  std::vector<const OptionsDict*> aliases_;
};

} // namespace lczero
