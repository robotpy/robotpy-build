#pragma once

class HasOperator {
public:
    HasOperator() : m_i(0) {}
    HasOperator(int i) : m_i(i) {}

    bool operator==(const HasOperator &o) const {
        return m_i == o.m_i;
    }

private:
    int m_i;
};

struct HasOperatorNoDefault {
    // no default constructor
    explicit HasOperatorNoDefault(int set_x) {
        x = set_x;
    }

    bool operator==(const HasOperatorNoDefault &o) const {
        return x == o.x;
    }

    int x;
};