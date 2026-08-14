""""""""""""""
" Indentation
""""""""""""""
syntax match t0 "\v^\s{0}\S.*$"
highlight link t0 T0
syntax match t4 "\v^\s{4}\S.*$"
highlight link t4 T4
syntax match t8 "\v^\s{8}\S.*$"
highlight link t8 T8
syntax match t12 "\v^\s{12}\S.*$"
highlight link t12 T12
syntax match t16 "\v^\s{16}\S.*$"
highlight link t16 T16
syntax match t20 "\v^\s{20}\S.*$"
highlight link t20 T20
syntax match t24 "\v^\s{24}\S.*$"
highlight link t24 T24
syntax match t28 "\v^\s{28}\S.*$"
highlight link t28 T28
syntax match t32 "\v^\s{32}\S.*$"
highlight link t32 T32

" T0?
highlight T4 ctermfg=darkgreen guifg=darkgreen
highlight T8 ctermfg=blue guifg=blue
highlight T12 ctermfg=yellow guifg=yellow
highlight T16 ctermfg=red guifg=red
highlight T20 ctermfg=darkgray guifg=darkgray
highlight T24 ctermfg=darkred guifg=darkred
highlight T28 ctermfg=white guifg=white
highlight T32 ctermfg=darkgreen guifg=darkgreen

""""""""""""""
" Text Tables
""""""""""""""
syntax match lightRow "\v\S.*┊.*" containedin=T4 contained
highlight link lightRow LightRow
syntax match darkRow "\v\S.*┆.*" containedin=T4 contained
highlight link darkRow DarkRow

highlight LightRow ctermfg=252
highlight DarkRow ctermfg=252 ctermbg=238

syntax match darkSepChar "\v┆" containedin=DarkRow contained
highlight link darkSepChar DarkSepChar
highlight DarkSepChar ctermfg=252

" syntax match tableHeaderChar "\v━" containedin=T4 contained
" highlight link tableHeaderChar TableHeaderChar
" highlight TableHeaderChar ctermfg=252

""""""""""""""
" Text Links
""""""""""""""

" define the syntax item for links, like (3920a)
" syntax match destLink "\v\[...\]" containedin=T0,T4,T8,T12,T16,T20,T24,T28,T32 contained
" highlight link destLink DestLink
" highlight DestLink ctermbg=blue guibg=blue ctermfg=white guifg=white

" syntax match sourceLink "\v\(...\)" containedin=T0,T4,T8,T12,T16,T20,T24,T28,T32 contained
" highlight link sourceLink SourceLink
" highlight SourceLink ctermbg=blue guibg=blue ctermfg=white guifg=white


""""""""""""""
" Flashcard
""""""""""""""
" - containedin keyword notifies vim that this pattern is within another pattern

" syntax match flashcardCloze containedin=T4,T8,T12,T16,T20,T24,T28,T32 "\v`[^`]+`"
syntax region flashcardCloze start=/\v`/ end=/\v`/ containedin=T4,T8,T12,T16,T20,T24,T28,T32
highlight link flashcardCloze Flashcard
highlight Flashcard ctermbg=darkblue guibg=darkblue ctermfg=white guifg=white

" Remove the wrap around colored beginning of line for flashcards when it spans multiple lines.
syntax match indentSpace "\v^\s+" containedin=T4,T8,T12,T16,T20,T24,T28,T32,flashcardCloze contained
highlight link indentSpace ISpace
highlight ISpace ctermfg=black guifg=black

""""""""""""""
" Notables
""""""""""""""
syntax match noteTag "\vNOTE" containedin=T0,T4,T8,T12,T16,T20,T24,T28,T32 contained
syntax match defTag "\vDEF" containedin=T0,T4,T8,T12,T16,T20,T24,T28,T32 contained
syntax match aliasTag "\vALIAS" containedin=T0,T4,T8,T12,T16,T20,T24,T28,T32 contained
syntax match procTag "\vPROC" containedin=T0,T4,T8,T12,T16,T20,T24,T28,T32 contained
syntax match procedureTag "\vPROCEDURE" containedin=T0,T4,T8,T12,T16,T20,T24,T28,T32 contained
syntax match exTag "\vEX" containedin=T0,T4,T8,T12,T16,T20,T24,T28,T32 contained
syntax match exampleTag "\vEXAMPLE" containedin=T0,T4,T8,T12,T16,T20,T24,T28,T32 contained

highlight link noteTag Notable
highlight link defTag Notable
highlight link aliasTag Notable
highlight link procTag Notable
highlight link procedureTag Notable
highlight link exTag Notable
highlight link exampleTag Notable

highlight Notable ctermbg=darkblue guibg=darkblue ctermfg=white guifg=white

""""""""""""""
" Question / Directive
""""""""""""""
syntax match question "\v[a-zA-Z0-9].+\?\?$" containedin=T4,T8,T12,T16,T20,T24,T28,T32
highlight link question Question
highlight Question ctermbg=darkgreen guibg=darkgreen ctermfg=black guifg=black

syntax match exclamation "\v[a-zA-Z0-9].+!!$" containedin=T4,T8,T12,T16,T20,T24,T28,T32
highlight link exclamation Directive
highlight Directive ctermbg=brown guibg=brown ctermfg=white guifg=white

""""""""""""""
" Media
""""""""""""""
syntax match imageLink "\vIMG:[a-zA-Z0-9_].+" containedin=T4,T8,T12,T16,T20,T24,T28,T32
highlight link imageLink Media
highlight Media ctermbg=darkgray guibg=darkgray ctermfg=white guifg=white

""""""""""""""
" Conceals
""""""""""""""
syntax match squaredText1 "\v\*\*2" conceal cchar=² containedin=T4,T8,T12,T16,T20,T24,T28,T32,flashcardCloze
syntax match cubedText1 "\v\*\*3" conceal cchar=³ containedin=T4,T8,T12,T16,T20,T24,T28,T32,flashcardCloze
syntax match squaredText2 "\v\^2" conceal cchar=² containedin=T4,T8,T12,T16,T20,T24,T28,T32,flashcardCloze
syntax match cubedText2 "\v\^3" conceal cchar=³ containedin=T4,T8,T12,T16,T20,T24,T28,T32,flashcardCloze
" syntax keyword pyKeyword alpha conceal cchar=α containedin=T4,T8,T12,T16,T20,T24,T28,T32
