
#include "demo.h"

int add2(int x) {
    return x + 2;
}

void DemoClass::setX(int x) {
    m_x = x;
}

int DemoClass::getX() const {
    return m_x;
}