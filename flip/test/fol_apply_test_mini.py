from fol_session import *
from command_wrapper import *

def ex91Ae():
  pcheckp(Text('A-elim from Kaye ex 9.10'), comment)
  pcheckp(A(x,E(v,Equal(v,x))), given)
  prapply(Ae, 1, w) # for Ae must provide only replacement term t1 for {v1:t1}

clear()
ex91Ae()
print()