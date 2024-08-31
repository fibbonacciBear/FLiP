"""
This module defines base classes that represent the abstract syntax
for formulas and terms.  It also provides methods for matching and
substitution.  The matching methods also check side conditions
involving bound and free variables.
"""

from operator import concat      # for free method in Compound
from copy import copy, deepcopy  # for subst methods
from functools import reduce

class Symbol(object):
  """
  Base class for syntax elements without arguments:
  T, F, propositional letters, variables, and match placeholders.
  """
  # Each Symbol instance has its own name, printed by both ppf and pform.
  # Kaye uses a single letter for the name, but any Python identifier will work
  def __init__(self, name):
    self.name = name

  def pform(self):
    return self.name

  def ppf(self):
    return self.pform()
  
  def mismatch(self, formula, subformulas, bound,free, other_errors,rule_type):
    if not isinstance(formula, type(self)): # pattern can be superclass
      return [ (self, formula, copy(bound)) ]  # formula is not a Symbol
    elif self.name != formula.name:
      return [ (self, formula, copy(bound)) ]  # different symbol
    else:
      return [] # symbols match

  def equal(self, other):
    'Structural equality,== tests instance identity. Dont redefine __eq__ now'
    return type(self) == type(other) and self.name == other.name
    
  def subst(self, substitutions):
    for key, value in substitutions.items():
      if self.equal(key):
        return deepcopy(value) #substitutions is dict,only one match possible
    return deepcopy(self)  # no match

  def generate(self, subformulas, otherdata, other_errors):
    'return formula generated by substituting subformulas into pattern (self)'
    return self.subst(subformulas)

class Formula(object):
  """
  Marker class for Kaye's formulas: predicates, expressions with Boolean values
  Top-level expression in a proof step must be a Formula
  Arguments to logical operators must be Formulas
  """
  pass

class Term(object):
  """
  Marker class for terms: expressions with non-Boolean values
  Arguments to functions and relations must be Terms
  """
  pass

class Letter(Symbol, Formula):
  """
  Kaye's 'propositional letters' (p. 64)
  A symbol that stands for a proposition that has a boolean truth value.
  Letters are actually relations with no arguments.  They are *not* variables.
  Kaye uses single letters for these, but any Python identifier will work.
  """
  def __init__(self, name):
    Symbol.__init__(self, name)

  def free(self):
    return []      # no free variables.  Letter is a relation with no args.

class Variable(Symbol, Term):
  """
  Kaye's variables, defs. 9.1, 9.2, 9.4 (pp. 117 - 119)
  """
  def __init__(self, name):
    Symbol.__init__(self, name)

  def free(self):
    return [ self ]

class Compound(object):
  """
  Base class for syntax elements with one or more arguments:
  Functions, relations, formulas, logical operators, quantifiers, ...
  """
  def __init__(self, *args): 
    self.args = list(args)   # mutable but update only in copied instance

  # pform prints class name.  same pform is used by all subclasses
  def pform(self):
    name = self.__class__.__name__
    arglist = ','.join([ a.pform() for a in self.args ])
    return '%s(%s)' % (name, arglist)

  # ppf prints class name unless subclass prints symbol  
  def ppf(self):
    return self.pform()

  def free(self):
    freevs = reduce(concat, map(lambda a: a.free(), self.args))
    return remove_dups(freevs)

  def mismatch(self, formula, subformulas, bound,free, other_errors,rule_type):
    if isinstance(formula, Let) and not isinstance(self, Let):
      return Compound.mismatch(self, formula.formula, subformulas, bound, 
                             free, other_errors, rule_type)
    elif not isinstance(formula, type(self)): # pattern can be superclass
      return [(self, formula, copy(bound))] # wrong formula class, outermost op
    else:
      mismatches = []
      for i in range(len(formula.args)):
        mm = self.args[i].mismatch(formula.args[i], subformulas, 
                                            bound,free, other_errors,rule_type)
        if other_errors:
          return False 
        else:
          mismatches += mm
      return mismatches

  def equal(self, other):
    'Structural equality,== tests instance identity. Dont redefine __eq__ now'
    if type(self) != type(other):
      return False
    for i, arg in enumerate(self.args):
      if not arg.equal(other.args[i]):
        return False
    return True

  def subst(self, substitutions):
    for key, value in substitutions.items():
      if self.equal(key):
        return deepcopy(value) # replace whole formula
    formcopy = deepcopy(self)  # must have deepcopy not copy here
    for i, form in enumerate(self.args):
      # substituting into copy achieves simultaneous not sequential subst.
      formcopy.args[i] = form.subst(substitutions)
    return formcopy # deep copy of self if no substitutions

  def generate(self, subformulas, otherdata, other_errors):
    'return formula generated by substituting subformulas into pattern (self)'
    return self.subst(subformulas)

