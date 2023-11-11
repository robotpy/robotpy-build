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
    using z = int;

    int overloaded(int i)
    {
        return 0x1;
    }
    int overloaded(const char *i)
    {
        return 0x2;
    }
    // Hack: this tricks CppHeaderParser..
    const z& overloaded(int i, int j)
    {
        o = i + j;
        return o;
    }

    // This shows rtnType is inconsistent in CppHeaderParser
    const OverloadedObject& overloaded() {
        return *this;
    }

    constexpr int overloaded_constexpr(int a, int b) {
        return a + b;
    }

    constexpr int overloaded_constexpr(int a, int b, int c) {
        return a + b + c;
    }

    static int overloaded_static(int i)
    {
        return 0x3;
    }
    static int overloaded_static(const char *i)
    {
        return 0x4;
    }

    void overloaded_private(int a) {}

private:

    // this causes errors if we don't account for it
    void overloaded_private(int a, int b) {}

    int o;
};