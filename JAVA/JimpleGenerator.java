import soot.*;
import soot.options.Options;
import soot.jimple.*;
import java.io.*;
import java.util.*;

/**
 * JimpleGenerator - Generates Jimple (TAC) from Java bytecode using Soot
 * Jimple is Soot's three-address code intermediate representation
 */
public class JimpleGenerator {
    
    public static void main(String[] args) {
        if (args.length < 1) {
            System.out.println("Usage: java JimpleGenerator <className1> [className2] ...");
            System.out.println("Example: java JimpleGenerator TestProgram1 TestProgram2");
            System.exit(1);
        }
        
        // Configure Soot once for all classes
        configureSoot();
        
        // Add all classes as basic classes with SIGNATURES level
        for (String className : args) {
            Scene.v().addBasicClass(className, soot.SootClass.SIGNATURES);
        }
        
        // Load necessary classes first
        Scene.v().loadNecessaryClasses();
        
        // Generate Jimple for each class
        for (String className : args) {
            System.out.println("Generating Jimple for: " + className);
            generateJimple(className);
        }
        
        System.out.println("\nJimple generation complete!");
    }
    
    private static void configureSoot() {
        // Reset Soot
        G.reset();
        
        // Set Soot options
        Options.v().set_prepend_classpath(true);
        Options.v().set_allow_phantom_refs(true);
        Options.v().set_output_format(Options.output_format_jimple);
        Options.v().set_keep_line_number(true);
        Options.v().set_whole_program(true);  // Changed to true
        
        // Set classpath to current directory
        String classpath = System.getProperty("java.class.path");
        String currentDir = System.getProperty("user.dir");
        Options.v().set_soot_classpath(classpath + File.pathSeparator + currentDir);
        
        // Set output directory
        Options.v().set_output_dir("./jimple_output");
        
        // Create output directory
        new File("./jimple_output").mkdirs();
    }
    
    private static void generateJimple(String className) {
        try {
            // Get the already loaded class
            SootClass sootClass = Scene.v().getSootClass(className);
            sootClass.setApplicationClass();
            
            // Generate Jimple for each method
            for (SootMethod method : sootClass.getMethods()) {
                if (method.isConcrete()) {
                    Body body = method.retrieveActiveBody();
                    
                    // Write Jimple to file - sanitize method name for Windows
                    String methodName = method.getName().replace("<", "").replace(">", "");
                    String outputFile = "./jimple_output/" + className + "." + 
                                       methodName + ".jimple";
                    writeJimpleToFile(method, body, outputFile);
                    
                    System.out.println("  Generated: " + outputFile);
                }
            }
            
            // Also write complete class Jimple
            String classOutputFile = "./jimple_output/" + className + ".jimple";
            writeClassJimpleToFile(sootClass, classOutputFile);
            System.out.println("  Generated: " + classOutputFile);
            
        } catch (Exception e) {
            System.err.println("Error generating Jimple for " + className + ": " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    private static void writeJimpleToFile(SootMethod method, Body body, String filename) {
        try (PrintWriter writer = new PrintWriter(new FileWriter(filename))) {
            writer.println("// Method: " + method.getSignature());
            writer.println("// Jimple (Three-Address Code) Representation");
            writer.println();
            Printer.v().printTo(body, writer);
        } catch (IOException e) {
            System.err.println("Error writing to file: " + filename);
            e.printStackTrace();
        }
    }
    
    private static void writeClassJimpleToFile(SootClass sootClass, String filename) {
        try (PrintWriter writer = new PrintWriter(new FileWriter(filename))) {
            writer.println("// Class: " + sootClass.getName());
            writer.println("// Complete Jimple Representation");
            writer.println();
            Printer.v().printTo(sootClass, writer);
        } catch (IOException e) {
            System.err.println("Error writing to file: " + filename);
            e.printStackTrace();
        }
    }
}