class Relation(Compound, Formula):
  """
  Base class for relations of any arity with prefix constructor syntax P(x) etc
  """
  def __init__(self, *args):
    check_type(self, Term, *args)
    Compound.__init__(self, *args)  # assigns args to self.args

class Function(Compound, Term):
  """
  Base class for functions of any arity with prefix constructor syntax f(x) etc
  """
  def __init__(self, *args):
    check_type(self, Term, *args)
    Compound.__init__(self, *args)  # assigns args to self.args

class Prefix(Compound):
  """
  Unary operator with symbol and prefix syntax, base class for ~, A, E etc.
  """
  def __init__(self, *args):
    check_count(self, 1, *args)
    Compound.__init__(self, *args)
    self.symbol = '?'          # each subclass will rebind

  def ppf(self):
    fmt = '%s%s'      # no parens
    if isinstance(self.args[0], Infix): # ... and higher arities
      fmt = '%s(%s)'  # parens
    return fmt % (self.symbol, self.args[0].ppf())  

class Infix(Compound):
  """
  Binary operator with symbol and infix syntax, base class for &, <, etc.
  """
  def __init__(self, *args):
    check_count(self, 2, *args)
    Compound.__init__(self, *args)
    self.symbol = '?'  # each subclass will rebind

  def ppf(self):
    f = [ '%s', '%s' ]  # format strings, no parens
    for i, a in enumerate(self.args):
      if isinstance(a, Infix):
        f[i] = '(%s)'   # parens
    format = f[0]+' %s '+f[1]
    return format % (self.args[0].ppf(), self.symbol, self.args[1].ppf())

class InfixRelation(Infix, Formula):
  """
  Base class for infix binary relations: = in fol, <, /< in Kaye's poset
  Arguments must all be Term
  """
  def __init__(self, *args):
    Infix.__init__(self, *args)
    check_type(self, Term, *args) # check types after check count in Infix...

class PrefixLogical(Prefix, Formula):
  """
  Base class for prefix unary logical operators, for example Not
  Argument must be Formula
  """
  def __init__(self, *args):
    Prefix.__init__(self, *args)
    check_type(self, Formula, *args) # check types after check count

class InfixLogical(Infix, Formula):
  """
  Base class for infix binary logical operators, for example And, Or, Impl
  Arguments must all be Formula
  """
  def __init__(self, *args):
    Infix.__init__(self, *args)      # assigns *args to self.args
    check_type(self, Formula, *args) # check types after check count


