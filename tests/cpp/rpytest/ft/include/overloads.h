#pragma once

int fnOverload(int i, int j)
{
    return j;
}

int fnOverload(int i)
{
    return i;
}

struct OverloadedObject
{
    int overloaded(int i)
    {
        return 0x1;
    }
    int overloaded(const char *i)
    {
        return 0x2;
    }

    static int overloaded_static(int i)
    {
        return 0x3;
    }
    static int overloaded_static(const char *i)
    {
        return 0x4;
    }
};