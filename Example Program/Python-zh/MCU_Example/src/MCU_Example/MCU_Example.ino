#include <Adafruit_NeoPixel.h>

// 定义 WS2812 连接的引脚
// ESP32-S3-DevKitC-1 板载 WS2812 通常在 GPIO 48，如果无效请尝试改为 38 或 18
#define LED_PIN    48
#define NUM_LEDS   1  // 板载通常只有 1 颗灯珠

// 初始化 NeoPixel 对象
Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

// 记录当前状态，初始为关闭 'C'
char currentState = 'C';

void setup() {
  // 初始化串口，波特率设为 115200
  Serial.begin(115200);
  
  // 初始化 WS2812
  strip.begin();
  strip.setPixelColor(0, strip.Color(0, 0, 0));
  strip.show(); // 初始关闭
  strip.setBrightness(255); // 设置亮度 (0-255)
}

void loop() {
  // 检查是否有串口数据输入
  if (Serial.available() > 0) {
    // 读取一个字符
    char incomingChar = Serial.read();

    // 根据接收到的字符执行操作
    switch (incomingChar) {
      case 'R':
        setLedColor(255, 0, 0); // 红色
        currentState = 'R';
        break;
      case 'G':
        setLedColor(0, 255, 0); // 绿色
        currentState = 'G';
        break;
      case 'B':
        setLedColor(0, 0, 255); // 蓝色
        currentState = 'B';
        break;
      case 'C':
        setLedColor(0, 0, 0);   // 关闭 (黑色)
        currentState = 'C';
        break;
      case 'T':
        // 查询状态，不改变灯光
        break;
      default:
        // 其他字符直接忽略
        return; 
    }

    // 返回当前状态字符
    Serial.println(currentState);
  }
}

// 辅助函数：设置灯珠颜色并刷新
void setLedColor(int r, int g, int b) {
  strip.setPixelColor(0, strip.Color(r, g, b));
  strip.show();
}