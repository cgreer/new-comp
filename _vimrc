set nocompatible

" =====================
" Settings / Config
" =====================
let mapleader=","

let fzf_default_options=" --cycle --bind 'ctrl-h:jump-accept'"

let g:python3_host_prog = '~/python-environments/jedi-env-311/bin/python3'
let g:jedi#force_py_version = 3
let g:jedi#goto_stubs_command = ""

let g:ale_linters = {
      \   'python': ['flake8'],
      \   'javascript': ['eslint'],
      \   'cpp': ['clang', 'g++'],
      \}
let g:ale_cpp_clang_options = '-std=c++17 -march=native -Wall -I /Users/chrisgreer/.pyenv/versions/3.9.0/lib/python3.9/site-packages/pybind11/include -I/Users/chrisgreer/.pyenv/versions/3.9.0/include/python3.9'
let g:ale_cpp_gcc_options = '-std=c++17 -march=native -Wall -I /Users/chrisgreer/.pyenv/versions/3.9.0/lib/python3.9/site-packages/pybind11/include -I/Users/chrisgreer/.pyenv/versions/3.9.0/include/python3.9'
let g:ale_virtualtext_cursor = 'disabled'
let g:ale_python_flake8_options = '--ignore=E226,E241,E261,E402,E501,E251,E221,E201'


" =====================
" Plugins
" =====================

call plug#begin()

" List your plugins here
Plug 'junegunn/fzf', { 'do': { -> fzf#install() } }
Plug 'junegunn/fzf.vim'
Plug 'morhetz/gruvbox'
Plug 'scrooloose/nerdcommenter'
Plug 'yegappan/mru'
Plug 'dense-analysis/ale'
Plug '~/Dropbox/projects/vimpyplug'
Plug 'davidhalter/jedi-vim'

call plug#end()


" =====================
" Functions
" =====================

function! WinMove(key)
    let t:curwin = winnr()
    exec "wincmd ".a:key
    if (t:curwin == winnr())
        if (match(a:key,'[jk]'))
            wincmd v
        else
            wincmd s
        endif
        exec "wincmd ".a:key
    endif
endfunction

function! StatusLineCwd()
    return fnamemodify(getcwd(), ":~:.")
endfunction


function! ToggleLineLevelFolding()
    " foldlevel will find the foldlevel of the line
    " line('.') get the current line under the cursor
    let currentFoldLevel = &foldlevel
    let lineFoldLevel = foldlevel(line('.'))
    if currentFoldLevel == lineFoldLevel
        silent exe "set foldlevel=99"
    else
        silent exe "set foldlevel=" . lineFoldLevel
    end
endfunction

function! VisualSelectionRangeToTempFile()
    let [line_start, column_start] = getpos("'<")[1:2]
    let [line_end, column_end] = getpos("'>")[1:2]
    execute line_start . "," . line_end . "w! ~/.visual_text"
endfunction

" range allows makes it so the function is only called once for entire visual
" selection.
function! FilterVisual(operation) range
    " Take visual text, filter through x, replace with results
    call VisualSelectionRangeToTempFile()
    silent execute "'<,'>!python3 ~/.vim/pythonfilter.py " . a:operation
endfunction

function! PyCall(fxnName, kwargs)
    " :fxnName: 'module.function'
    "
    " Uses a literal string (r'something') in fxn call to correctly
    " escape newlines and control characters
    let fxnCall = a:fxnName . "(r'''" . json_encode(a:kwargs) . "''')"
    return py3eval(fxnCall)
endfunction

function! ToggleTable()
    call PyCall("sample.toggle_table", {})
endfunction

function! PyLocalTags()
    let lines = py3eval('sample.local_tags()')
    return lines
endfunction

function! PyAboveNotes()
    let lines = py3eval('sample.above_outline()')
    return lines
endfunction

function! PyLocalTagsD2()
    let lines = py3eval('sample.local_tags_d2()')
    return lines
endfunction

function! HandleLineJump(e)
    " echom a:e
    let linenum = matchstr(a:e, "^\[0-9]\\+") " parse out linenum
    call cursor(linenum + 1, 1) " line, col

    " Center top/cursor on screen
    exe "normal! z\<CR>"
    " exe "normal! z."
endfunction

function! HandleRecursiveTagSelection(e)
    " Move to line X
    let linenum = matchstr(a:e, "^\[0-9]\\+") " parse out linenum
    call cursor(linenum + 1, 1) " line, col

    " Call local tags from that line
    call fzf#run({
        \'source': PyLocalTags(),
        \'sink': function('HandleLineJump'),
        \'down': '50%',
        \'options': '--reverse --no-sort'})

    " Center top/cursor on screen
    " exe "normal! z\<CR>"
    " exe "normal! z."
