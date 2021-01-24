#pragma once
#include "pchild.h"

class PGChild : public PChild {
public:
  explicit PGChild(int i) : PChild(i) {}

private:
  // test is compile-only, previously would fail to compile this
  int privateFinalTestGC() final { return 30; }
};