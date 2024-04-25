%s/&#x20/ /g
%s/<nowiki\/>»/»/g
%s/«<nowiki\/>/«/g

%s/hidden-ref//g
%s/ref-info//g
%s/<span class="citation">//g
%s/<span lang="\w\+">//g

"make refs separated:
%s/<\/ref>/\0/g

/языке
