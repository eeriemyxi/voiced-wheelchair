// --- Pin Definitions based on your wiring ---
// Motor A (Left)
const int enA = 10; 
const int in1 = 9;  
const int in2 = 8;  

// Motor B (Right)
const int enB = 5;  
const int in3 = 7;  
const int in4 = 6;  

// Speed variable (0 to 255)
int motorSpeed = 200; 

void setup() {
  // Set all motor control pins to outputs
  pinMode(enA, OUTPUT);
  pinMode(in1, OUTPUT);
  pinMode(in2, OUTPUT);
  
  pinMode(enB, OUTPUT);
  pinMode(in3, OUTPUT);
  pinMode(in4, OUTPUT);
  
  // Start serial communication at 9600 baud rate
  Serial.begin(9600);
  Serial.println("System Ready!");
  Serial.println("Type 'W' to go forward, 'X' to go backward, 'S' to stop.");
}

void loop() {
  // Check if you typed anything into the Serial terminal
  if (Serial.available() > 0) {
    char command = Serial.read();
    
    if (command == 'W' || command == 'w') {
      moveForward();
    } 
    else if (command == 'X' || command == 'x') {
      moveBackward();
    }
    else if (command == 'L' || command == 'l') {
      moveLeft();
    }
    else if (command == 'R' || command == 'r') {
      moveRight();
    }
    else if (command == 'S' || command == 's') {
      stopMotors();
    }
  }
}

// --- Motor Control Functions ---

void moveForward() {
  Serial.println("Moving forward...");
  
  // Motor A Forward
  digitalWrite(in1, HIGH);
  digitalWrite(in2, LOW);
  analogWrite(enA, motorSpeed); // analogWrite controls PWM speed
  
  // Motor B Forward
  digitalWrite(in3, HIGH);
  digitalWrite(in4, LOW);
  analogWrite(enB, motorSpeed);
}

void moveRight() {
  Serial.println("Moving right...");
  
  digitalWrite(in1, HIGH);
  digitalWrite(in2, LOW);
  analogWrite(enA, motorSpeed);
  
  digitalWrite(in3, LOW);
  digitalWrite(in4, LOW);
  analogWrite(enB, 0);

  delay(2000);

  digitalWrite(in1, LOW);
  digitalWrite(in2, LOW);
  analogWrite(enA, 0);

}

void moveLeft() {
  Serial.println("Moving left...");
  
  digitalWrite(in3, HIGH);
  digitalWrite(in4, LOW);
  analogWrite(enB, motorSpeed);
  
  digitalWrite(in1, LOW);
  digitalWrite(in2, LOW);
  analogWrite(enA, 0);

  delay(2000);

  digitalWrite(in3, LOW);
  digitalWrite(in4, LOW);
  analogWrite(enB, 0);
}

void moveBackward() {
  Serial.println("Moving backward...");
  
  // Reverse the HIGH/LOW states to reverse direction
  digitalWrite(in1, LOW);
  digitalWrite(in2, HIGH);
  analogWrite(enA, motorSpeed); 
  
  digitalWrite(in3, LOW);
  digitalWrite(in4, HIGH);
  analogWrite(enB, motorSpeed);
}

void stopMotors() {
  Serial.println("Stopping...");
  
  // Setting both IN pins LOW stops the motor
  digitalWrite(in1, LOW);
  digitalWrite(in2, LOW);
  analogWrite(enA, 0);
  
  digitalWrite(in3, LOW);
  digitalWrite(in4, LOW);
  analogWrite(enB, 0);
}
