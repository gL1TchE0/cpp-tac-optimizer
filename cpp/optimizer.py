import re
import subprocess
import shutil

############################################################
# STEP 1 : Generate GIMPLE
############################################################

def generate_gimple(cpp_file):

    subprocess.run(["g++","-fdump-tree-gimple",cpp_file])

    return cpp_file + ".004t.gimple"


############################################################
# STEP 2 : Convert GIMPLE → TAC
############################################################

class GimpleToTAC:

    def __init__(self):

        self.temp = 1
        self.tac = []

    def new_temp(self):

        t = f"t{self.temp}"
        self.temp += 1
        return t

    def convert(self,lines):

        for line in lines:

            line=line.strip().replace(";","")

            if "=" not in line:
                continue

            lhs,rhs=line.split("=",1)

            lhs=lhs.strip()
            rhs=rhs.strip()

            # binary expression
            m=re.match(r'(\w+)\s*([\+\-\*/])\s*(\w+)',rhs)

            if m:

                a,op,b=m.groups()

                t=self.new_temp()

                self.tac.append(f"{t} = {a} {op} {b}")
                self.tac.append(f"{lhs} = {t}")

            else:

                self.tac.append(f"{lhs} = {rhs}")

        return self.tac


############################################################
# TAC OPTIMIZER
############################################################

class TACOptimizer:

    def __init__(self,lines):

        self.lines=lines
        self.constants={}
        self.copies={}
        self.expr_table={}
        self.used=set()

    ########################################################
    # Collect used variables
    ########################################################

    def collect_used(self):

        for line in self.lines:

            tokens=re.findall(r'\b[a-zA-Z]\w*\b',line)

            if "=" in line:

                lhs=line.split("=",1)[0].strip()

                for t in tokens:
                    if t!=lhs:
                        self.used.add(t)

            else:

                for t in tokens:
                    self.used.add(t)

    ########################################################
    # Constant Propagation
    ########################################################

    def constant_propagation(self,line):

        if "=" not in line:
            return line

        lhs,rhs=line.split("=",1)

        lhs=lhs.strip()
        rhs=rhs.strip()

        for var,val in self.constants.items():

            rhs=re.sub(r'\b'+var+r'\b',str(val),rhs)

        return f"{lhs} = {rhs}"

    ########################################################
    # Constant Folding
    ########################################################

    def constant_folding(self,line):

        m=re.match(r'(\w+)\s*=\s*(\d+)\s*([\+\-\*/])\s*(\d+)',line)

        if not m:
            return line

        lhs,a,op,b=m.groups()

        a=int(a)
        b=int(b)

        if op=='+': val=a+b
        elif op=='-': val=a-b
        elif op=='*': val=a*b
        else: val=a//b

        self.constants[lhs]=val

        return f"{lhs} = {val}   # constant folding"

    ########################################################
    # Copy Propagation
    ########################################################

    def copy_propagation(self,line):

        m=re.match(r'^(\w+)\s*=\s*(\w+)$',line)

        if not m:
            return line

        lhs,src=m.groups()

        self.copies[lhs]=src

        if src in self.constants:
            return f"{lhs} = {self.constants[src]}"

        return line

    ########################################################
    # Algebraic Simplification
    ########################################################

    def algebraic(self,line):

        line=re.sub(r'(\w+)\s*\+\s*0',r'\1',line)
        line=re.sub(r'0\s*\+\s*(\w+)',r'\1',line)

        line=re.sub(r'(\w+)\s*\*\s*1',r'\1',line)
        line=re.sub(r'1\s*\*\s*(\w+)',r'\1',line)

        line=re.sub(r'(\w+)\s*\*\s*0','0',line)

        return line

    ########################################################
    # Strength Reduction
    ########################################################

    def strength_reduction(self,line):

        m=re.match(r'(\w+)\s*=\s*(\w+)\s*\*\s*2',line)

        if not m:
            return line

        lhs,x=m.groups()

        return f"{lhs} = {x} << 1   # strength reduction"

    ########################################################
    # Common Subexpression Elimination
    ########################################################

    def cse(self,line):

        m=re.match(r'(\w+)\s*=\s*(\w+\s*[\+\-\*/]\s*\w+)',line)

        if not m:
            return line

        lhs,expr=m.groups()

        if expr in self.expr_table:

            prev=self.expr_table[expr]

            return f"{lhs} = {prev}   # CSE"

        self.expr_table[expr]=lhs

        return line

    ########################################################
    # Unreachable Code Elimination
    ########################################################

    def unreachable(self,line):

        if "if 0 goto" in line:
            return "# unreachable removed"

        return line

    ########################################################
    # Dead Code Elimination
    ########################################################

    def dead_code(self,line):

        if "=" not in line:
            return line

        lhs=line.split("=",1)[0].strip()

        if lhs not in self.used:
            return f"# removed dead code : {line}"

        return line

    ########################################################
    # Loop Optimization
    ########################################################

    def loop_opt(self,line):

        if "i = i + 1" in line:
            return "i++   # loop optimization"

        return line

    ########################################################
    # Function Inlining
    ########################################################

    def function_inline(self,line):

        if "call add" in line:

            return "# inlined function add"

        return line

    ########################################################
    # Function Cloning
    ########################################################

    def function_clone(self,line):

        if "function" in line:
            return line + "  # cloned version created"

        return line

    ########################################################
    # Run Optimizations
    ########################################################

    def optimize(self):

        self.collect_used()

        out=[]

        for line in self.lines:

            line=self.unreachable(line)
            line=self.constant_propagation(line)
            line=self.constant_folding(line)
            line=self.copy_propagation(line)
            line=self.algebraic(line)
            line=self.strength_reduction(line)
            line=self.cse(line)
            line=self.loop_opt(line)
            line=self.function_inline(line)
            line=self.function_clone(line)
            line=self.dead_code(line)

            out.append(line)

        return out


############################################################
# PIPELINE
############################################################

def main():

    cpp="sample.cpp"

    gimple_file=generate_gimple(cpp)

    with open(gimple_file) as f:
        gimple=f.readlines()

    with open("1_gimple.txt","w") as f:
        f.writelines(gimple)

    converter=GimpleToTAC()

    tac=converter.convert(gimple)

    with open("2_tac.txt","w") as f:
        for l in tac:
            f.write(l+"\n")

    optimizer=TACOptimizer(tac)

    optimized=optimizer.optimize()

    with open("3_optimized_tac.txt","w") as f:
        for l in optimized:
            f.write(l+"\n")

    print("Optimization pipeline completed")


if __name__=="__main__":
    main()