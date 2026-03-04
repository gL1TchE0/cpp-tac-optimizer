#include <iostream>
using namespace std;

int add(int x, int y) {
    int t = x + y;       // candidate for function inlining
    return t;
}

int main() {

    // CONSTANT PROPAGATION
    int a = 5;
    int b = a + 3;

    // CONSTANT FOLDING
    int c = 10 + 20;

    // COPY PROPAGATION
    int d = c;

    // ALGEBRAIC SIMPLIFICATION
    int e = d + 0;
    int f = e * 1;

    // STRENGTH REDUCTION
    int g = f * 2;

    // COMMON SUBEXPRESSION ELIMINATION
    int h = a + b;
    int i = a + b;

    // DEAD CODE
    int dead1 = 100;
    int dead2 = dead1 + 20;

    // UNREACHABLE CODE
    if (0) {
        int unreachable = 50;
        cout << unreachable << endl;
    }

    // LOOP OPTIMIZATION
    int sum = 0;
    for (int j = 0; j < 5; j++) {
        sum = sum + j;
    }

    // FUNCTION CALL (candidate for inlining)
    int result = add(g, h);

    cout << result << endl;

    return 0;
}