class Quantifier(Compound, Formula):
  """
  Base class for quantifiers A (All) and E (Exists), but also Let meta-formula
  Like Q in Kaye ex 9.33
  Two arguments, first must be Variable, second must be Formula
  """
  def __init__(self, *args):
    check_count(self, 2, *args)
    check_type(self, Variable, args[0])
    check_type(self, Formula, args[1]) 
    Compound.__init__(self, *args)
    self.bound = self.args[0]     # variable
    self.formula = self.args[1]   # formula

  def pform(self):
    return '%s(%s, %s)' % \
      (self.__class__.__name__,self.bound.name,self.formula.pform())

  def ppf(self):
    fmt = '%s%s.%s'     # no parens around formula
    if isinstance(self.formula, Infix):
      fmt = '%s%s.(%s)'  # parens
    return fmt % (self.__class__.__name__, self.bound.name, self.formula.ppf())

  def free(self):
    return [ v for v in self.formula.free() if not v == self.bound ]
                  
  def mismatch(self, formula, subformulas, bound,free, other_errors,rule_type):
    bound.append(self.bound)
    return Compound.mismatch(self, formula, subformulas, bound, free, 
                             other_errors, rule_type)
   
  def subst(self, substitutions):
    qformcopy = Compound.subst(self, substitutions) # rebinds args only
    qformcopy.bound = qformcopy.args[0]   # variable
    qformcopy.formula = qformcopy.args[1] # formula    
    return qformcopy

  def generate(self, subformulas, otherdata, other_errors):
    if self.bound in subformulas:
      # Ai, bound variable is in premises
      bound = subformulas[self.bound]  
    else:
      # Ei, otherdata is a tuple, otherdata[0] is the dictionary {t1:v1}
      if len(otherdata) < 1 or not isinstance(otherdata[0], dict):
        other_errors.append(
          'Fail: apply command requires argument: {term:variable}')
        return False
      pair = list((otherdata[0].items()))[0]
      term = pair[0]
      bound = pair[1]
      if not (isinstance(bound,Variable) and isinstance(term,Term)):
        other_errors.append(
          'Fail: apply command requires argument: {term:variable}')
        return False
    Q = self.__class__  # subclass, might be A or E
    return Q(bound, self.formula.generate(subformulas,otherdata,other_errors))

# Meta-formulas

# Values for rule_type used in nd proofs, checked in Meta-formula classes here
# assumer, assumer case, discharger, other, unknown. 
# Use short identifiers that don't conflict w/ variable names.
ar, ac, dr, xr, xx = 'ar', 'ac', 'dr', 'xr', 'xx'

class New(Relation):
  """
  Introduce a new free variable
  Used in fol to prepare for A-intro.
  Assert New(x) with the new rule to start a subproof with new free variable x
  New(x) mismatch method returns other_error if x is already free in the proof
  Subclass of Relation because it has same syntax and arg checks as any rel'n
  """
  def __init__(self, *args):
    check_count(self, 1, *args)
    check_type(self, Variable, *args)
    Relation.__init__(self, *args)
    self.variable = self.args[0]

  def pform(self):
    return 'New(%s)' % self.variable.pform()

  def ppf(self):
    return 'Let %s be arbitrary' % self.variable.ppf()

  def free(self):
    return self.variable.free()  
    
  def mismatch(self, formula, subformulas, bound,free, other_errors,rule_type):
    if rule_type == ar: # assume step, check that variable is new
      if formula.variable in free:
        other_errors.append(
          'Fail: variable %s already appears free in proof among %s' % \
             (formula.variable.ppf(), ppflist(free)))
        return False
    return Compound.mismatch(self, formula, subformulas, bound, 
                             free, other_errors, rule_type)
    #return [] # nothing else to check, New step will never be used as premise


class Let(Quantifier):
  """
  Assert a formula containing a new free variable
  Used in fol to prepare for E-elim.
  Assert Let(x,P(x)) with the let rule to assume P(x) with new free variable x
  Let(x,P(x)) mismatch method returns other_error if x is already free in proof
  Subclass of Quantifier because it has same syntax and arg checks as any Q.
  """
  def __init__(self, *args):
    Quantifier.__init__(self, *args)
    # self.formula = self.args[1] # already assigned in Quantifier.__init__
    self.variable = self.args[0]  # already assigned to self.bound in Quant.

  def pform(self):
    return 'Let(%s,%s)' % (self.variable.pform(), self.formula.pform())

  def ppf(self):
    return 'Let %s satisfy %s' % (self.variable.ppf(), self.formula.ppf())

  def free(self):
    return self.formula.free()  
    
  def mismatch(self, formula, subformulas, bound,free, other_errors,rule_type):
    # mismatch checks variable only in assume step where it is introduced
    if rule_type == ar: # assume step, check that variable is new
      if formula.variable in free:  
        other_errors.append(
          'Fail: variable %s already appears free in proof among %s' % \
          (formula.variable.ppf(), ppflist(free)))
        return False
    #if isinstance(formula, Let): # this is just ar
    if rule_type == ar or rule_type == dr:
      # match the entire Let pattern 
      return Compound.mismatch(self, formula, subformulas, bound, 
                             free, other_errors, rule_type)
    else:
      # just match the formula part of the Let pattern
      return self.formula.mismatch(formula, subformulas, bound, 
                             free, other_errors, rule_type)

