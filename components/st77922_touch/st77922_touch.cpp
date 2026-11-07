#include "st77922_touch.h"
#include "esphome/core/hal.h"
#include "esphome/core/log.h"

namespace esphome::st77922_touch {

static const char *const TAG = "st77922_touch";

// ST77922 TDDI 触摸寄存器（16 位地址，大端发送）
static const uint16_t REG_TOUCH_INFO = 0x0010;   // bit3 = 有触摸
static const uint16_t REG_MAX_POINTS = 0x0009;   // 支持的触点数
static const uint16_t REG_POINT0 = 0x0014;       // 首点数据
static const uint8_t POINT_SIZE = 7;             // 每点 7 字节
static const uint8_t MAX_POINTS_LIMIT = 5;       // 协议上限
static const uint8_t INFO_TOUCH_MASK = 0x08;     // 有触摸
static const uint8_t POINT_VALID_MASK = 0x80;    // 该点有效
static const uint8_t POINT_XY_MASK = 0x3F;       // X/Y 高 6 位

void ST77922Touchscreen::setup() {
  ESP_LOGCONFIG(TAG, "Setting up ST77922 touchscreen...");

  // 触摸控制器复位：低电平 10ms，然后放高等它启动（与厂家例程一致）
  if (this->reset_pin_ != nullptr) {
    this->reset_pin_->setup();
    this->reset_pin_->digital_write(false);
    delay(10);
    this->reset_pin_->digital_write(true);
    delay(100);
  }

  // 中断引脚仅作输入保留（本驱动用轮询，不依赖中断上报）
  if (this->interrupt_pin_ != nullptr) {
    this->interrupt_pin_->pin_mode(gpio::FLAG_INPUT | gpio::FLAG_PULLUP);
    this->interrupt_pin_->setup();
  }

  // 触摸原始坐标范围默认取面板原生分辨率；可在 YAML 用 calibration 覆盖
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

  // 读最大触点数：它决定每次必须读多少字节才能把 FIFO 排空。
  // 只读 7 字节而实际有 N 个点时，剩余数据留在缓冲里，
  // 会让状态位一直保持"有触摸"，表现为只能点一次、之后再也触发不了按下事件。
  uint8_t max_points = 0;
  if (this->read_register16(REG_MAX_POINTS, &max_points, 1) == i2c::ERROR_OK && max_points > 0 &&
      max_points <= MAX_POINTS_LIMIT) {
    this->max_points_ = max_points;
  } else {
    this->max_points_ = 1;
    ESP_LOGW(TAG, "Max touch points unreadable (got %u), assuming 1", max_points);
  }
  ESP_LOGI(TAG, "Max touch points: %u (drain %u bytes per poll)", this->max_points_,
           (unsigned) (this->max_points_ * POINT_SIZE));
}

void ST77922Touchscreen::update_touches() {
  uint8_t info = 0;
  if (this->read_register16(REG_TOUCH_INFO, &info, 1) != i2c::ERROR_OK) {
    this->read_fail_count_++;
    if (this->read_fail_count_ % 100 == 1) {
      ESP_LOGW(TAG, "I2C read failed (%u times)", this->read_fail_count_);
      this->status_set_warning();
    }
    return;
  }
  if (this->read_fail_count_ > 0) {
    this->read_fail_count_ = 0;
    this->status_clear_warning();
  }

  if ((info & INFO_TOUCH_MASK) == 0) {
    return;  // 没有触摸，交给基类判定为"抬起"
  }

  // 必须一次性把整个 FIFO 读完（7 × 触点数字节），否则控制器缓冲不清，
  // 状态位会一直保持在"有触摸"，下一次按下就再也进不来了。
  uint8_t buf[POINT_SIZE * MAX_POINTS_LIMIT];
  size_t len = (size_t) this->max_points_ * POINT_SIZE;
  if (this->read_register16(REG_POINT0, buf, len) != i2c::ERROR_OK) {
    // 读满长度失败时退回单点长度，避免整颗 IC 卡在"永远有触摸"的状态
    if (len != POINT_SIZE && this->read_register16(REG_POINT0, buf, POINT_SIZE) == i2c::ERROR_OK) {
      len = POINT_SIZE;
    } else {
      return;
    }
  }

  // 取第一个有效点上报（单点模式；多点可扩展成循环 id）
  for (size_t i = 0; i + POINT_SIZE <= len; i += POINT_SIZE) {
    if ((buf[i] & POINT_VALID_MASK) == 0)
      continue;

    int16_t x = ((buf[i] & POINT_XY_MASK) << 8) | buf[i + 1];
    int16_t y = ((buf[i + 2] & POINT_XY_MASK) << 8) | buf[i + 3];

    // 上电瞬间可能读到 0,0，忽略，避免误判成左上角点击
    if (x == 0 && y == 0)
      continue;

    ESP_LOGV(TAG, "Touch raw (%d, %d) pressure=%u", x, y, buf[i + 4]);
    this->add_raw_touch_position_(0, x, y, buf[i + 4]);
    return;
  }

  ESP_LOGV(TAG, "Info=0x%02X says touched, but no valid point in %u bytes", info, (unsigned) len);
}

void ST77922Touchscreen::dump_config() {
  ESP_LOGCONFIG(TAG, "ST77922 Touchscreen (TDDI, I2C 0x%02X):", this->address_);
  LOG_PIN("  Reset Pin: ", this->reset_pin_);
  LOG_PIN("  Interrupt Pin: ", this->interrupt_pin_);
  ESP_LOGCONFIG(TAG,
                "  Max Touch Points: %u\n"
                "  X Raw Range: [%d, %d]\n"
                "  Y Raw Range: [%d, %d]\n"
                "  Display: %dx%d",
                this->max_points_, this->x_raw_min_, this->x_raw_max_, this->y_raw_min_,
                this->y_raw_max_, this->display_width_, this->display_height_);
  LOG_UPDATE_INTERVAL(this);
}

}  // namespace esphome::st77922_touch
