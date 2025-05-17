#pragma once
struct Abstract
{
    virtual ~Abstract() {}
    virtual int mustOverrideMe() = 0;
};

struct PrivateAbstract
{
    PrivateAbstract() {}
    virtual ~PrivateAbstract() = default;

    static int getPrivateOverride(PrivateAbstract *p) {
        return p->mustOverrideMe();
    }
    
private:
    virtual int mustOverrideMe() = 0;
};

