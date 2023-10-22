
#pragma once

//
// Ignore everything by default, but enable some things
//

int id_fnIgnore(void) { return 1; }
int id_fnEnable(void) { return 2; }

enum id_IgnoredEnum {
    Param1 = 1,
    Param2 = 2,
};

enum id_EnabledEnum {
    Param3 = 3,
    Param4 = 4,
};

struct id_IgnoreClass {
    enum InnerEnum { 
        Param5 = 5,
    };
};

struct id_EnabledClass {
    enum InnerEnum { 
        Param6 = 6,
    };
    enum InnerEnumMissing { 
        Param7 = 7,
    };

    int fn() { return 3; }

    // not in yaml but still works
    int fn_missing() { return 4; }
};
