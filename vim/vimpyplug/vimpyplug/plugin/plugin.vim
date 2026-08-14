" http://candidtim.github.io/vim/2017/08/11/write-vim-plugin-in-python.html

if !has("python3")
    echo "vim has to be compiled with +python3 to run this"
    finish
endif

if exists('g:sample_plugin_loaded')
    finish
endif

" ######################################
" Setup plugin to interface with Python
" ######################################

" Get the root directory of this plugin
let s:plugin_root_dir = fnamemodify(resolve(expand('<sfile>:p')), ':h')

python3 << EOF
import sys
from os.path import normpath, join
import vim

# Add the python directory into the python path
# - The directory is ../python relative to this plugin file.
plugin_root_dir = vim.eval('s:plugin_root_dir')
python_root_dir = normpath(join(plugin_root_dir, '..', 'python'))
sys.path.insert(0, python_root_dir)

# print(sys.path)

import notes # Order matters, modifies sys path!!!
import sample
EOF

" ######################################
" Functions that interface with Python
" ######################################

function! PyRegenNotesSyntax(notesPath)
    let fArgs = '"' . a:notesPath . '"'
    let retValue = py3eval('notes.regenerate_local_syntax(' . fArgs . ')')
endfunction

function! PyCoverage()
    let cpath = expand("%:p")
    let outputPath = "/Users/chrisgreer/coverage.wiki"

    " Update the coverage file
    let fArgs = '"' . cpath . '"'
    let fArgs = fArgs . ', "' . outputPath . '"'
    let retValue = py3eval('notes.update_coverage_file(' . fArgs . ')')

    " Edit it
    execute "edit " . outputPath
endfunction

function! PrintCountry()
    python3 sample.print_country()
endfunction
" So we don't have to type :call X(), just :X
command! -nargs=0 PrintCountry call PrintCountry()

function! PyTagLines()
    let lines = py3eval('sample.taglines()')
    return lines
endfunction

function! PyClassLines()
    let lines = py3eval('sample.classlines()')
    return lines
endfunction

function! PyTopTags()
    let lines = py3eval('sample.top_tags()')
    return lines
endfunction

function! PyLogMenuChoice(menuChoice)
    let fArgs = '"' . a:menuChoice . '"'
    let blah = py3eval('sample.log_menu_choice(' . fArgs . ')')
endfunction

function! PyMenuChoicesLRU()
    let lines = py3eval('sample.menu_choices_lru()')
    return lines
endfunction

function! PyLevelLines()
    let lines = py3eval('sample.level_topics()')
    return lines
endfunction

function! PyDebug()
    let result = py3eval('sample.level_topics()')
endfunction

function! PyMakeTest()
    " Get replacement text
    let teststring = py3eval('sample.make_test()')

    " Swap out word with replacement text
    execute "normal! ciw" . teststring
endfunction

" ######################################
" Finish loading
" ######################################
let g:sample_plugin_loaded = 1 " Should be last line
