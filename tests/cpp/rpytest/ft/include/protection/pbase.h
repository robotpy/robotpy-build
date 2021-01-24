
#pragma once

class PBase {
public:
  virtual ~PBase() {}
  virtual int getChannel() { return channel; }

  // child makes this final
  virtual int privateFinalTestC() { return 1; }
  // grandchild declares this final
  virtual int privateFinalTestGC() { return 10; }
  // child overrides private, which is effectively final
  virtual int privateOverrideTestC() { return 100; }

protected:
  void setChannel(int c) { channel = c; }

private:
  int channel = 9;
};
