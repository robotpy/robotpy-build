#pragma once

#include <stdint.h>

class ClassWithFields {
public:
  ClassWithFields() : ref_int(actual_int) {
    array_of_two[0] = 0x10;
    array_of_two[1] = 0x22;

    ref_int = actual_int;
  }

  // array with size
  int array_of_two[2];

  int get_array_of_two(int index) { return array_of_two[index]; }

  // readwrite
  int actual_int = 2;

  // reference
  int &ref_int;

  // constant
  const int const_field = 3;

  // static
  static int static_int;

  // constant static
  const static int static_const = 5;

  // constexpr
  constexpr static int static_constexpr = 6;

  // there's no sensible way to deal with this automatically
  int should_be_ignored[];
};

struct StructWithBitfields {
  StructWithBitfields() {
    enabled = 0;
    autonomous = 0;
    test = 0;
    eStop = 0;
    fmsAttached = 0;
    dsAttached = 0;
    control_reserved = 0;
  }

  uint32_t enabled : 1;
  uint32_t autonomous : 1;
  uint32_t test : 1;
  uint32_t eStop : 1;
  uint32_t fmsAttached : 1;
  uint32_t dsAttached : 1;
  uint32_t control_reserved : 26;
};
