
#pragma once

#include "using_companion.h"

namespace cr::inner {
    
class ProtectedUsing {
public:

  ProtectedUsing() = default;
  virtual ~ProtectedUsing() = default;

protected:
  ProtectedUsing(CantResolve t) {}
};

}
