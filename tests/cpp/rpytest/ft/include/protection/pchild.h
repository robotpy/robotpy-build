#pragma once
#include "pbase.h"

class PChild : public PBase {
protected:
  explicit PChild(int channel) : PBase() { setChannel(channel); }

private:
  int privateFinalTestC() final { return 2; }

public:
  int privateFinalTestGC() override { return 20; }

private:
  int privateOverrideTestC() override { return 200; }
};