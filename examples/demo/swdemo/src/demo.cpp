
#include "demo.h"

int add2(int x) {
    return x + 2;
}

namespace demo {

void DemoClass::setX(int x) {
    m_x = x;
}

int DemoClass::getX() const {
    return m_x;
}

} // namespace demo
