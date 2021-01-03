
#pragma once

// note: unnamed enums not supported at this time

// global enum
enum GEnum { GE1 = 1 };

// global enum class
enum class GCEnum { GCE1 = 1 };

// global enum in a namespace
namespace enum_ns {
enum NSGEnum { NSGE2 = 2 };
enum class NSGCEnum { NSGE2 = 2 };
} // namespace enum_ns

// enum in a class
class EnumContainer {
public:
  enum InnerEnum { IE1 = 1 };
  enum class InnerCEnum { IEC1 = 1 };
};

// enum in a namespace in a class
namespace enum_container_ns {
class NSEnumContainer {
public:
  enum InnerEnum { NSIE1 = 1 };
  enum class InnerCEnum { NSIEC1 = 1 };
};
}; // namespace enum_container_ns
