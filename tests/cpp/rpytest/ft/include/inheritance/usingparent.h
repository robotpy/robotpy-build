
#pragma once

class UPBase {
public:
    virtual ~UPBase() = default;
    int get5() {
        return 5;
    }
};

class UPChild : private UPBase {
public:
    using UPBase::get5;

    int get6() {
        return 6;
    }
};
