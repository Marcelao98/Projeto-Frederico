import sys
P = {
# preset: genero, energia, animacao, climas, ocasioes, temas, instrumentos, idioma
'fc':('funk-carioca',4,4,'animado|festivo|alegre','festa|balada','danca|curticao','','pt'),
'fm':('funk-melody',3,4,'romantico|alegre|nostalgico','festa','amor|paixao','','pt'),
'fo':('funk-ostentacao',4,5,'confiante|festivo|animado','balada|esquenta','ostentacao|curticao','','pt'),
'fx':('mandelao',5,4,'animado|sensual|confiante','balada|esquenta','pegacao|curticao','','pt'),
'f150':('funk-150',5,5,'animado|empolgante|festivo','balada|treino','danca|curticao','','pt'),
'fs':('funk-carioca',4,4,'sensual|animado|confiante','balada|esquenta','pegacao|danca','','pt'),
'fpop':('funk-carioca',4,5,'animado|alegre|festivo','balada|esquenta','danca|curticao','','pt'),
'fcon':('funk-consciente',3,3,'contemplativo|esperancoso|confiante','','critica-social|superacao','','pt'),
'fa':('funk-automotivo',5,4,'agressivo|animado|empolgante','treino|balada','danca','sintetizador','pt'),
'rc':('rap-nacional',3,2,'dramatico|sombrio|contemplativo','','critica-social|quebrada','','pt'),
'rm':('rap-nacional',3,3,'confiante|contemplativo|esperancoso','','superacao|quebrada','','pt'),
'rl':('rap-nacional',3,4,'alegre|confiante|animado','','curticao|amizade','','pt'),
'rr':('rap-nacional',2,3,'romantico|melancolico|saudade','','amor|paixao','','pt'),
'rs':('rap-nacional',3,3,'contemplativo|melancolico|esperancoso','','critica-social|liberdade','','pt'),
'tr':('trap-nacional',4,3,'confiante|sombrio|agressivo','treino','ostentacao|quebrada','sintetizador','pt'),
'dr':('drill',4,2,'sombrio|agressivo|tenso','','quebrada','','pt'),
'lv':('louvor',2,3,'sagrado|contemplativo|esperancoso','momento-de-fe','fe','piano','pt'),
'le':('louvor',4,4,'sagrado|empolgante|esperancoso','momento-de-fe','fe','','pt'),
'lc':('louvor',3,4,'sagrado|alegre|esperancoso','momento-de-fe','fe','','pt'),
'gp':('gospel-pop',3,4,'esperancoso|alegre|sagrado','momento-de-fe','fe|superacao','','pt'),
'gb':('black-gospel',4,4,'sagrado|empolgante|alegre','momento-de-fe','fe','coral','en'),
'ge':('louvor',3,4,'sagrado|esperancoso|empolgante','momento-de-fe','fe','','en'),
'gl':('louvor',2,3,'sagrado|contemplativo|esperancoso','momento-de-fe','fe','piano','en'),
'mc':('musica-catolica',2,3,'sagrado|calmo|esperancoso','momento-de-fe','fe','violao','pt'),
'mce':('musica-catolica',3,4,'sagrado|alegre|festivo','momento-de-fe','fe','','pt'),
'hn':('louvor',2,3,'sagrado|nostalgico|aconchegante','momento-de-fe','fe','coral|orgao','pt'),
'nt':('louvor',2,3,'sagrado|aconchegante|calmo','natal|momento-de-fe','fe','coral','pt'),
'ci':('cantiga-de-roda',3,4,'alegre|aconchegante|nostalgico','criancas','infancia','','pt'),
'cn':('cantiga-de-roda',2,3,'aconchegante|calmo|nostalgico','criancas|dormir','infancia|familia','','pt'),
'im':('musica-infantil',3,5,'alegre|engracado|animado','criancas','infancia|zoeira','','pt'),
'ia':('musica-infantil',3,4,'alegre|aconchegante|nostalgico','criancas','infancia','','pt'),
'ib':('musica-infantil',2,3,'aconchegante|calmo|sonhador','criancas|dormir','infancia','','pt'),
'id':('desenho-animado',4,5,'alegre|epico|animado','criancas','infancia','','pt'),
}
OVER = {'rap-nacional-alt':None}
def build(src):
    out=[]
    for ln in src.strip().splitlines():
        ln=ln.strip()
        if not ln or ln.startswith('#'): continue
        f=ln.split('|')
        f+=['']*(9-len(f))
        art,tit,ano,pr,pop,fl,feat,nota,idi=f[:9]
        g,e,a,cl,oc,tm,ins,ida=P[pr]
        if idi: ida=idi
        if ida=='' : pass
        row=[art,tit,ano,g,'',feat,ida,'1',str(e),str(a),cl,oc,tm,ins,pop,
             '1' if 'E' in fl else '0','1' if 'C' in fl else '0','1' if 'X' in fl else '0','1' if 'V' in fl else '0',nota]
        for c in row: assert ';' not in c,(ln)
        out.append(';'.join(row))
    return out
if __name__=='__main__':
    src=''.join(open(p,encoding='utf-8').read()+'\n' for p in sys.argv[2:])
    rows=build(src)
    hdr='artista;titulo;ano;genero;genero2;feat;idioma;tem_voz;energia;animacao;climas;ocasioes;temas;instrumentos;popularidade;essencial;canta_junto;explicita;ao_vivo;nota'
    open(sys.argv[1],'w',encoding='utf-8').write(hdr+'\n'+'\n'.join(rows)+'\n')
    print(len(rows),'linhas; incertas:',sum(1 for p in sys.argv[2:] for l in open(p,encoding='utf-8') if '?' in l.split('|')[5:6][0:1][0] ) if False else '')
