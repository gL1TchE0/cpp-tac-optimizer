// Test program for CSE, loop optimization, and unreachable code
public class TestProgram2 {
    
    public static int commonSubexpressionElimination(int a, int b) {
        int x = a * b + 5;
        int y = a * b + 10;  // a*b is common subexpression
        int z = a * b + 15;  // a*b is common subexpression
        return x + y + z;
    }
    
    public static int loopInvariantCodeMotion(int n) {
        int sum = 0;
        int constant = 100 * 50;  // Loop invariant
        for (int i = 0; i < n; i++) {
            sum += i + constant;  // constant should be moved outside
        }
        return sum;
    }
    
    public static int unreachableCode(int x) {
        int result;
        if (x > 10) {
            result = x;
        } else {
            result = x + 1;
        }
        // This code is reachable in source but may have dead assignments
        int y = 20;     // Dead variable - never used
        int z = 30;     // Dead variable - never used
        return result;
    }
    
    public static int loopUnrolling() {
        int sum = 0;
        for (int i = 0; i < 4; i++) {  // Small loop - candidate for unrolling
            sum += i * 2;
        }
        return sum;
    }
    
    public static boolean alwaysTrue() {
        return true;
    }
    
    public static int branchOptimization(int x) {
        boolean alwaysTrue = true;
        if (alwaysTrue) {  // Constant condition - can be optimized
            return x * 2;
        } else {
            int unused = 999;  // Dead code in else branch
            return x * 3;
        }
    }
    
    public static void main(String[] args) {
        System.out.println("CSE: " + commonSubexpressionElimination(3, 4));
        System.out.println("Loop Invariant: " + loopInvariantCodeMotion(10));
        System.out.println("Unreachable Code: " + unreachableCode(15));
        System.out.println("Loop Unrolling: " + loopUnrolling());
        System.out.println("Branch Optimization: " + branchOptimization(5));
    }
}
