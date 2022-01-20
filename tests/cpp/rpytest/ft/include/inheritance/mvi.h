
#pragma once

namespace inheritance {

struct MVB {
  MVB() = default;
  MVB(const MVB &) = default;
  virtual ~MVB() = default;

  int b = 1;
  int get_b_b() const { return b; }
};
struct MVC : virtual MVB {
  int c = 2;
  int get_c_b() const { return b; }
  int get_c_c() const { return c; }
};
struct MVD0 : virtual MVC {
  int d0 = 3;
  int get_d0_b() const { return b; }
  int get_d0_c() const { return c; }
  int get_d0_d0() const { return d0; }
};
struct MVD1 : virtual MVC {
  int d1 = 4;
  int get_d1_b() const { return b; }
  int get_d1_c() const { return c; }
  int get_d1_d1() const { return d1; }
};
struct MVE : virtual MVD0, virtual MVD1 {
  int e = 5;
  int get_e_b() const { return b; }
  int get_e_c() const { return c; }
  int get_e_d0() const { return d0; }
  int get_e_d1() const { return d1; }
  int get_e_e() const { return e; }
};
struct MVF : virtual MVE {
  int f = 6;
  int get_f_b() const { return b; }
  int get_f_c() const { return c; }
  int get_f_d0() const { return d0; }
  int get_f_d1() const { return d1; }
  int get_f_e() const { return e; }
  int get_f_f() const { return f; }
};

} // namespace inheritance
