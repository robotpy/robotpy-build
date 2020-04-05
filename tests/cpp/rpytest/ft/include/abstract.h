#pragma once
struct Abstract
{
    virtual ~Abstract() {}
    virtual int mustOverrideMe() = 0;
};