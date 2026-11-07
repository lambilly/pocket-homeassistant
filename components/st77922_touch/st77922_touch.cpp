#include "st77922_touch.h"
#include "esphome/core/hal.h"
#include "esphome/core/log.h"

namespace esphome::st77922_touch {

static const char *const TAG = "st77922_touch";

// ST77922 TDDI 触摸寄存器（16 位地址，大端发送）
static const uint16_t REG_TOUCH_INFO = 0x0010;  // bit3 = 有触摸
static const uint16_t REG_POINT0 = 0x0014;      // 首点数据
static const uint8_t POINT_SIZE = 7;            // 每点 7 字节
static const uint8_t INFO_TOUCH_MASK = 0x08;    // 有触摸
static const uint8_t POINT_VALID_MASK = 0x80;   // 该点有效
static const uint8_t POINT_XY_MASK = 0x3F;      // X/Y 高 6 位

void ST77922Touchscreen::setup() {
  ESP_LOGCONFIG(TAG, "Setting up ST77922 touchscreen...");

  // 触摸控制器复位：低电平 20ms，然后放高等它启动
  if (this->reset_pin_ != nullptr) {
    this->reset_pin_->setup();
    this->reset_pin_->digital_write(false);
    delay(20);
    this->reset_pin_->digital_write(true);
    delay(100);
  }

  // 中断引脚仅作输入保留（本驱动用轮询，不依赖中断上报）
  if (this->interrupt_pin_ != nullptr) {
    this->interrupt_pin_->pin_mode(gpio::FLAG_INPUT | gpio::FLAG_PULLUP);
    this->interrupt_pin_->setup();
  }

  // 触摸原始坐标范围就是面板原生分辨率（这块板原生竖屏 320x480）
  if (this->x_raw_max_ == this->x_raw_min_) {
    this->x_raw_max_ = this->display_ != nullptr ? this->display_->get_native_width() : 320;
  }
  if (this->y_raw_max_ == this->y_raw_min_) {
    this->y_raw_max_ = this->display_ != nullptr ? this->display_->get_native_height() : 480;
  }

  // 探活：读状态寄存器，读得到说明触摸那一半活着
  uint8_t info = 0;
  if (this->read_register16(REG_TOUCH_INFO, &info, 1) == i2c::ERROR_OK) {
    ESP_LOGI(TAG, "Touch controller answered, status reg=0x%02X", info);
    this->status_clear_warning();
  } else {
    ESP_LOGE(TAG, "Touch controller not responding at 0x%02X", this->address_);
    this->status_set_warning();
  }
}

void ST77922Touchscreen::update_touches() {
  uint8_t info = 0;
  if (this->read_register16(REG_TOUCH_INFO, &info, 1) != i2c::ERROR_OK) {
    if (this->read_fail_count_++ % 100 == 0) {
      ESP_LOGW(TAG, "I2C read failed (%u)", this->read_fail_count_);
    }
    return;
  }
  this->read_fail_count_ = 0;

  if ((info & INFO_TOUCH_MASK) == 0) {
    return;  // 没有触摸
  }

  // 必须一次性读完 7 字节，否则控制器缓冲不清，下一点读不出来
  uint8_t buf[POINT_SIZE];
  if (this->read_register16(REG_POINT0, buf, POINT_SIZE) != i2c::ERROR_OK) {
    return;
  }

  if ((buf[0] & POINT_VALID_MASK) == 0) {
    return;  // 该点无效
  }

  int16_t x = ((buf[0] & POINT_XY_MASK) << 8) | buf[1];
  int16_t y = ((buf[2] & POINT_XY_MASK) << 8) | buf[3];

  // 上电瞬间可能读到 0,0，忽略，避免误判成左上角点击
  if (x == 0 && y == 0) {
    return;
  }

  ESP_LOGV(TAG, "Touch raw (%d, %d) pressure=%u", x, y, buf[4]);
  this->add_raw_touch_position_(0, x, y, buf[4]);
}

void ST77922Touchscreen::dump_config() {
  ESP_LOGCONFIG(TAG, "ST77922 Touchscreen (TDDI, I2C 0x%02X):", this->address_);
  LOG_PIN("  Reset Pin: ", this->reset_pin_);
  LOG_PIN("  Interrupt Pin: ", this->interrupt_pin_);
  ESP_LOGCONFIG(TAG,
                "  X Raw Range: [%d, %d]\n"
                "  Y Raw Range: [%d, %d]\n"
                "  Display: %dx%d (rotation applied by touchscreen transform)",
                this->x_raw_min_, this->x_raw_max_, this->y_raw_min_, this->y_raw_max_, this->display_width_,
                this->display_height_);
  LOG_UPDATE_INTERVAL(this);
}

}  // namespace esphome::st77922_touch