class Apply(Compound, Formula):
  """
  Metaformula. Commands prover to generate conclusion from rule and premises
  """
  # Inherit Compound to get its pform method for informative error messages
  def __init__(self, *args):
    Compound.__init__(self, *args)  # assigns args to self.args


# Placeholders that only appear in rules, not in the proofs themselves

class Placeholder(Symbol):
  """
  Placeholder m1, m2, ... that matches formula or subformula
  """
  def __init__(self, name):
    Symbol.__init__(self, name)

  def mismatch(self, formula, subformulas, bound,free, other_errors,rule_type):
    if self in subformulas:
      return subformulas[self].mismatch(formula, subformulas, 
                                        bound, free, other_errors, rule_type)
    else:
      subformulas.update({ self : formula })
      return [] # formula matches this Placeholder 
    
# Marked placeholders that appear where a particular argument type is required

class FormulaPlaceholder(Placeholder, Formula):
  pass

class TermPlaceholder(Placeholder, Term):
  pass

class VariablePlaceholder(Placeholder, Variable):
  pass


# Placeholders that also support substitution

class Subst(Symbol, Formula):
  """
  Placeholder that also supports substitution, as in Substitute rule:
   sub: [ Equal(t1,s1), S1(t1), S1({t1:s1}) ],
  The mismatch method does *not* check that *all* occurrences are substituted.
  Sufficient for sub and Ei rules, use SubstAll for others
  """
  # In S1(t1), does *not* check that t1 occurs in S1
  # Subst is a placeholder but doesn't inherit anything from Placeholder class
  # Don't use Symbol.__init__ here
  def __init__(self, arg):
    self.name = self.pattern.name  # subclass assigns self.pattern
    if isinstance(arg, dict):
      self.substitutions = arg.items() # convert dictionary to list of pairs
    elif isinstance(arg, Symbol):
      self.substitutions = [(arg,arg)] # HACK to accommodate P(v1)
    else:
      self.substitutions = []
    # If the argument is not a dictionary it is simply ignored!
    # The rule looks nice with P1(v1) but this code doesn't use v1 at all.

  def mismatch(self, formula, subformulas, bound,free, other_errors,rule_type):
    if self.pattern not in subformulas:
      subformulas.update({ self.pattern : formula })
      return [] # formula matches this Placeholder 
    else: 
    # self.pattern is premise P1. formula is conclusion, P1 with substitutions
    # First of each mismatches tuple is source subformula from P1 in premise
    # Second of tuple is replacement subformula from P1({*:*}) in conclusion
     mismatches= self.pattern.mismatch(formula,subformulas,bound,free,
                                      other_errors, rule_type)
     m_mismatches = [] # invalid mismatches, nonempty indicates failure
     for source_subformula, replacement_subformula, bound in mismatches:
      # sub: source_key,replacement_key are placeholders t1,s1 in Equal premise
      #  t1, s1, P1 are all keys in subformulas
      # Ae: source_key is placeholder v1 for bound variable in premise
      #  replacement_key is placeholder t1 for replacement term in conclusion
      # Ei: source_key is placeholder t1 for source term
      #  replacement_key is placeholder v1 for bound variable in conclusion
      # Ae,Ei: v1, P1 are keys in subformulas, but t1 is not
      for source_key, replacement_key in self.substitutions:
        # subformulas is dictionary from placeholders t1,s1,v1 to (sub)formulas
        # Case analysis enables this one method to work for all sub and Q rules
        if source_key in subformulas: # Ei source_key t1 is not in subformulas
          source = subformulas[source_key]  # sub, Ae rules
        else:
          source = source_subformula # Ei premise in rule does not constrain t1
        if replacement_key in subformulas: #Ae replacement_key t1 not in subf.
          replacement = subformulas[replacement_key] # sub, Ei rules
        else:
          replacement = replacement_subformula #Ae premise doesn't constrain t1
        # Check side conditions on bound variables
        for descrip, term in (('source',source), ('replacement',replacement)):
          if list(filter(lambda v: v in bound, term.free())):
            other_errors.append(
              'Fail: %s term %s includes bound variable in %s' % \
               (descrip, term.pform(), ppflist(bound)))
            return False
        # Check that source in premise agrees with replacement in conclusion
        if not source_subformula.equal(source) or \
            not replacement_subformula.equal(replacement):
          m_mismatches.append((source_subformula, replacement_subformula,
                               copy(bound))) # indicate failure
     return m_mismatches # nonempty indicates failure
    
  def generate(self, subformulas, otherdata, other_errors):
    """
    Return formula generated by substituting subformulas into pattern (self),
    and then substituting into those as directed by self.substititions
    """
    form = self.pattern.subst(subformulas)
    subst_pairs = []
    for (k,v) in self.substitutions:
      # Handle all cases right here, not in subclasses SubstAll P1 and NotIn Q1
      # S1({t1:s1}) in sub, k is s1 term, v is t1 term
      if k in subformulas and v in subformulas: 
        subst_pairs.append((subformulas[k], subformulas[v]))
      # Q1{{v2:None}) in Ee, k is bound variable v2, v is None, no subst needed
      elif k in subformulas and not v: 
        pass
      # In following case, term t1 and bound variable v1 both from otherdata
      # S1({t1:v1}) in Ei, k is term t1, v is bound variable v1
      elif k not in subformulas and v not in subformulas:
        # otherdata has already been checked in Quantifier generate 
        k,v = list((otherdata[0].items()))[0] 
        subst_pairs.append((k,v))
      # In following cases, term t1 only is from otherdata
      elif len(otherdata) < 1 or not isinstance(otherdata[0],Term):
        other_errors.append(
          'Fail: apply command requires argument: term or variable')
        return False
      # P1({v1:t1}) in Ae, k is bound variable v1, v is term t1
      elif k in subformulas and v not in subformulas:
        subst_pairs.append((subformulas[k], otherdata[0]))
      # P1({t1:v1}) in Ai, k is term t1, v is bound variable v1
      elif k not in subformulas and v in subformulas: # Ai rule
        subst_pairs.append((otherdata[0], subformulas[v]))
    return form.subst(dict(subst_pairs))


