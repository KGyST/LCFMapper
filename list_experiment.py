import pprint

a = [1]

def func(l:list):
    l.append(2)

func(a)
pprint.pprint(a)