#include <Adafruit_NeoPixel.h>

// Define the pin connected to the WS2812 LED
// The onboard WS2812 LED on the ESP32-S3-DevKitC-1 typically uses GPIO 48.
// If it does not work, try changing this to 38 or 18.
#define LED_PIN    48
#define NUM_LEDS   1  // Typically, there is only one onboard LED

// Initialize the NeoPixel object
Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

// Store the current state; initially set to off ('C')
char currentState = 'C';

void setup() {
  // Initialize serial communication at a baud rate of 115200
  Serial.begin(115200);
  
  // Initialize the WS2812 LED
  strip.begin();
  strip.setPixelColor(0, strip.Color(0, 0, 0));
  strip.show(); // Turn the LED off initially
  strip.setBrightness(255); // Set brightness (0–255)
}

void loop() {
  // Check for incoming serial data
  if (Serial.available() > 0) {
    // Read one character
    char incomingChar = Serial.read();

    // Perform an action based on the received character
    switch (incomingChar) {
      case 'R':
        setLedColor(255, 0, 0); // Red
        currentState = 'R';
        break;
      case 'G':
        setLedColor(0, 255, 0); // Green
        currentState = 'G';
        break;
      case 'B':
        setLedColor(0, 0, 255); // Blue
        currentState = 'B';
        break;
      case 'C':
        setLedColor(0, 0, 0);   // Off (black)
        currentState = 'C';
        break;
      case 'T':
        // Query the current state without changing the LED
        break;
      default:
        // Ignore all other characters
        return; 
    }

    // Send back the current state character
    Serial.println(currentState);
  }
}

// Helper function: set the LED color and update the display
void setLedColor(int r, int g, int b) {
  strip.setPixelColor(0, strip.Color(r, g, b));
  strip.show();
}