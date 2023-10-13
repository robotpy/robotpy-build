#pragma once

template <int N>
struct TVParam {
    int get() const {
        return N;
    }
};

template <typename T>
struct TVBase {

    virtual std::string get(T t) const {
        return "TVBase " + std::to_string(t.get());
    }
};
