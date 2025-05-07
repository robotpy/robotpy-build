
#pragma once

namespace bq {
    struct Hidden {
        Hidden() = default;
        virtual ~Hidden() = default;
    };

    template <typename T>
    struct THiddenBase1 {
        THiddenBase1() = default;
        virtual ~THiddenBase1() = default;
    };

    template <typename T>
    struct THiddenBase2 {
        THiddenBase2() = default;
        virtual ~THiddenBase2() = default;
    };
};