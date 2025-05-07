#pragma once

class StaticOnly
{
private:
    // this will only compile if nodelete: true is set in the YML
    ~StaticOnly();

public:
    static int callme()
    {
        return 0x56;
    }
};