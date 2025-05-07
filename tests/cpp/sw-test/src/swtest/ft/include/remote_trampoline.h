#pragma  once

#include "baseclass.h"

class RemoteTrampoline : public abaseclass {
public:

    inline virtual std::string fn() {
        return "RemoteTrampoline";
    }
};