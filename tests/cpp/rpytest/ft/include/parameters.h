
#pragma once

//
// Various tests related to function parameters
//

// the array parameter is returned
int fnParamArrayOut(int x[3])
{
    x[0] = 5;
    x[1] = 6;
    x[2] = 7;
    return 4;
}

// the array parameter is returned, with a default initialization
int fnParamArrayOutWithDefault(int x[3])
{
    x[1] = 6;
    return 4;
}

// parameters that are pointers and fundamental types are out by default
int fnParamFundPtr(int x, int * y)
{
    *y = x + 1;
    return x - 1;
}

// parameters that are references and fundamental types are out by default
int fnParamFundRef(int x, int &y)
{
    y = x - 1;
    return x + 1;
}

// parameters that are const references and fundamental types are inputs
int fnParamFundConstRef(int x, const int &y)
{
    return x + y;
}

