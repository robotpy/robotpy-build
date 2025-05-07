
#pragma once

namespace NS::inner {
    static constexpr auto KONSTANT = 4;
}

class InlineCode {
public:
    enum MyE {
        Value1 = 1
    };

    int get2() const { return 2; }

    int cpp_code_with_constant() { return 3; }
};
