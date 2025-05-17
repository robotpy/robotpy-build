#pragma  once

#include <string>

// tests trampoline across packages
class abaseclass {
public:
    virtual ~abaseclass() = default;

    inline virtual std::string fn() {
        return "abaseclass";
    }

};