
#pragma once

// unnamed enum at global scope not supported yet
// enum { UGEX = 7 };

// global enum
enum GEnum { GE1 = 1 };

// global enum class
enum class GCEnum { GCE1 = 1 };

// global enum in a namespace
namespace enum_ns {

enum NSGEnum { NSGE2 = 2 };
enum class NSGCEnum { NSGE2 = 2 };

// unnamed enum in a namespace not supported yet
// enum { NSUGEX = 5 };

} // namespace enum_ns

// enum in a class
class EnumContainer {
public:
  enum InnerEnum { IE1 = 1 };
  enum class InnerCEnum { IEC1 = 1 };

  // unnamed enum in a class
  enum { UEX = 4 };
};

// enum in a namespace in a class
namespace enum_container_ns {
class NSEnumContainer {
public:
  enum InnerEnum { NSIE1 = 1 };
  enum class InnerCEnum { NSIEC1 = 1 };
};
}; // namespace enum_container_ns

// enum in a namespace in a nested class
namespace enum_container_ns {
class NSEnumContainer2 {
public:
  class InnerEnumContainer {
    public:
    enum MoreInnerEnum { NSIEMIE1 = 1 };
    enum class MoreInnerCEnum { NSIEMIEC1 = 1 };
  };
  
};
}; // namespace enum_container_ns


// strip prefix
enum StripPrefixEnum { STRIP_1 = 1, STRIP_B = 2 };

// global enum with arithmetic
enum GEnumMath { MGE1 = 1 };

// enum with arithmetic in a class
class EnumContainer2 {
public:
  enum InnerMathEnum { IME1 = 1 };
};
