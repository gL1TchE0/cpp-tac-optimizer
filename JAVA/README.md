# Java TAC (Three-Address Code) Optimizer

A comprehensive optimization framework for Java programs using **Jimple** (Soot's intermediate representation). This project generates TAC from Java bytecode and applies multiple compiler optimizations.

## 🎯 Features

### Implemented Optimizations

✅ **Constant Propagation** - Replace variables with their constant values  
✅ **Constant Folding** - Evaluate constant expressions at compile time  
✅ **Algebraic Simplification** - Apply algebraic identities (x+0=x, x*1=x, etc.)  
✅ **Strength Reduction** - Replace expensive operations (multiplication → shift)  
✅ **Copy Propagation** - Replace variables with their copied values  
✅ **Common Subexpression Elimination (CSE)** - Eliminate redundant computations  
✅ **Dead Code Elimination** - Remove unused assignments  
✅ **Unreachable Code Elimination** - Remove code that can never execute  
✅ **Loop Optimization** - Basic loop analysis and optimization  
✅ **Function-related Optimizations** - Preparation for inlining

## 📁 Project Structure

```
JAVA/
├── TestProgram1.java           # Test cases for constant propagation, folding, etc.
├── TestProgram2.java           # Test cases for CSE, loop optimization
├── TestProgram3.java           # Test cases for function inlining, strength reduction
├── JimpleGenerator.java        # Soot-based TAC generator
├── jimple_optimizer.py         # Python optimizer implementing all optimizations
├── setup.bat                   # Setup script (install dependencies)
├── compile.bat                 # Compile Java programs
├── generate_tac.bat            # Generate Jimple TAC
├── optimize.bat                # Run optimizer
├── run_all.bat                 # Complete pipeline
└── README.md                   # This file
```

## 🚀 Quick Start

### Prerequisites

- **Java JDK 8+** ([Download](https://www.oracle.com/java/technologies/downloads/))
- **Python 3.7+** ([Download](https://www.python.org/downloads/))

### Installation & Running

#### Option 1: Complete Pipeline (Recommended)
```cmd
cd JAVA
run_all.bat
```

This single command will:
1. Set up dependencies (download Soot)
2. Compile all Java programs
3. Generate Jimple TAC
4. Optimize the TAC
5. Show results

#### Option 2: Step-by-Step

```cmd
cd JAVA

# Step 1: Setup
setup.bat

# Step 2: Compile Java programs
compile.bat

# Step 3: Generate Jimple TAC
generate_tac.bat

# Step 4: Run optimizer
optimize.bat
```

## 📊 What Happens

### 1. TAC Generation
Java bytecode → **Jimple TAC** (Three-Address Code)

Example:
```java
int z = x + y;    // Java source
```
↓
```jimple
$i0 = x;          // Jimple TAC
$i1 = y;
$i2 = $i0 + $i1;
z = $i2;
```

### 2. Optimization
Original TAC → **Optimized TAC**

Example optimizations:
```jimple
// BEFORE
x = 5;
y = 10;
z = x + y;        // Constant propagation → z = 5 + 10
result = z * 2;   // Constant folding → result = 30

// AFTER
x = 5;
y = 10;
z = 15;           // Folded!
result = 30;      // Folded!
```

### 3. Results
- **Original TAC**: `jimple_output/*.jimple`
- **Optimized TAC**: `jimple_output/optimized/*.optimized.jimple`

## 🔍 Optimization Examples

### Constant Propagation & Folding
```java
int x = 5;
int y = 10;
int z = x + y;    // Optimized to: z = 15
```

### Algebraic Simplification
```java
int b = a * 1;    // Optimized to: b = a
int c = b + 0;    // Optimized to: c = b
```

### Strength Reduction
```java
int d = n * 4;    // Optimized to: d = n << 2 (shift)
int e = n / 2;    // Optimized to: e = n >> 1 (shift)
```

### Copy Propagation
```java
int b = a;
int c = b;        // Optimized to: c = a
int d = c + 5;    // Optimized to: d = a + 5
```

### Common Subexpression Elimination
```java
int x = a * b + 5;
int y = a * b + 10;    // Reuse a*b from above
int z = a * b + 15;    // Reuse a*b from above
```

### Dead Code Elimination
```java
int y = x + 10;
int z = 20;       // Dead - never used ❌
int w = 30;       // Dead - never used ❌
return y;
```

## 📈 Understanding Results

After running the optimizer, you'll see statistics like:

```
OPTIMIZATION STATISTICS
═══════════════════════════════════════
  Constant Propagation ................     12
  Constant Folding ....................      8
  Copy Propagation ....................      6
  Algebraic Simplification ............      5
  Strength Reduction ..................      4
  Common Subexpression Elimination ....      3
  Dead Code Elimination ...............      7
  Unreachable Code Elimination ........      2
  TOTAL OPTIMIZATIONS APPLIED .........     47
═══════════════════════════════════════
```

## 🛠️ Technical Details

### Jimple (TAC Format)
Jimple is Soot's intermediate representation:
- Three-address code format
- Typed instructions
- Simplified control flow
- Platform-independent

### Optimizer Architecture
```
1. Parse Jimple → Instruction objects
2. Multi-pass optimization:
   - Pass 1: Constant propagation, folding, copy propagation
   - Pass 2: Algebraic simplification, strength reduction
   - Pass 3: Common subexpression elimination
3. Dead code & unreachable code elimination
4. Generate optimized Jimple
```

## 📝 Test Programs

### TestProgram1.java
- Constant propagation
- Constant folding
- Algebraic simplification
- Copy propagation
- Dead code

### TestProgram2.java
- Common subexpression elimination
- Loop optimization
- Unreachable code
- Branch optimization

### TestProgram3.java
- Function inlining candidates
- Complex multi-optimization scenarios
- Strength reduction

## 🔧 Customization

### Adding New Optimizations
Edit `jimple_optimizer.py` and add new optimization methods:

```python
def my_custom_optimization(self):
    """Your optimization description"""
    for instr in self.instructions:
        # Your optimization logic
        pass
```

Then call it in the `optimize()` method.

### Adding New Test Cases
Create new Java files in the JAVA directory and add them to the compilation scripts.

## ⚠️ Troubleshooting

### "Java is not installed"
Install Java JDK 8+ and ensure `java` and `javac` are in your PATH.

### "Python is not installed"
Install Python 3.7+ and ensure `python` is in your PATH.

### "Soot JAR not found"
Run `setup.bat` to download Soot, or manually download from:
https://github.com/soot-oss/soot/releases/download/v4.4.1/soot-4.4.1-jar-with-dependencies.jar

Save it to: `JAVA/lib/`

### "Class files not found"
Run `compile.bat` before `generate_tac.bat`.

### "Jimple files not found"
Run `generate_tac.bat` before `optimize.bat`.

## 📚 References

- **Soot Framework**: https://soot-oss.github.io/soot/
- **Jimple Specification**: https://www.sable.mcgill.ca/soot/doc/
- **Compiler Optimizations**: "Compilers: Principles, Techniques, and Tools" (Dragon Book)

## 🎓 Educational Use

This project demonstrates:
- Intermediate representation (IR) generation
- Multi-pass optimization algorithms
- Data flow analysis
- Control flow analysis
- Compiler optimization techniques

Perfect for:
- Compiler design courses
- Code optimization studies
- Program analysis research
- Understanding TAC/IR concepts

## 📄 License

Educational use - free to use and modify.

## 👨‍💻 Author

Created for compiler design and optimization studies.

---

**Enjoy optimizing! 🚀**
