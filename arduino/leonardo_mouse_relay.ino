/*
  KeyboardAndMouseControl

  Controls the mouse from five pushbuttons on an Arduino Leonardo, Micro or Due.

  Hardware:
  - five pushbuttons attached to D2, D3, D4, D5, D6

  The mouse movement is always relative. This sketch reads four pushbuttons, and
  uses them to set the movement of the mouse.

  WARNING: When you use the Mouse.move() command, the Arduino takes over your
  mouse! Make sure you have control before you use the mouse commands.

  created 15 Mar 2012
  modified 27 Mar 2012
  by Tom Igoe

  This example code is in the public domain.

  https://www.arduino.cc/en/Tutorial/BuiltInExamples/KeyboardAndMouseControl
*/

#include "Keyboard.h"
#include "Mouse.h"

// max string to be printed to serial
#define MAX_FMT_SIZE 254

// define function prototype
typedef void (*callbackFunction)(byte *buffer, byte bufferSize);

class SerialPacketProtocol
{
public:
  /**
   * @brief Construct a new Serial Packet Protocol object
   * This class defines a simple protocol to receive data faster over serial
   * No error checking is made and packets with variable sizes are not supported
   * in order to decrease possible errors and overhead.
   * The protocol is as follows:
   * 1. The first byte is the size of the packet (excluding the size byte)
   * 2. The second byte is the command byte or packet id
   * 3. The rest of the packet is the data
   *
   *
   * @param baudRate The serial baudRate
   * @param numberOfPackets The maximum number of packets that can be registered
   */
  SerialPacketProtocol(int baudRate, int numberOfPackets = 4)
  {
    this->m_maxFunctions = 4;

    // Alloc memory
    m_functionCallbacks = (callbackFunction *)malloc(numberOfPackets * sizeof(callbackFunction));
    m_packetSizes = (byte *)malloc(numberOfPackets * sizeof(byte));

    Serial.begin(baudRate);
  }

  ~SerialPacketProtocol()
  {
    free(m_functionCallbacks);
    free(m_packetSizes);
  }

  /**
   * @brief Add a function to the protocol
   * The function will be called with the respective packet ID
   * @param packetId The packet id, must be smaller the the numberOfPackets passed in constructor
   * @param packetSize The packet size, must include the packetId byte
   * @param function The function to call
   */
  bool setHandler(byte packetId, callbackFunction callback, byte packetSize)
  {
    if (packetId < m_maxFunctions)
    {
      m_functionCallbacks[packetId] = callback;
      m_packetSizes[packetId] = packetSize;
      return true;
    }
    else
    {
      this->sendPrint("ERROR, Packet ID=%d out of range", packetId);
      return false;
    }
  }

  /**
   * @brief Simulates a printf over serial
   */
  void sendPrint(const char *fmt, ...)
  {
    char formatted_string[MAX_FMT_SIZE];

    va_list va;
    va_start(va, fmt);
    int _size = vsprintf(formatted_string, fmt, va);
    va_end(va);

    Serial.println(formatted_string);
  }

