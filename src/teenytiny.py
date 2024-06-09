from lex import Lexer
from emit import Emitter
from parse import Parser
import sys

def main():
  print("Teeny Tiny Compiler")

  if len(sys.argv) != 2:
    sys.exit("Error: Compiler needs source file as argument")
  with open(sys.argv[1], 'r') as inputFile:
    source = inputFile.read()

  # Initialize the lexer and parser
  lexer = Lexer(source)
  emitter = Emitter("out.c")
  praser = Parser(lexer, emitter)

  praser.program() # Start the parser
  emitter.writeFile() # Write the output to a file
  print("Compiling completed")

main()