class SubstAll(Subst, Formula):
  """
  Placeholder that also supports substitution of all occurences, 
  as in A-Elimination:
    Ae  :  [ A(v1,P1(v1)), P1({v1:t1}) ],
  The mismatch method here checks that *all* occurrences are substituted.
  Needed for Ae, Ai, Ee rules.  Use base class for sub, Ei rules.
  """
  # In P1(v1), does *not* check that v1 occurs in P1
  # SubstAll doesn't inherit any attributes from base class Subst 
  # but it does invoke Subst.__init__ here, and repeats Subst code in mismatch
  def __init__(self, *args):
    Subst.__init__(self, *args)

  # This mismatch method *does* check that *all* occurrences are substituted.
  def mismatch(self, formula, subformulas, bound,free, other_errors,rule_type):
   # Next four lines appear in Subst and all its subclasses.
   if self.pattern not in subformulas:
      subformulas.update({ self.pattern : formula })
      return [] # formula matches this Placeholder 
   else: 
    # Call base class mismatch method to do most error checking
    mismatches = Subst.mismatch(self, formula, subformulas, 
                               bound, free, other_errors, rule_type)
    if mismatches or other_errors:
     return mismatches # must be error other than all occurrences not replaced
    else:
     # no error, must find which substitutions were done
     # self.pattern is premise P1. formula is conclusion, P1 with substitutions
     # mismatches shows which substitutions were done, which must be correct
     #  otherwise Base.mismatch would have indicated error and returned, above
     mismatches = self.pattern.mismatch(formula,subformulas,bound,free,
                                        other_errors, rule_type)
     if other_errors:
       return False
     else:
       # Apply correct substitutions to all occurrences in P1 to get all_substs
       all_substs = \
        subformulas[self.pattern].subst(dict([(p,f) for (p,f,b) in mismatches]))
       # Compare all_substs to formula, which is the conclusion of the rule.
       # m_mismatches will be empty iff all substitutions were performed
       # use mismatch not equal because returned m_mismatches used in error msg
       m_mismatches=all_substs.mismatch(formula,subformulas,bound,free,
                                        other_errors, rule_type)
       if m_mismatches:
         other_errors.append(
          'Fail: Not all occurrences substituted the same way %s' % \
            ppfpairs([ (p,f) for (p,f,b) in mismatches ]))
         return False
       elif other_errors:
         return False
       else: 
         return []

