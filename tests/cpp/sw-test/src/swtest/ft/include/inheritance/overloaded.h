
#pragma once

namespace overloaded_inheritance
{

struct OBInitializer {
    virtual ~OBInitializer() = default;
    virtual std::string doInit() {
        return "OBInitializer";
    }
};

struct OB {
    virtual ~OB() = default;
    virtual std::string Init(OBInitializer &init) = 0;
};

struct OCInitializer : OBInitializer {
    std::string doInit() override {
        return "OCInitializer";
    }
};

struct OC : OB {
    std::string Init(OBInitializer &init) override {
        return "OC::Init(OBInitializer &init) => " + init.doInit();
    }

    virtual std::string Init(OCInitializer &init) = 0;
};

struct OG : OC {
    std::string Init(OCInitializer &init) override {
        return "OG::Init(OCInitializer &init) => " + init.doInit();
    }
};

std::string OBinitOB(OB *ob, OBInitializer &init) {
    return ob->Init(init);
}

std::string OCinitOB(OB *oc, OBInitializer &init) {
    return oc->Init(init);
}

std::string OCinitOC(OC *oc, OBInitializer &init) {
    return oc->Init(init);
}

// Can't do this without a cast
// std::string OGinitOB(OG *og, OBInitializer &init) {
//     return og->Init(init);
// }

std::string OGinitOC(OG *og, OCInitializer &init) {
    return og->Init(init);
}

}