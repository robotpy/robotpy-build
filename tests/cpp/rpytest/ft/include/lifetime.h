#pragma once

#include <memory>

struct LTWithVirtual {
    virtual bool get_bool() {
        return false;
    }
};

class LTTester {
public:

    void set_val(std::shared_ptr<LTWithVirtual> val) {
        m_val = val;
    }

    bool get_bool() {
        return m_val->get_bool();
    }

private:
    std::shared_ptr<LTWithVirtual> m_val;
};
