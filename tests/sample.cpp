#include <iostream>
using namespace std;

int main() {
  int a = 1;
  double b = 2.5;
  bool c = true;
  string s = "hi";
  int arr[] = {1, 2, 3};

  if (c && a < 10) {
    a = a + arr[0];
  }

  for (int i = 0; i < 3; i = i + 1) {
    b = b + 0.1;
  }
cout<<a;
  return 0;
}
