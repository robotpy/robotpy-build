#pragma once
#include "ibase.h"

namespace inheritance {

struct IMOther {
  virtual ~IMOther() {}
};

// a child that does multiple inheritance
struct IMChild : IBase, IMOther {

  std::string baseAndChild() override { return "mchild::baseAndChild"; }

  std::string baseAndChildFinal() final { return "mchild::baseAndChildFinal"; }
};

}; // namespace inheritance