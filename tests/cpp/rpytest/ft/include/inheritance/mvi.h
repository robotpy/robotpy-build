
#pragma once

namespace inheritance {

struct MVIBase {

    virtual ~MVIBase() = default;

    int i = 1;

    int base_getI() {
        return i;
    }
};

struct MVIChild : virtual MVIBase {
    int ci = 2;

    int child_getI() {
        return i;
    }

    int child_getCI() {
        return ci;
    }
};

struct MVIGChildA : virtual MVIChild {
    int cia = 3;

    int gchildA_getI() {
        return i;
    }

    int gchildA_getCI() {
        return ci;
    }

    int gchildA_getCIA() {
        return cia;
    }
};

struct MVIGChildB : virtual MVIChild {
    int cib = 4;

    int gchildB_getI() {
        return i;
    }

    int gchildB_getCI() {
        return ci;
    }

    int gchildB_getCIB() {
        return cib;
    }
};

struct MVIGGChild : virtual MVIGChildA, virtual MVIGChildB {

    int gi = 5;
    
    int ggchild_getI() {
        return i;
    }

    int ggchild_getCI() {
        return ci;
    }

    int ggchild_getCIA() {
        return cia;
    }

    int ggchild_getCIB() {
        return cib;
    }

    int ggchild_getGI() {
        return gi;
    }
};

struct MVIGGGChild : virtual MVIGGChild {
    
    int gggchild_getI() {
        return i;
    }

    int gggchild_getCI() {
        return ci;
    }

    int gggchild_getCIA() {
        return cia;
    }

    int gggchild_getCIB() {
        return cib;
    }

    int gggchild_getGI() {
        return gi;
    }
};


}