endfunction

function! InsertFZFSelectionCol1(e)
    " First column (space seperated) is text to insert
    echom a:e
    let text = split(a:e)
    exe "normal! i" . text[0]
endfunction

function! InsertFZFSelection(e)
    " Insert text that was selected via FZF
    echom a:e
    exe "normal! a" . a:e
endfunction

function! InsertSymbol()
    call fzf#run({
        \'source': 'cat ~/symbols.txt',
        \'sink': function('InsertFZFSelectionCol1'),
        \'down': '50%',
        \'options': '--reverse --no-sort'})
endfunction

function! InsertUnicodeSymbol()
    call fzf#run({
        \'source': 'cat ~/unicode_chars_vim.txt',
        \'sink': function('InsertFZFSelectionCol1'),
        \'down': '50%',
        \'options': '--reverse --no-sort'})
endfunction

" MRU

function! MRUFiles()
    call fzf#run({
        \'source': 'cat ~/.vim_mru_files \| grep -v Most',
        \'sink': 'e',
        \'options': '--no-sort'
        \})
endfunction

function! MRUDirectories()
    call fzf#run({
        \'source': '~/Dropbox/projects/vim_stuff/mru_dir_list.sh',
        \'sink': 'cd',
        \'options': '--no-sort'
        \})
endfunction

function! MRUClean()
    execute "!python3 ~/Dropbox/projects/vim_stuff/clean_mru.py"
endfunction

function! MarkAndJumpLeft()
    mark A
    call WinMove('h')
    exe "normal! 'A"

    " Center in buffer
    exe "normal! z."
endfunction

function! MarkAndJumpRight()
    mark A
    call WinMove('l')
    exe "normal! 'A"

    " Center in buffer
    exe "normal! z."
endfunction

function! SetVisualMarks(start, end)
    " Move cursor to line, col and set visual start mark
    call cursor(a:start, 1)
    normal! m<

    " Move cursor to line, col and set visual end mark
    call cursor(a:end, 1)
    normal! m>
endfunction

function! SelectNotesSection()
    let nrange = PyCall("sample.selected_section_range", {})
    call SetVisualMarks(nrange[0] + 1, nrange[1] + 1)
    normal! gv
endfunction


function! InfiniPopulate()
    let lst = py3eval('sample.menu_choices_lru()')
    return lst
endfunction

function! StartInfiniMenu() range
    call fzf#run({
    \'source': InfiniPopulate(),
    \'sink': function('InfiniHandleChoice'),
    \'down': '50%',
    \'options': '--reverse'
    \})

endfunction

function! InfiniHandleChoice(e)
    " Seems to be a newline or something
    let fxn = a:e->trim()

    " Log that we're selecting this choice
    call PyLogMenuChoice(fxn)

    " Execute the selected chosen operation
    execute "call " . fxn
endfunction

" ==============================
" Mappings
" ==============================

" jk as escape
inoremap jk <Esc>

" quit with qq
noremap qq :q<CR>

" toggle paste for pasting from outside
" set pastetoggle=<leader>tp

" begin/end of line to H/L
noremap H ^
noremap L $

" Move to windows with ctrl-<movement>
" map <c-j> <c-w>j
map <c-j> :call WinMove('j')<CR>
map <c-k> :call WinMove('k')<CR>
map <c-h> :call WinMove('h')<CR>
map <c-l> :call WinMove('l')<CR>

" Make buffer to the left/right
nmap <leader>bh :call MarkAndJumpLeft()<CR>
nmap <leader>bl :call MarkAndJumpRight()<CR>

nnoremap ,z :call ToggleLineLevelFolding()<CR>

" Text table
nnoremap <c-t> :call ToggleTable()<CR>

