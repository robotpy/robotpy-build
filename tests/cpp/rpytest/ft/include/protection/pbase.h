
#pragma once

class PBase
{
public:
    virtual ~PBase() {}
    virtual int getChannel()
    {
        return channel;
    }

protected:
    void setChannel(int c)
    {
        channel = c;
    }

private:
    int channel = 9;
};
