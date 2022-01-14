
#pragma once

namespace rpy {

struct rpyint_plus_5 {

  rpyint_plus_5() = default;
  rpyint_plus_5(int v) : int_value(v) {}

  int get() const { return int_value; }

  void set(int v) { int_value = v; }

private:
  int int_value = 0;
};

struct rpyint {

  rpyint() = default;

  // this implicit conversion causes issues without `default_arg_cast`
  rpyint(const rpyint_plus_5 &o) : int_value(o.get() + 5) {}

  int get() const { return int_value; }

  void set(int v) { int_value = v; }

private:
  int int_value = 0;
};




} // namespace rpy