class NotIn(Subst, Formula):
  """
  Placeholder that indicates a variable does *not* occur free in a formula,
  as used in E-Elimination rule, where Q1({v2:None}) says v2 is not free in Q1:
   Ee : [ E(v1, P1(v1)), [Let(v2,P1({v1:v2})), Q1({v2:None})], Q1({v2:None}) ]
  """
  # NotIn doesn't inherit any attributes from base class Subst 
  # but it does invoke Subst.__init__ here, and repeats Subst code in mismatch
  def __init__(self, *args):
    Subst.__init__(self, *args)
    
  def mismatch(self, formula, subformulas, bound,free, other_errors,rule_type):
   # Next four lines appear in Subst and all its subclasses.
   if self.pattern not in subformulas:
      subformulas.update({ self.pattern : formula })
      return [] # formula matches this Placeholder 
   else: 
    for v_key, v_code in self.substitutions:
      # This code doesn't use v_code at all
      # Rule looks nice with Q1({v2:None}) but this code doesn't check for None
      v = subformulas[v_key] 
      fvs = subformulas[self.pattern].free()
      if v in fvs:
        other_errors.append(
          'Fail: variable %s appears free in formula among %s' % \
             (v.ppf(), ppflist(fvs)))
        return False
    return subformulas[self.pattern].mismatch(formula, subformulas, bound, 
                                              free,other_errors,rule_type)


# utility functions

def check_count(self, count, *args):
  """
  Check number of args. self here is for error message
  This is a function, not a method.  It is used by several classes.
  """
  # return # uncomment this line to turn off argument count check
  n = len(args)
  if n != count:
    raise SyntaxError('%s requires %d arguments, found %d' % \
      (self.__class__.__name__, count, n))

def check_type(self, arg_type, *args):
  """
  Check that all args belong to arg_type. self here is for error message
  """
  # return # uncomment this line to turn off argument type check
  for i, a in enumerate(args):
    if not(isinstance(a, arg_type)):
      raise TypeError('%s argument %d, %s is %s, must be %s' % \
        (self.__class__.__name__, i, a.ppf(), type(a), arg_type))

def remove_dups(vs):
  'Return shallow copy of list with duplicates removed'
  vars = []
  for v in vs:
    if v not in vars:
      vars.append(v)
  return vars

# pretty-printing for bound/free, match/substitute lists and dictionaries

def ppflist(flist):
  """
  Pretty-print list of formulas
  """
  return [ v.ppf() for v in flist ]

def ppfpairs(fpairs):
  """
  Pretty-print list of formula pairs
  """
  return '{ %s }' % \
    ', '.join([ '(%s, %s)' % (p.ppf(), f.ppf()) for p, f in fpairs 
                                                if p and f ]) # Might be None

def ppfdict(fdict):
  """
  Pretty-print dictionary of formula to formula
  """
  return '{ %s }' % \
    ', '.join([ '%s:%s' % (p.ppf(), f.ppf()) for p, f in fdict.items() ])

def mm_args(self, formula, subformulas, bound, free, other_errors, rule_type):
  'Return list of some arguments to mismatch method, pretty-printed'
  return ('self %s, formula %s, subformulas %s' % \
          (self.ppf(), formula.ppf(), ppfdict(subformulas)))
