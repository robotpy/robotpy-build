
#pragma once

struct MoveOnlyParam {
  MoveOnlyParam() = default;
  MoveOnlyParam(MoveOnlyParam &&) = default;
  MoveOnlyParam(const MoveOnlyParam &) = delete;
  MoveOnlyParam &operator=(MoveOnlyParam &&) = default;
  MoveOnlyParam &operator=(const MoveOnlyParam &) = delete;

  int i = 6;
};

struct ClassWithTrampoline {

    static constexpr int kConst = 42;

    ClassWithTrampoline() = default;
    virtual ~ClassWithTrampoline() {}

    enum E { E1 };

    virtual int fnWithMoveOnlyParam(MoveOnlyParam param) {
        return param.i;
    }

    static int check_moveonly(ClassWithTrampoline * o) {
        MoveOnlyParam param;
        param.i = 7;
        return o->fnWithMoveOnlyParam(std::move(param));
    }

    virtual E getE() {
        return E1;
    }

protected:
    // bug: ensure this doesn't get forwarded
    ClassWithTrampoline(const int &name) {}
};