  /**
   * @brief Process the serial buffer
   * This function should to be called on every loop
   *
   */
  void update()
  {
    // Check if there is data in the serial buffer
    if (Serial.available() > 0)
    {
      // Read the first byte
      byte bytePacket = Serial.read();

      // Check if it is a new packet
      if (m_serialBufferCurrentSize == 0 && m_serialBufferCurrentPacketSize == 0)
      {
        //sendPrint("Recieved Packet data with size: %d", bytePacket);
        // First byte represent the size not stored in the buffer
        m_serialBufferCurrentPacketSize = bytePacket;
        return;
      }
      // Check if the packet id is valid
      else if (m_serialBufferCurrentSize == 0)
      {
        // Second byte represent the packet id
        if (bytePacket >= m_maxFunctions)
        {
          this->sendPrint("ERROR, Packet ID=%d not known", bytePacket);
          m_serialBufferCurrentSize = 0;
          m_serialBufferCurrentPacketSize = 0;
          return;
        }
        else if (m_serialBufferCurrentPacketSize != m_packetSizes[bytePacket])
        {
          this->sendPrint("ERROR, Packet ID=%d sizes sent do not match", bytePacket);
          m_serialBufferCurrentSize = 0;
          m_serialBufferCurrentPacketSize = 0;
          return;
        }
      }

      // Append current byte to the buffer
      m_serialBuffer[m_serialBufferCurrentSize++] = bytePacket;

      // Check if the packet is complete
      if (m_serialBufferCurrentSize == m_serialBufferCurrentPacketSize)
      {
        //this->sendPrint("Recieved Packet with header: %d and size: %d", m_serialBuffer[0], m_serialBufferCurrentSize);
        handleCurrentPacket();
        m_serialBufferCurrentSize = 0;
        m_serialBufferCurrentPacketSize = 0;
      }
    }
  }

private:
  void handleCurrentPacket()
  {
    // Call the callback function starting on the packet header
    m_functionCallbacks[m_serialBuffer[0]](m_serialBuffer, m_serialBufferCurrentSize);
  }

private:
  byte m_serialBuffer[254] = {};
  byte m_serialBufferCurrentSize = 0;
  byte m_serialBufferCurrentPacketSize = 0;

  // Related to function callbacks and packet redirection
  byte m_maxFunctions = 0;
  callbackFunction *m_functionCallbacks;
  byte *m_packetSizes;

};

enum PacketHeaders{
  COMMAND_LDOWN,
  COMMAND_LUP,
  COMMAND_MOUSEMOVE,
};

struct SerialMouseMovePacket
{
  byte command;
  short x;
  short y;
};

SerialPacketProtocol *packetProtocol;


/*************************************************************
 *  Function callbacks
 *************************************************************/
void mouseMoveCallback(SerialMouseMovePacket *buffer, byte bufferSize)
{
  moveLargeMouse(buffer->x, buffer->y);
  packetProtocol->sendPrint("Mouse moved (%d), (%d)", buffer->x, buffer->y);
}

void mouseLDownCallback(byte *buffer, byte bufferSize)
{
  Mouse.press(MOUSE_LEFT);
}

void mouseLUpCallback(byte *buffer, byte bufferSize)
{
  Mouse.release(MOUSE_LEFT);
}

void moveLargeMouse(int x, int y)
{
  if (x == 0 && y == 0)
  {
    return;
  }

  byte times = max(ceil(abs(x) / 125.0), ceil(abs(y) / 125.0));
  int x_delta = floor(x / times);
  int y_delta = floor(y / times);

  int x_remainder = int(x % x_delta);
  int y_remainder = int(y % y_delta);

  for (int i = 0; i < times; i++)
  {
    Mouse.move(x_delta, y_delta, 0);
    //packetProtocol->sendPrint("Small Delta Mouse Move to x=%d, y=%d",x_delta,y_delta);
  }

  if(x_remainder || y_remainder){
    Mouse.move(x_remainder, y_remainder, 0);
    //packetProtocol->sendPrint("Small Mouse Move to x=%d, y=%d",x_remainder,y_remainder);
  }
}



void setup()
{
  // initialize the buttons' inputs:
  packetProtocol = new SerialPacketProtocol(115200, sizeof(PacketHeaders));
  packetProtocol->setHandler(COMMAND_MOUSEMOVE, mouseMoveCallback, sizeof(SerialMouseMovePacket));
  packetProtocol->setHandler(COMMAND_LDOWN, mouseLDownCallback, 1);
  packetProtocol->setHandler(COMMAND_LUP, mouseLUpCallback, 1);

  // initialize mouse control:
  Mouse.begin();
  // Keyboard.begin();
}

void loop()
{
  packetProtocol->update();
}
