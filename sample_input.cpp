/*
 * Sample C++ program designed to exercise ALL 10 optimization passes.
 * Each section targets a specific optimization technique.
 */
#include <iostream>
using namespace std;

// --- Function for inlining (Pass 10) ---
int square(int x) {
    return x * x;
}

int add(int a, int b) {
    return a + b;
}

int main() {

    // PASS 1 — Constant Folding: 3 + 5 can be computed at compile time
    int a = 3 + 5;

    // PASS 2 — Constant Propagation: a is known to be 8, so propagate
    int b = a * 2;

    // PASS 3 — Algebraic Simplification: x * 1 = x, x + 0 = x
    int c = b * 1;
    int d = c + 0;

    // PASS 4 — Strength Reduction: x * 4 → x << 2
    int e = d * 4;

    // PASS 5 — Copy Propagation: f is just a copy of e
    int f = e;
    int g = f + 10;

    // PASS 6 — Common Subexpression Elimination: same expression computed twice
    int h = a + b;
    int i = a + b;

    // PASS 7 — Dead Code Elimination: j is assigned but never used
    int j = 42;

    // PASS 8 — Unreachable Code Elimination: if(false) block is never entered
    if (false) {
        int k = 100;
        int l = k + 200;
    }

    // PASS 9 — Loop Optimization: loop-invariant code motion
    int m = 5;
    int sum = 0;
    int n = 0;
    while (n < 10) {
        int inv = m * 2;
        sum = sum + inv + n;
        n = n + 1;
    }

    // PASS 10 — Function Inlining: inline small functions
    int result1 = square(4);
    int result2 = add(a, b);

    // Output (preserved by optimizer — not dead code)
    cout << g << endl;
    cout << h << endl;
    cout << i << endl;
    cout << sum << endl;
    cout << result1 << endl;
    cout << result2 << endl;

    return 0;
}
