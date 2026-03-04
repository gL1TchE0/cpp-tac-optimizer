// Test program for constant propagation, folding, and algebraic simplification
public class TestProgram1 {
    
    public static int constantPropagation() {
        int x = 5;           // x = 5
        int y = 10;          // y = 10
        int z = x + y;       // z should be 15 (constant folding)
        int result = z * 2;  // result should be 30
        return result;
    }
    
    public static int algebraicSimplification(int a) {
        int b = a * 1;       // Can be simplified to: b = a
        int c = b + 0;       // Can be simplified to: c = b
        int d = c * 2;       // Strength reduction: shift left by 1
        int e = d / 2;       // Can be optimized
        return e;
    }
    
    public static int deadCodeExample(int x) {
        int y = x + 10;
        int z = 20;          // Dead code - never used
        int w = 30;          // Dead code - never used
        return y;
    }
    
    public static int copyPropagation(int a) {
        int b = a;
        int c = b;           // c should use 'a' directly
        int d = c + 5;       // d should use 'a' + 5
        return d;
    }
    
    public static void main(String[] args) {
        System.out.println("Constant Propagation: " + constantPropagation());
        System.out.println("Algebraic Simplification: " + algebraicSimplification(10));
        System.out.println("Dead Code Example: " + deadCodeExample(5));
        System.out.println("Copy Propagation: " + copyPropagation(7));
    }
}