" Toggle task / question
nnoremap <c-n> :call PyCall("sample.toggle_task", {})<CR>
nnoremap <c-p> :call PyCall("sample.toggle_note", {})<CR>

vnoremap ,P :call FilterVisual("auto_expand_collapse")<CR>:noh<CR>
noremap ,P ?[({[]<CR>v%:call FilterVisual("auto_expand_collapse")<CR>:noh<CR>

" Infinimenu
" - Normal mode
" - Insert mode (<C-o> will run subsequent as if in normal)
" - Visual mode
nnoremap <C-s> :call StartInfiniMenu()<CR>
inoremap <C-s> <C-o>:call StartInfiniMenu()<CR>
xnoremap <C-s> :call StartInfiniMenu()<CR>

" Jumping to errors
nnoremap ,e :ALENext<CR>

nmap ,s :call MRUFiles()<CR>

" Recursively select top level tags then local
nmap T :call fzf#run({
            \'source': PyTopTags(),
            \'sink': function('HandleRecursiveTagSelection'),
            \'down': '50%',
            \'options': '--reverse --no-sort' . fzf_default_options})<CR>

" All tags (class, def) in file
nmap ,t :call fzf#run({
            \'source': PyTagLines(),
            \'sink': function('HandleLineJump'),
            \'options': '--reverse --no-sort --preview="tail -n +{1} ' . expand("%:p") . ' \| head -n 45"' . fzf_default_options})<CR>

" Local tags (and UNDER for notes)
nmap ,c :call fzf#run({
            \'source': PyLocalTags(),
            \'sink': function('HandleLineJump'),
            \'options': "--reverse --no-sort" . fzf_default_options})<CR>

" ABOVE for notes)
nmap ,C :call fzf#run({
            \'source': PyAboveNotes(),
            \'sink': function('HandleLineJump'),
            \'options': "--reverse --no-sort" . fzf_default_options})<CR>

" Local tasks
nmap ,5 :call fzf#run({
            \'source': LocalTasksView(),
            \'sink': function('HandleLineJump'),
            \'down': '50%',
            \'options': '--reverse --no-sort' . fzf_default_options})<CR>

nmap ,V :call SelectNotesSection()<CR>

" Local section's subsections
nmap ,1 :call fzf#run({
            \'source': PyLocalTagsD2(),
            \'sink': function('HandleLineJump'),
            \'down': '50%',
            \'options': '--reverse --no-sort' . fzf_default_options})<CR>

imap [" [""]<left><left>

" ==============================
" Autocommands / File settings
" ==============================
"
syntax on
set tabstop=4
set shiftwidth=4
set expandtab
set smartcase
set textwidth=120 " Automatically wrap new line after hitting 80 characters
set autoindent " When forming a new line, indent it to previous line's indent level
filetype plugin indent on     " enable loading indent file for filetype

" === Folding ===
set foldmethod=indent       " allow us to fold on indents
set foldlevel=99            " don't fold by default

" ==== Searching and Patterns ====
set ignorecase              " Default to using case insensitive searches,
set smartcase               " unless uppercase letters are used in the regex.
set smarttab                " Handle tabs more intelligently
set hlsearch                " Highlight searches by default.
set incsearch               " Incrementally search while typing a /regex

" ====== OTHER =======
set confirm " Instead of typing q! it will just ask you Y/N/C?
set backspace=indent,eol,start
set nowrap
set conceallevel=2

set laststatus=2
set statusline=%F:%l%m\ (cwd:%{StatusLineCwd()})

colorscheme gruvbox

" Get rid of trailing whitespace
autocmd BufWritePre * :%s/\s\+$//e

autocmd FileType cpp,html,xhtml,xml,css,typescriptreact,typescript,js,javascript setlocal expandtab shiftwidth=2 tabstop=2 softtabstop=2 smartindent
au FileType python setlocal expandtab shiftwidth=4 tabstop=8 softtabstop=4 smartindent cinwords=if,elif,else,for,while,try,except,finally,def,>
au BufRead *.py set efm=%C\ %.%#,%A\ \ File\ \"%f\"\\,\ line\ %l%.%#,%Z%[%^\ ]%\\@=%m
autocmd BufRead,BufNewFile *.wiki set filetype=notes foldmethod=indent

