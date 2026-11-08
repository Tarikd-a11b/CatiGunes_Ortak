import sys,re,io
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
f=sys.argv[1]; a=int(sys.argv[2]) if len(sys.argv)>2 else 0; b=int(sys.argv[3]) if len(sys.argv)>3 else 10**9
t=open(f,encoding='utf-8').read()
m=list(re.finditer(r'\n\s*(References|REFERENCES|Bibliography|KAYNAKÇA|Kaynakça|Kaynaklar)\s*\n',t))
if m and m[-1].start()>len(t)*0.5: t=t[:m[-1].start()]
t=re.sub(r'[ \t]+',' ',t); t=re.sub(r'\n(?!\[\[)',' ',t)
print(len(t)); print(t[a:b])
