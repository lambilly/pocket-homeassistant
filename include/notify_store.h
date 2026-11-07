// ==========================================================
// v2.0 NOTIFY：通知环形缓冲（8 槽）
// ----------------------------------------------------------
// 设计要点：
//   · 热点在 MQTT 回调里写入、在页面 1s 巡检里读取，两边都在主线程，
//     不需要加锁；只是把“存哪、怎么截断、怎么判重复”收在一处，
//     避免 lambda 里堆一大堆字符串处理代码。
//   · 截断按 UTF-8 字节边界回退，绝不切出半个汉字（屏幕会显示方块/乱码）。
//   · rev 是内容版本号：页面只在 rev 变化时重刷 label，
//     否则每秒 12 次 lv_label_set_text 会白耗 SPI 与 CPU。
// ==========================================================
#pragma once

#include <cstdint>
#include <cstring>
#include <ctime>
#include <string>
#include <vector>

#include "notify_charset.h"   // 自动生成的字形码表（.workbuddy/gen_charset_h.py）

namespace ns_notify {

struct Slot {
  std::string title;
  std::string msg;
  uint32_t ts = 0;
};

static Slot slots[8];
static int count = 0;     // 有效条数 0..8
static int head = 0;      // 下一条写入位置
static int unread = 0;    // 未读条数（进通知页清零）
static int view = 0;      // 当前浏览位置：0 = 最新，越大越旧
static uint32_t rev = 1;  // 内容版本号

// 单条正文上限（字节）。ESP-IDF 的 MQTT 接收缓冲是 4096，
// 留出 topic 与协议开销，正文封顶 3500；家居简报（约 3.3KB）刚好装下。
static const size_t MSG_MAX = 3500;
// 标题上限 72 字节 ≈ 24 汉字。为什么不给更大：标题 label 的 DOT 省略号依赖
//   宽度约束才生效，而宽度在运行期未必稳；24 字 × 12px = 288px，加左边距 23
//   到 311px，仍然不会压到 x348 的时间，版式靠长度兜住而不是靠布局。
static const size_t TITLE_MAX = 72;

// 按 UTF-8 字符边界截断，超长补省略号
static std::string clip(const std::string &s, size_t maxb) {
  if (s.size() <= maxb) return s;
  size_t cut = maxb;
  while (cut > 0 && (static_cast<unsigned char>(s[cut]) & 0xC0) == 0x80) cut--;
  return s.substr(0, cut) + "…";
}

static inline bool is_space(char c) { return c == ' ' || c == '\t'; }

// 文本规整（11-01 用户反馈「没有按原通知换行」后新增）
//   1) CRLF / CR 统一成 LF，去掉 BOM
//   2) 字面量转义还原：MQTT 载荷若被上游多转义一层，换行会变成两个字符 \ 和 n
//      —— 这里还原成真换行，否则整条通知挤成一行
//   3) 制表符变空格，逐行去首尾空格，连续 3 个以上换行压成 2 个
static std::string normalize(const std::string &in) {
  std::string s;
  s.reserve(in.size());

  size_t i = 0;
  if (in.size() >= 3 && (unsigned char) in[0] == 0xEF && (unsigned char) in[1] == 0xBB &&
      (unsigned char) in[2] == 0xBF) {
    i = 3;                                     // UTF-8 BOM
  }
  for (; i < in.size(); i++) {
    const char c = in[i];
    if (c == '\r') continue;                   // CRLF / CR → 只留 LF
    if (c == '\\' && i + 1 < in.size()) {
      const char n = in[i + 1];
      if (n == 'n') { s += '\n'; i++; continue; }
      if (n == 't') { s += ' ';  i++; continue; }
      if (n == '"') { s += '"';  i++; continue; }
      if (n == '\\') { s += '\\'; i++; continue; }
    }
    s += (c == '\t') ? ' ' : c;
  }

  // 逐行 trim + 连续空行压缩成 1 个
  std::vector<std::string> lines;
  size_t pos = 0;
  while (true) {
    const size_t nl = s.find('\n', pos);
    const size_t end = (nl == std::string::npos) ? s.size() : nl;
    size_t b = pos, e = end;
    while (b < e && is_space(s[b])) b++;
    while (e > b && is_space(s[e - 1])) e--;
    lines.push_back(s.substr(b, e - b));
    if (nl == std::string::npos) break;
    pos = nl + 1;
  }
  while (!lines.empty() && lines.back().empty()) lines.pop_back();

  std::string out;
  out.reserve(s.size());
  int blanks = 0;
  for (const auto &ln : lines) {
    if (ln.empty()) { blanks++; continue; }
    if (!out.empty()) out += (blanks > 0) ? "\n\n" : "\n";
    out += ln;
    blanks = 0;
  }
  return out;
}

// ----------------------------------------------------------
// 条目断行（11-01 第八轮）
//   上游的通知正文是一段到底的流水文字，条目之间只用两个空格加序号分隔：
//     "…0Klx  1.【天气】…  2.【室内】…  3.【室外】…"
//   硬折行只会按像素切，序号很可能落在行中间，读起来还是一堵墙。
//   这里先把「空格 + 1~2 位数字 + . 或 、」认成条目序号，在它前面断成新行。
//   排除项（避免误伤）：
//     · "PM2.5" 前面不是空格  → 不匹配
//     · "3.33km/h" 的 '.' 后面是数字 → 不匹配
//     · "2026年" 没有点 → 不匹配
//   幂等：已经断过的地方前面是 '\n' 不是空格，再跑一遍不会重复断。
// ----------------------------------------------------------
static std::string split_items(const std::string &s) {
  std::string out;
  out.reserve(s.size() + 64);
  bool has_text = false;      // 前面是否已有正文（避免开头就断）

  size_t i = 0;
  while (i < s.size()) {
    if (s[i] == ' ' && i + 3 < s.size() && s[i + 1] >= '0' && s[i + 1] <= '9') {
      size_t j = i + 1;
      while (j < s.size() && s[j] >= '0' && s[j] <= '9' && j - (i + 1) < 2) j++;

      size_t after = 0;
      bool ok = false;
      if (j < s.size() && s[j] == '.') {
        after = j + 1;
        // '.' 后面不能是数字（3.33 不是序号）
        ok = !(after < s.size() && s[after] >= '0' && s[after] <= '9');
      } else if (j + 2 < s.size() && (unsigned char) s[j] == 0xE3 &&
                 (unsigned char) s[j + 1] == 0x80 && (unsigned char) s[j + 2] == 0x81) {
        after = j + 3;                        // 、
        ok = true;
      }
      if (ok && after < s.size() && has_text) {
        // 行尾的空格要清干净，否则会留下一个「只有空格的行」
        while (!out.empty() && out.back() == ' ') out.pop_back();
        out += '\n';
        while (i < after && s[i] == ' ') i++;   // 跳过序号前的所有空格
        out.append(s, i, after - i);            // 序号连点一起抄："1." / "12、"
        i = after;
        has_text = true;
        continue;
      }
    }
    if (s[i] != ' ' && s[i] != '\n') has_text = true;
    out += s[i++];
  }
  return out;
}

// ----------------------------------------------------------
// 硬折行（11-01 第三轮，用户「内容仍然没有换行、右边没有留白」后新增）
//   为什么不能只靠 LVGL 的 LV_LABEL_LONG_WRAP：
//     正文 label 的宽度在 set_text 之后会被文本重算覆盖（退成内容宽），
//     一旦宽度失守，WRAP 没有可用的「行宽」参照，整条正文就变成一行，
//     右端直接顶到卡片边框——连试两轮 set_width + update_layout 都没稳住。
//   所以在入库时就把长行自己切开，插真换行符：
//     · 换行符是硬断行，宽度策略再怎么变都照断；
//     · 每行最多 425px，而正文可用宽 450px，于是右侧天然留出 25px
//       （第十轮：左边距 10→5，折行同步 420→425，右侧留白保持原样）；
//     · 行首避头点：，。！？、；：）」』】》 这类标点若正好落在行首，
//       就跟着上一行一起收尾（允许该行超宽 12px，仍在 450px 内）。
//   宽度口径（fontTools 实测 NotoSansSC-SemiBold，12px）：
//     汉字/全角/符号 12px，ASCII 字母数字 7px，空格 3px
//   LVGL 的 #RRGGBB 着色标记不计宽（两个 # 之间的六位十六进制原样透传）。
// ----------------------------------------------------------
static const int WRAP_PX = 425;

static inline int ch_px(uint32_t cp) {
  if (cp == ' ') return 3;
  if (cp < 0x80) return 7;
  return 12;
}

// 可连写的「词内」字符：ASCII 字母数字 + . % / - : _ 以及 °（U+00B0）
//   用于把 "PM2.5" "1006hPa" "3.33km/h" "27°C" 当成一个整体、不被行宽劈开
static inline bool is_word_ch(uint32_t cp) {
  if ((cp >= '0' && cp <= '9') || (cp >= 'a' && cp <= 'z') || (cp >= 'A' && cp <= 'Z')) return true;
  if (cp == '.' || cp == '%' || cp == '/' || cp == '-' || cp == ':' || cp == '_') return true;
  if (cp == 0xB0) return true;   // °
  return false;
}

// 行首禁则标点（出现在行首会让版面难看）
static inline bool no_line_head(uint32_t cp) {
  switch (cp) {
    case ',' : case '.' : case '!' : case '?' : case ';' : case ':':
    case 0xFF0C: case 0x3002: case 0xFF01: case 0xFF1F: case 0x3001:   // ，。！？、
    case 0xFF1B: case 0xFF1A:                                            // ；：
    case 0xFF09: case 0x300D: case 0x300F: case 0x3011: case 0x300B:     // ）」』】》
    case 0x201D: case 0x2019:                                            // ” ’
      return true;
    default:
      return false;
  }
}

static inline bool is_hex6(const std::string &s, size_t p) {
  if (p + 6 > s.size()) return false;
  for (size_t k = 0; k < 6; k++) {
    const char c = s[p + k];
    const bool hex = (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F');
    if (!hex) return false;
  }
  return true;
}

// 把 recolor 标记整个抹掉，只留可见文字（第十九轮）
//   用途：标题栏。标题只允许纯文字，图标由页面固定给（铃铛），
//   上游若随标题带了 emoji → 图标标记，会和铃铛挤成「两个图标」。
static std::string strip_marks(const std::string &s) {
  std::string out;
  out.reserve(s.size());
  for (size_t i = 0; i < s.size();) {
    if (s[i] == '#' && is_hex6(s, i + 1)) {
      size_t g = i + 7;
      while (g < s.size() && s[g] == ' ') g++;
      const size_t e = s.find('#', g);
      if (e != std::string::npos && e - g <= 4) { i = e + 1; continue; }
      i++;
      continue;
    }
    out += s[i++];
  }
  return out;
}

// 行尾若是孤零零一个 recolor 标记（图标），把它单独摘出来 —— 折行时
//   连它和后面的字一起挪到下一行。否则屏幕上会出现「一行只有一个星星」
//   （用户 18 轮报的新闻简报就是：每条新闻前的星号落单，标题跑到下一行）。
//   返回摘出的标记（含 #RRGGBB 与收尾 #），mw 回填它的可视宽度；没有则返回空。
static std::string pop_tail_mark(std::string &out, int &mw) {
  const size_t end = out.size();
  if (end < 10 || out[end - 1] != '#') return "";
  for (size_t back = 1; back <= 12 && back < end; back++) {
    const size_t p = end - 1 - back;
    if (out[p] != '#') continue;
    if (!is_hex6(out, p + 1)) continue;
    size_t g = p + 7;
    while (g < end && out[g] == ' ') g++;
    const size_t len = (end - 1) - g;
    if (len < 1 || len > 4) continue;
    bool has_text = false;                    // 行里还得有别的字，否则整行就一个图标
    for (size_t k = 0; k < p; k++) {
      if (out[k] != ' ' && out[k] != '\n') { has_text = true; break; }
    }
    if (!has_text) return "";
    mw = (static_cast<unsigned char>(out[g]) < 0x80)
             ? ch_px(static_cast<unsigned char>(out[g])) : 12;
    std::string m = out.substr(p);
    out.erase(p);
    return m;
  }
  return "";
}

static std::string wrap_hard(const std::string &s) {
  std::string out;
  out.reserve(s.size() + s.size() / 24);

  int w = 0;            // 当前行已占宽度
  size_t i = 0;
  while (i < s.size()) {
    const unsigned char b = static_cast<unsigned char>(s[i]);

    // LVGL recolor 标记「#RRGGBB 字形#」整段当一个不可拆的原子（16 轮）：
    //   只抄 #RRGGBB 会把折行断在和字形之间 —— 上一行末尾留一串 #B39DFF、
    //   下一行图标没颜色，屏幕上看就是「图标丢了」。
    //   宽度只算字形本身（hex 和两侧 # 都不上屏）。
    if (b == '#' && is_hex6(s, i + 1)) {
      size_t j = i + 7;
      while (j < s.size() && s[j] == ' ') j++;
      size_t k = j;
      while (k < s.size() && (k - j) < 8 && s[k] != '#') k++;
      if (k > j && k < s.size() && s[k] == '#') {
        const unsigned char mb = static_cast<unsigned char>(s[j]);
        const int mw = (mb < 0x80) ? ch_px(mb) : 12;
        if (w > 0 && w + mw > WRAP_PX) { out += '\n'; w = 0; }
        out.append(s, i, k + 1 - i);
        w += mw;
        i = k + 1;
        continue;
      }
      out.append(s, i, 7);
      i += 7;
      continue;
    }
    if (b == '#') {           // recolor 的收尾 #
      out += '#';
      i++;
      continue;
    }

    uint32_t cp = 0;
    size_t n = 1;
    if (b < 0x80)                { cp = b;          n = 1; }
    else if ((b & 0xE0) == 0xC0) { cp = b & 0x1F;   n = 2; }
    else if ((b & 0xF0) == 0xE0) { cp = b & 0x0F;   n = 3; }
    else if ((b & 0xF8) == 0xF0) { cp = b & 0x07;   n = 4; }
    else { i++; continue; }
    if (i + n > s.size()) break;
    for (size_t k = 1; k < n; k++) {
      const unsigned char c = static_cast<unsigned char>(s[i + k]);
      if ((c & 0xC0) != 0x80) { cp = 0; break; }
      cp = (cp << 6) | (c & 0x3F);
    }

    if (cp == '\n') {         // 原文换行：直接过，重新计宽
      out += '\n';
      w = 0;
      i += n;
      continue;
    }

    // ASCII / 度数符号串整段不断（11-01 第八轮）：
    //   按字符切会把 "PM2.5值16g/m³" 断成 "PM2.5值1|6g/m³"、
    //   "CO2值854ppm" 断成 "CO|2值854ppm"，数字被劈开很难读。
    //   这里先把整段可连写字符测出宽度，放不下就整段挪到下一行。
    if (is_word_ch(cp)) {
      size_t j = i;
      int ww = 0;
      while (j < s.size()) {
        const unsigned char b2 = static_cast<unsigned char>(s[j]);
        uint32_t c2 = 0;
        size_t n2 = 1;
        if (b2 < 0x80)                { c2 = b2;        n2 = 1; }
        else if ((b2 & 0xE0) == 0xC0) { c2 = b2 & 0x1F; n2 = 2; }
        else if ((b2 & 0xF0) == 0xE0) { c2 = b2 & 0x0F; n2 = 3; }
        else if ((b2 & 0xF8) == 0xF0) { c2 = b2 & 0x07; n2 = 4; }
        else break;
        if (j + n2 > s.size()) break;
        for (size_t k = 1; k < n2; k++) {
          const unsigned char c = static_cast<unsigned char>(s[j + k]);
          if ((c & 0xC0) != 0x80) { c2 = 0; break; }
          c2 = (c2 << 6) | (c & 0x3F);
        }
        if (!is_word_ch(c2)) break;
        ww += ch_px(c2);
        j += n2;
      }
      if (ww > 0) {
        // 整段比一行还长（罕见）：按原逻辑逐字符断，别硬挪
        if (ww > WRAP_PX) {
          ww = 0;
          j = i + n;
        }
        if (ww > 0) {
          if (w > 0 && w + ww > WRAP_PX) {
            int tmw = 0;
            std::string tm = pop_tail_mark(out, tmw);
            out += '\n';
            w = 0;
            if (!tm.empty()) { out += tm; w = tmw; }
          }
          out.append(s, i, j - i);
          w += ww;
          i = j;
          continue;
        }
      }
    }

    const int pw = ch_px(cp);
    // 放不下就断行；但禁则标点宁可挤在本行末尾，也不放到下一行行首
    if (w > 0 && w + pw > WRAP_PX && !no_line_head(cp)) {
      if (cp == ' ') { i += n; continue; }   // 折行处的空格吞掉，别留在行首
      int tmw = 0;
      std::string tm = pop_tail_mark(out, tmw);
      out += '\n';
      w = 0;
      if (!tm.empty()) { out += tm; w = tmw; }
    }
    out.append(s, i, n);
    w += pw;
    i += n;
  }
  return out;
}

// 去重已并入 push（见下），这里不再单独暴露 is_dup

static void push(const std::string &title, const std::string &msg, uint32_t ts) {
  // normalize：换行/制表/转义归一
  // filter_known：挖掉字库没有的字（否则是方框）
  // wrap_hard：长行自己切成 ≤432px 的短行（不指望 LVGL 的 WRAP）
  std::string t = clip(filter_known(normalize(title.empty() ? std::string("通知") : title)), TITLE_MAX);
  std::string body = filter_known(normalize(msg));
  if (body.size() > 3300) body = clip(body, 3300);   // 先给折行留出 \n 的余量
  body = split_items(body);                          // 序号前断行（条目各自成段）
  std::string b = clip(wrap_hard(body), MSG_MAX);
  const uint32_t tt = (ts != 0) ? ts : static_cast<uint32_t>(::time(nullptr));

  // 去重必须拿「处理后的值」比对（11-01 修）：以前在上层用原始载荷比，
  //   而缓冲区里存的是 normalize + filter + 折行之后的结果，两者永不相等，
  //   QoS1 的重投会重复入列。现在挪到入库前一刻做。
  if (count > 0) {
    const Slot &last = slots[(head - 1 + 8) % 8];
    if (last.ts == tt && last.title == t && last.msg == b) return;
  }

  Slot &s = slots[head];
  s.title = t;
  s.msg = b;
  s.ts = tt;
  head = (head + 1) % 8;
  if (count < 8) count++;
  unread++;
  rev++;
}

// 清空全部（切换条「全部删除」用）
static void clear_all() {
  for (int i = 0; i < 8; i++) {
    slots[i].title.clear();
    slots[i].msg.clear();
    slots[i].ts = 0;
  }
  count = 0;
  head = 0;
  unread = 0;
  view = 0;
  rev++;
}

// i = 0 是最新一条；越界返回空槽
static const Slot &at(int i) {
  static Slot empty_slot;
  if (i < 0 || i >= count) return empty_slot;
  return slots[((head - 1 - i) % 8 + 8) % 8];
}

// 删除第 i 条（0 = 最新）：把剩下的按“旧→新”重排回数组，保持环形不变式
static void remove_at(int i) {
  if (i < 0 || i >= count) return;
  Slot tmp[8];
  int n = 0;
  for (int k = count - 1; k >= 0; k--) {     // 从最旧到最新
    if (k == i) continue;
    tmp[n++] = at(k);
  }
  for (int k = 0; k < n; k++) slots[k] = tmp[k];
  count = n;
  head = n % 8;
  if (view > count - 1) view = (count > 0) ? count - 1 : 0;
  rev++;
}

}  // namespace ns_notify
