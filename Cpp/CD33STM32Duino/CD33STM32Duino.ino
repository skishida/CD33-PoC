/*
 * STM32DuinoでCD33と通信するコード
 * nucleo L053R8で動作確認
 */

const char STX = 0x02;
const char ETX = 0x03;

const String SERIAL_NO     = "SERIAL_NO";
const String START_MEASURE = "START_MEASURE";
const String STOP_MEASURE  = "STOP_MEASURE";

const String AVG         = "AVG";
const String BIT_RATE    = "BIT_RATE";
const String SAMPLE_RATE = "SAMPLE_RATE";

String serialnumber;
String averageMode;
String sampleRate;
String bitRate;

float         len;
unsigned long timeMeasureStarted;
unsigned long timeMeasured;
int           cnt = 0;

union Distance {
  struct {
    unsigned long time;
    float         len;
    uint8_t       stat;
  };
  uint8_t bin[sizeof(unsigned long) + sizeof(float) + sizeof(uint8_t)];
};

Distance dist;

const uint8_t END     = 0xC0;
const uint8_t ESC     = 0xDB;
const uint8_t ESC_END = 0xDC;
const uint8_t ESC_ESC = 0xDD;

HardwareSerial Serial1(PA10, PA9); // RX/TX それぞれD2,D8に相当

bool          measureend;
bool          measureing;
unsigned long duration = 1;

bool          flippingPin = false;
unsigned long timeLastFlipped;

void sendCommand(const String command) {
  String cmd = STX + command + ETX;
  // Serial.print("TX> ");
  // Serial.println(cmd);
  Serial1.print(cmd);
}

String readResponse() {
  return Serial1.readStringUntil(ETX).substring(1);
}

/* SLIPに基づいたデータエンコード
 * https://qiita.com/hideakitai/items/347985528656be03b620
 */
void sendPacket(const uint8_t* buffer, size_t size) {
  for (size_t i = 0; i < size; ++i) {
    uint8_t data = buffer[i];

    if (data == END) {
      Serial.write(ESC);
      Serial.write(ESC_END);
    } else if (data == ESC) {
      Serial.write(ESC);
      Serial.write(ESC_ESC);
    } else {
      Serial.write(data);
    }
  }
  Serial.write(END);
}

void setup() {

  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(D7, OUTPUT);

  // USB Serialの設定
  // 実はSTM32Duino(mbed)の場合ここのボーレートはあまり本質的ではない
  Serial.begin(1000000); // USB Serial
  while (!Serial) {
  }
  while (Serial.available() > 0) {
    Serial.read();
  }

  // Hardware Serialの設定
  // 実際にマイコンのポート経由で送受信をする
  Serial1.begin(115200); // HW Serial
  Serial1.setTimeout(5);

  // もしセンサが動きっぱだった場合にバッファを綺麗にしておく
  sendCommand(STOP_MEASURE);
  delay(100);
  while (Serial1.available() > 0) {
    Serial1.read();
  }

  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_BUILTIN, HIGH);
    delay(100);
    digitalWrite(LED_BUILTIN, LOW);
    delay(100);
  }
  digitalWrite(D7, flippingPin);
}

void loop() {
  if (!measureing) {
    // 測定待機モード
    String cmd = Serial.readStringUntil('\r');

    // 測定開始
    if (cmd.endsWith("S")) {
      measureing = true;
      digitalWrite(LED_BUILTIN, HIGH);
      sendCommand(START_MEASURE);
      timeMeasureStarted = micros();
      timeLastFlipped    = timeMeasureStarted;
    }

    // 設定読み出し
    if (cmd.endsWith("I")) {
      dumpInfo();
    }

    // 測定時間変更
    // "#10" -> 10秒読みだし
    if (cmd.startsWith("#")) {
      duration = cmd.substring(1).toInt();
    }
  } else {
    // 測定中
    if (micros() - timeMeasureStarted < duration * 1000000) {
      dist.len  = Serial1.readStringUntil('\r').toFloat();
      dist.time = micros() - timeMeasureStarted;
      dist.stat = (flippingPin) ? 0x01 : 0x00;
      // 受信側のバッファ節約のためにSLIP形式でバイナリのまま送る
      sendPacket(dist.bin, sizeof(Distance));
      cnt++;
    } else {
      // 測定終了時の処理
      dist.len  = 9999.99;
      dist.time = 0;
      sendPacket(dist.bin, sizeof(Distance));

      sendCommand(STOP_MEASURE);
      while (Serial1.available() > 0) {
        Serial1.read();
      }

      cnt = 0;

      measureing = false;
      digitalWrite(LED_BUILTIN, LOW);
    }

    // Pin Fipping
    if (micros() - timeLastFlipped > 1000000) {
      flippingPin     = !flippingPin;
      timeLastFlipped = micros();
    }
    digitalWrite(D7, flippingPin);
  }
}

/* 計測設定データ等を読み出す
 */
void dumpInfo() {
  sendCommand(SERIAL_NO);
  serialnumber = readResponse();
  Serial.print("Serial No. : ");
  Serial.println(serialnumber);

  sendCommand(AVG);
  averageMode = readResponse();
  Serial.print("Averaging Mode : ");
  Serial.println(averageMode);

  // sendCommand(BIT_RATE + " 115.2");
  // Serial.print("set bit rate :");
  // Serial.println(readResponse());

  sendCommand(BIT_RATE);
  bitRate = readResponse();
  Serial.print("Bit Rate : ");
  Serial.println(bitRate);

  // sendCommand(SAMPLE_RATE + " 1000");
  // Serial.print("set sample rate :");
  // Serial.println(readResponse());

  sendCommand(SAMPLE_RATE);
  sampleRate = readResponse();
  Serial.print("Sampling Rate : ");
  Serial.println(sampleRate);

  Serial.print("Data Structure : ");
  Serial.println(sizeof(Distance));
  Serial.print("\ttime: ");
  Serial.println(sizeof(unsigned long));
  Serial.print("\tdist: ");
  Serial.println(sizeof(float));
  Serial.print("\tstat: ");
  Serial.println(sizeof(uint8_t));

  while (Serial1.available() > 0) {
    Serial1.read();
  }
}