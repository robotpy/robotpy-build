#pragma once

#include <cstring>
#include <vector>

class Buffers {
public:

    // in
    void set_buffer(const uint8_t *data, size_t len) {
        m_buf.resize(len);
        memcpy(m_buf.data(), data, len);
    }

    // out
    // - data is bytes
    // - len is input_size and output size
    void get_buffer2(uint8_t *data, size_t *len) {
        *len = get_buffer1(data, *len);
    }

    // out
    // - data is bytes
    // - len is input size
    // - return value is output size
    size_t get_buffer1(uint8_t *data, size_t len) {
        size_t rlen = len < m_buf.size() ? len : m_buf.size();
        if (rlen) {
            memcpy(data, m_buf.data(), rlen);
        }
        return rlen;
    }

    // in and out with shared length
    int inout_buffer(const uint8_t *indata, uint8_t* outdata, int size) {
        for (int i = 0; i < size; i++) {
            outdata[i] = indata[i] + 1;
        }
        return size;
    }

    //
    // virtual functions -- trampolines are disabled but normal function
    // calls work
    //

    virtual void v_set_buffer(const uint8_t *data, size_t len) {
        set_buffer(data, len);
    }

    virtual void v_get_buffer2(uint8_t *data, size_t *len) {
        get_buffer2(data, len);
    }

    virtual size_t v_get_buffer1(uint8_t *data, size_t len) {
        return get_buffer1(data, len);
    }

private:

    std::vector<uint8_t> m_buf;
};
