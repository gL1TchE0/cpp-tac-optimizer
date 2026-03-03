import re

class TACOptimizer:

    def __init__(self, lines):

        self.lines = [l.strip() for l in lines if l.strip()]

        self.constants = {}
        self.expr_table = {}
        self.used_vars = set()

        self.optimized = []

        self.in_loop = False


    # ------------------------------------------------
    # Collect variables used later (for dead code)
    # ------------------------------------------------

    def collect_used_variables(self):

        for line in self.lines:

            tokens = re.findall(r'\b[a-zA-Z_]\w*\b', line)

            if "=" in line:

                left = line.split("=")[0].strip()

                for t in tokens:

                    if t != left:
                        self.used_vars.add(t)

            else:

                for t in tokens:
                    self.used_vars.add(t)



    # ------------------------------------------------
    # Detect loop region
    # ------------------------------------------------

    def detect_loop(self, line):

        if "goto <D." in line and ">" in line:
            self.in_loop = True

        if "<D." in line and ":" in line:
            self.in_loop = True



    # ------------------------------------------------
    # Constant Propagation (safe)
    # ------------------------------------------------

    def constant_propagation(self, line):

        if self.in_loop:
            return line

        if "=" not in line:
            return line

        left, right = line.split("=", 1)

        for var, val in self.constants.items():

            right = re.sub(r'\b'+var+r'\b', str(val), right)

        return left + "=" + right



    # ------------------------------------------------
    # Constant Folding
    # ------------------------------------------------

    def constant_folding(self, line):

        m = re.search(r'(\w+)\s*=\s*(\d+)\s*([\+\-\*/])\s*(\d+)', line)

        if not m:
            return line

        var, a, op, b = m.groups()

        a = int(a)
        b = int(b)

        if op == '+':
            val = a + b
        elif op == '-':
            val = a - b
        elif op == '*':
            val = a * b
        else:
            val = a // b

        self.constants[var] = val

        return f"{var} = {val}    // constant folding"



    # ------------------------------------------------
    # Copy Propagation
    # ------------------------------------------------

    def copy_propagation(self, line):

        m = re.search(r'(\w+)\s*=\s*(\w+)', line)

        if not m:
            return line

        dest, src = m.groups()

        if src in self.constants:
            return f"{dest} = {self.constants[src]}    // copy propagation"

        return line



    # ------------------------------------------------
    # Algebraic Simplification
    # ------------------------------------------------

    def algebraic(self, line):

        line = re.sub(r'(\w+)\s*\+\s*0', r'\1', line)
        line = re.sub(r'0\s*\+\s*(\w+)', r'\1', line)

        line = re.sub(r'(\w+)\s*\*\s*1', r'\1', line)
        line = re.sub(r'1\s*\*\s*(\w+)', r'\1', line)

        return line



    # ------------------------------------------------
    # Strength Reduction
    # ------------------------------------------------

    def strength_reduction(self, line):

        m = re.search(r'(\w+)\s*=\s*(\w+)\s*\*\s*2', line)

        if not m:
            return line

        var, x = m.groups()

        return f"{var} = {x} << 1    // strength reduction"



    # ------------------------------------------------
    # Common Subexpression Elimination
    # ------------------------------------------------

    def cse(self, line):

        m = re.search(r'(\w+)\s*=\s*(\w+\s*[\+\-\*/]\s*\w+)', line)

        if not m:
            return line

        var, expr = m.groups()

        if expr in self.expr_table:

            prev = self.expr_table[expr]

            return f"{var} = {prev}    // CSE"

        self.expr_table[expr] = var

        return line



    # ------------------------------------------------
    # Unreachable Code
    # ------------------------------------------------

    def unreachable(self, line):

        if "if (0" in line or "if (0 !=" in line:
            return "// unreachable branch removed"

        return line



    # ------------------------------------------------
    # Dead Code Elimination
    # ------------------------------------------------

    def dead_code(self, line):

        if "=" not in line:
            return line
    
        left = line.split("=")[0].strip()
    
        # Do not remove assignments used in return statements
        if left in self.used_vars:
            return line
    
        # Do not remove assignments used in cout operations
        if "cout" in line or "operator<<" in line:
            return line
    
        # Do not remove assignments used for return values
        if "D." in left and "return" in " ".join(self.lines):
            return line
    
        return f"// dead code removed: {line}"



    # ------------------------------------------------
    # Loop Optimization
    # ------------------------------------------------

    def loop_optimization(self, line):

        if "i = i + 1" in line:
            return "i++    // loop optimization"

        return line



    # ------------------------------------------------
    # Function Optimization
    # ------------------------------------------------

    def function_opt(self, line):

        if "add (" in line:
            return line + "    // inline candidate"

        return line



    # ------------------------------------------------
    # Remove GCC internal functions
    # ------------------------------------------------

    def filter_runtime(self, line):

        if "__static_initialization" in line:
            return ""

        if "__tcf_" in line:
            return ""

        if "__ioinit" in line:
            return ""

        return line



    # ------------------------------------------------
    # Run Optimizer
    # ------------------------------------------------

    def optimize(self):

        self.collect_used_variables()

        for line in self.lines:

            line = self.filter_runtime(line)

            if line == "":
                continue

            self.detect_loop(line)

            line = self.unreachable(line)

            line = self.constant_propagation(line)

            line = self.constant_folding(line)

            line = self.copy_propagation(line)

            line = self.algebraic(line)

            line = self.strength_reduction(line)

            line = self.cse(line)

            line = self.loop_optimization(line)

            line = self.function_opt(line)

            line = self.dead_code(line)

            self.optimized.append(line)

        return self.optimized



# ------------------------------------------------
# MAIN
# ------------------------------------------------

def main():

    file = "sample.cpp.004t.gimple"

    with open(file) as f:
        lines = f.readlines()


    print("\n========== UNOPTIMIZED TAC ==========\n")

    for l in lines:
        print(l.strip())


    optimizer = TACOptimizer(lines)

    optimized = optimizer.optimize()


    print("\n========== OPTIMIZED TAC ==========\n")

    for l in optimized:
        print(l)



if __name__ == "__main__":
    main()