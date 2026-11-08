import re
rows=[l.rstrip("\n").split(";") for l in open("p3.csv",encoding="utf8") if l.strip()]
drop=["Roll Tide","Tears of a Clown","The Spirit of Adventure","Skyfall","My Heart Will Go On (Titanic","Circle of Life (Instr","Hornpipe Medley","Narnia: The Battle","Harry in Winter","Journey to the Line","Arrival of the Birds","A Million Dreams","One Day More","Somewhere;","Kimba","Starbuck on the Beach"]
ren={ # titulo -> (artista, feat)
"Beauty and the Beast":("Angela Lansbury",""),
"A Whole New World":("Brad Kane & Lea Salonga",""),
"Part of Your World":("Jodi Benson",""),
"Under the Sea":("Samuel E. Wright",""),
"Be Our Guest":("Jerry Orbach",""),
"Colors of the Wind":("Judy Kuhn",""),
"Reflection":("Christina Aguilera",""),
"Go the Distance":("Roger Bart",""),
"Do You Want to Build a Snowman?":("Kristen Bell",""),
"For the First Time in Forever":("Kristen Bell & Idina Menzel",""),
"We Don't Talk About Bruno":("Carolina Gaitán",""),
"How Far I'll Go":("Auliʻi Cravalho",""),
"You're Welcome":("Dwayne Johnson",""),
"Surface Pressure":("Jessica Darrow",""),
"My Shot":("Lin-Manuel Miranda",""),
"Wait for It":("Leslie Odom Jr.",""),
"This Is Me":("Keala Settle",""),
"Rewrite the Stars":("Zac Efron & Zendaya",""),
"City of Stars":("Ryan Gosling & Emma Stone",""),
"The Phantom of the Opera":("Sarah Brightman & Michael Crawford",""),
"Memory":("Elaine Paige",""),
"I Dreamed a Dream":("Anne Hathaway",""),
"Defying Gravity":("Idina Menzel & Kristin Chenoweth",""),
"My Favorite Things":("Julie Andrews",""),
"Do-Re-Mi":("Julie Andrews",""),
"Supercalifragilisticexpialidocious":("Julie Andrews & Dick Van Dyke",""),
"Chim Chim Cher-ee":("Dick Van Dyke",""),
"I See You (Theme from Avatar)":("Leona Lewis",""),
"May It Be":("Enya",""),
"Gollum's Song":("Emiliana Torrini",""),
}
out=[]
for r in rows:
    key=r[0]+";"+r[1]
    if any(d in key for d in drop): continue
    if r[1] in ren:
        r[0]=ren[r[1]][0]; r[5]=ren[r[1]][1]
    r[0]=r[0].replace("Hisaishi Joe","Joe Hisaishi")
    out.append(";".join(r))
open("p3a.csv","w",encoding="utf8").write("\n".join(out)+"\n")
print(len(out))
