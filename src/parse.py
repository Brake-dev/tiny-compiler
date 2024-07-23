import sys
from lex import TokenType, Token, Lexer
from emit import Emitter

# Parser object keeps track of current token and checks if the code matches the grammar
class Parser:
  def __init__(self, lexer: Lexer, emitter: Emitter):
    self.lexer = lexer
    self.emitter = emitter

    self.symbols = set() # Variables declared so far
    self.labelsDeclared = set() # Labels declared so far
    self.labelsGotoed = set() # Labels goto'ed so far

    self.curToken: Token = None
    self.peekToken: Token = None
    self.nextToken()
    self.nextToken() #  Call this twice to initialize current and peek

  # Return true if the current token matches
  def checkToken(self, kind: TokenType):
    return kind == self.curToken.kind

  # Return true if the next token matches
  def checkPeek(self, kind: TokenType):
    return kind == self.peekToken.kind

  # Try to match current token. If not, error. Advances the current token.
  def match(self, kind: TokenType):
    if not self.checkToken(kind):
      self.abort("Expected: " + kind.name + ", got " + self.curToken.kind.name)
    self.nextToken()

  # Advances the current token
  def nextToken(self):
    self.curToken = self.peekToken
    self.peekToken = self.lexer.getToken()
    # No need to worry about passing the EOF, lexer handles that

  def abort(self, message):
    sys.exit("Error: " + message)

  # Production rules

  # program ::= {statement}
  def program(self):
    self.emitter.headerLine("#include <stdio.h>")
    self.emitter.headerLine("int main(void){")

    # Since some newlines are required in our grammaer, need to skip the excess
    while self.checkToken(TokenType.NEWLINE):
      self.nextToken()

    # Parse all the statements in the program
    while not self.checkToken(TokenType.EOF):
      self.statement()

    # Wrap things up
    self.emitter.emitLine("return 0;")
    self.emitter.emitLine("}")

    # Check that each label referenced in a GOTO is declared
    for label in self.labelsGotoed:
      if label not in self.labelsDeclared:
        self.abort("Attempting to GOTO to undeclared label: " + label)

  def ifElseStatement(self):
    if self.checkToken(TokenType.ELSEIF):
      self.nextToken()
      self.emitter.emit("}else if(")
      self.comparison()

      self.match(TokenType.THEN)
      self.nl()
      self.emitter.emitLine("){")

      # Zero or more statements in the body
      while not self.checkToken(TokenType.ENDIF):
        self.statement()

      self.match(TokenType.ENDIF)

      if (self.peekToken.kind != TokenType.ELSEIF and self.peekToken.kind != TokenType.ELSE):
        self.emitter.emitLine("}")

    return self.peekToken.kind == TokenType.ELSEIF

  # One of the following statements ...
  def statement(self):
    # Check the first token to see what kind of statement this is

    # "PRINT" (expression | string)
    if self.checkToken(TokenType.PRINT):
      self.nextToken()

      if self.checkToken(TokenType.STRING):
        # Simple string, so print it
        self.emitter.emitLine("printf(\"" + self.curToken.text + "\\n\");")
        self.nextToken()
      else:
        # Expect expression and print the result as a float
        self.emitter.emit("printf(\"%" + ".2f\\n\", (float)(")
        self.expression()
        self.emitter.emitLine("));")

    elif self.checkToken(TokenType.IF):
      self.nextToken()
      self.emitter.emit("if(")
      self.comparison()

      self.match(TokenType.THEN)
      self.nl()
      self.emitter.emitLine("){")

      # Zero or more statements in the body
      while not self.checkToken(TokenType.ENDIF):
        self.statement()

      self.match(TokenType.ENDIF)

      if (self.peekToken.kind != TokenType.ELSEIF and self.peekToken.kind != TokenType.ELSE):
        self.emitter.emitLine("}")
      else:
        self.nextToken()
        while(self.ifElseStatement()):
          self.nextToken()

        self.nextToken()
        if self.checkToken(TokenType.ELSE):
          self.nextToken()
          self.emitter.emit("}else")

          self.nl()
          self.emitter.emitLine("{")

          # Zero or more statements in the body
          while not self.checkToken(TokenType.ENDIF):
            self.statement()

          self.match(TokenType.ENDIF)
          self.emitter.emitLine("}")

    elif self.checkToken(TokenType.WHILE):
      self.nextToken()
      self.emitter.emit("while(")
      self.comparison()

      self.match(TokenType.REPEAT)
      self.nl()
      self.emitter.emitLine("){")

      # Zero or more statements in the loop body
      while not self.checkToken(TokenType.ENDWHILE):
        self.statement()

      self.match(TokenType.ENDWHILE)
      self.emitter.emitLine("}")
      
    # "LABEL" ident
    elif self.checkToken(TokenType.LABEL):
      self.nextToken()

      # Make sure this label doesn't already exist
      if self.curToken.text in self.labelsDeclared:
        self.abort("Label already exists: " + self.curToken.text)
      self.labelsDeclared.add(self.curToken.text)

      self.emitter.emitLine(self.curToken.text + ":")
      self.match(TokenType.IDENT)

    # "GOTO" ident
    elif self.checkToken(TokenType.GOTO):
      self.nextToken()
      self.labelsGotoed.add(self.curToken.text)
      self.emitter.emitLine("goto " + self.curToken.text + ";")
      self.match(TokenType.IDENT)

    # "INT" ident "=" expression
    elif self.checkToken(TokenType.INT):
      self.nextToken()

      if self.curToken.text not in self.symbols:
        self.symbols.add(self.curToken.text)
        self.emitter.headerLine("int " + self.curToken.text + ";")

      self.emitter.emit(self.curToken.text + " = ")
      self.match(TokenType.IDENT)
      self.match(TokenType.EQ)

      self.expression()
      self.emitter.emitLine(";")

    # "FLT" ident "=" expression
    elif self.checkToken(TokenType.FLT):
      self.nextToken()

      if self.curToken.text not in self.symbols:
        self.symbols.add(self.curToken.text)
        self.emitter.headerLine("float " + self.curToken.text + ";")

      self.emitter.emit(self.curToken.text + " = ")
      self.match(TokenType.IDENT)
      self.match(TokenType.EQ)

      self.expression()
      self.emitter.emitLine(";")

    # "STR" ident "=" value
    elif self.checkToken(TokenType.STR):
      self.nextToken()

      if self.curToken.text not in self.symbols:
        self.symbols.add(self.curToken.text)
        self.emitter.headerLine("char " + self.curToken.text + ";")

      self.emitter.emit(self.curToken.text + " = ")
      self.match(TokenType.IDENT)
      self.match(TokenType.EQ)
      self.emitter.emit("\"" + self.curToken.text + "\"")
      self.match(TokenType.STRING)

      self.emitter.emitLine(";")

    # "INPUT" ident
    elif self.checkToken(TokenType.INPUT):
      self.nextToken()

      # If variable doesn't already exist, declare it
      if self.curToken.text not in self.symbols:
        self.symbols.add(self.curToken.text)
        self.emitter.headerLine("float " + self.curToken.text + ";")

      # Emit scanf but also validate the input. If invalid, set the variable to 0 and clear the input
      self.emitter.emitLine("if(0 == scanf(\"%" + "f\", &" + self.curToken.text + ")) {")
      self.emitter.emitLine(self.curToken.text + " = 0;")
      self.emitter.emit("scanf(\"%")
      self.emitter.emitLine("*s\");")
      self.emitter.emitLine("}")
      self.match(TokenType.IDENT)

    elif self.checkToken(TokenType.ARRAYSTART):
      if self.curToken.text not in self.symbols:
        self.symbols.add(self.curToken.text)
        self.emitter.headerLine("char " + self.curToken.text + ";")

      arrayContent = str()
      arrayLength = 0

      if self.peekToken == TokenType.NUMBER:
        self.emitter.emit("float ")
      elif self.peekToken == TokenType.STRING:
        self.emitter.emit("char ")

      while self.curToken != TokenType.ARRAYEND:
        if self.curToken == TokenType.NUMBER or self.curToken == TokenType.STRING:
          arrayContent += self.curToken.text
          arrayLength += 1
        else:
          self.abort("Illegal character in an array " + self.curToken.text + ". Only numbers and strings are allowed.")

        if self.peekToken != TokenType.ARRAYEND:
          arrayContent += ", "

        self.nextToken()

      self.emitter.emit("[" + str(arrayLength) + "]")

      if arrayContent > 0:
        self.emitter.emit(" = {" + arrayContent + "};")

    # This is not a valid statement. Error.
    else:
      self.abort("Invalid statement at " + self.curToken.text + " (" + self.curToken.kind.name + ")")
    
    # Newline
    self.nl()

  # comparison ::= expression (("==" | "!=" | ">" | ">=" | "<" | "<=") expression)+
  def comparison(self):
    self.expression()
    # Must be at least comparison operator and another expression
    if self.isComparisonOperator():
      self.emitter.emit(self.curToken.text)
      self.nextToken()
      self.expression()
    # Can have 0 or more comparison operators and expressions
    while self.isComparisonOperator():
      self.emitter.emit(self.curToken.text)
      self.nextToken()
      self.expression()

    # Can have 0 or more +/- and expressions
    while self.checkToken(TokenType.PLUS) or self.checkToken(TokenType.MINUS):
      self.emitter.emit(self.curToken.text)
      self.nextToken()
      self.expression()
    
  # Return true if the current token is a comparison operator
  def isComparisonOperator(self):
    return self.checkToken(TokenType.GT) or self.checkToken(TokenType.GTEQ) or self.checkToken(TokenType.LT) or self.checkToken(TokenType.LTEQ) or self.checkToken(TokenType.EQEQ) or self.checkToken(TokenType.NOTEQ)

  # expression ::= term {( "-" | "+" ) term}
  def expression(self):
    self.term()
    # Can have 0 or more +/- and expressions
    while self.checkToken(TokenType.PLUS) or self.checkToken(TokenType.MINUS):
      self.emitter.emit(self.curToken.text)
      self.nextToken()
      self.term()

  # term ::= unary {( "/" | "*" ) unary}
  def term(self):
    self.unary()
    # Can have 0 or more *// and expressions.
    while self.checkToken(TokenType.ASTERISK) or self.checkToken(TokenType.SLASH):
      self.emitter.emit(self.curToken.text)
      self.nextToken()
      self.unary()

  # unary ::= ["+" | "-"] primary
  def unary(self):
    # Optional unary +/-
    if self.checkToken(TokenType.PLUS) or self.checkToken(TokenType.MINUS):
        self.emitter.emit(self.curToken.text)
        self.nextToken()        
    self.primary()

  # primary ::= number | ident
  def primary(self):
    if self.checkToken(TokenType.NUMBER):
      self.emitter.emit(self.curToken.text)
      self.nextToken()
    elif self.checkToken(TokenType.IDENT):
      # Ensure the variable already exists
      if self.curToken.text not in self.symbols:
        self.abort("Referencing variable before assignment: " + self.curToken.text)

      self.emitter.emit(self.curToken.text)
      self.nextToken()
    else:
      # Error
      self.abort("Unexpected token at " + self.curToken.text)

  # nl ::= '\n'+
  def nl(self):
    # Require at least one newline
    self.match(TokenType.NEWLINE)
    # But we will allow extra newlines too
    while self.checkToken(TokenType.NEWLINE):
      self.nextToken()