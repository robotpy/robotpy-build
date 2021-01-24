#pragma once

#include <vector>

int fnSimpleDefaultParam(int i, int j = 3) { return i + j; }

std::vector<int> fnEmptyDefaultParam(std::vector<int> p = {}) { return p; }
