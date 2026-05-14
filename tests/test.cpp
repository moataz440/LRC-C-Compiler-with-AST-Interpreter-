#include <iostream>
using namespace std;

int main() {
  int x = 1;
  int y = 0;

  y = x++;      // y=1, x=2
  y = y + ++x;  // x=3, y=1+3=4
  y = y + x--;  // y=4+3=7, x=2
  y = y + --x;  // x=1, y=8

  cout << y << endl;
  cout << x;
  return 0;
}

