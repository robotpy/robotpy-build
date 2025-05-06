
#pragma once

#include "using_companion.h"
#include <string>

namespace cr::inner {

using cr2::WontResolve;
    
class ProtectedUsing {
public:

  ProtectedUsing() = default;
  virtual ~ProtectedUsing() = default;

protected:
  ProtectedUsing(CantResolve t) {}
};

inline void fn_using(AlsoCantResolve t) {}
inline void fn_using(std::string t) {}

}

// used in using2.h
namespace u {

struct FwdDecl {
  int x = 0;
};

}