// Test program for function inlining and more complex optimizations
public class TestProgram3 {
    
    // Small function - candidate for inlining
    public static int square(int x) {
        return x * x;
    }
    
    // Small function - candidate for inlining
    public static int add(int a, int b) {
        return a + b;
    }
    
    public static int functionInliningExample(int n) {
        int result = square(n);      // Can be inlined to: n * n
        result = add(result, 10);    // Can be inlined to: result + 10
        return result;
    }
    
    public static int complexOptimization(int x, int y) {
        // Multiple optimization opportunities
        int a = 5;                   // Constant
        int b = 10;                  // Constant
        int c = a + b;               // Constant folding: c = 15
        int d = x + 0;               // Algebraic simplification: d = x
        int e = y * 1;               // Algebraic simplification: e = y
        int f = d + e;               // Copy propagation: f = x + y
        int g = c + f;               // g = 15 + x + y
        int unused = 999;            // Dead code
        return g;
    }
    
    public static int strengthReduction(int n) {
        int a = n * 2;               // Should be: n << 1
        int b = n * 4;               // Should be: n << 2
        int c = n * 8;               // Should be: n << 3
        int d = n / 2;               // Should be: n >> 1
        int e = n / 4;               // Should be: n >> 2
        return a + b + c + d + e;
    }
    
    public static void main(String[] args) {
        System.out.println("Function Inlining: " + functionInliningExample(5));
        System.out.println("Complex Optimization: " + complexOptimization(3, 7));
        System.out.println("Strength Reduction: " + strengthReduction(16));
    }
}
