#pragma once

#include "esphome/components/i2c/i2c.h"
#include "esphome/components/touchscreen/touchscreen.h"
#include "esphome/core/component.h"
#include "esphome/core/gpio.h"

namespace esphome::st77922_touch {

using namespace touchscreen;

class ST77922Touchscreen : public Touchscreen, public i2c::I2CDevice {
 public:
  void setup() override;
  void dump_config() override;

  void set_reset_pin(GPIOPin *pin) { this->reset_pin_ = pin; }
  void set_interrupt_pin(InternalGPIOPin *pin) { this->interrupt_pin_ = pin; }

 protected:
  void update_touches() override;

  GPIOPin *reset_pin_{nullptr};
  InternalGPIOPin *interrupt_pin_{nullptr};

  // 连续读失败计数，用于避免日志刷屏
  uint16_t read_fail_count_{0};
};

}  // namespace esphome::st77922_touch
