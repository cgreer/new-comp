import sys
from pathlib import Path

import vim # noqa

parsing_lib_path = "/Users/chrisgreer/Dropbox/projects/priming"
sys.path.insert(0, parsing_lib_path)
import run # noqa Probably not the best way to import this module.

# print(sys.executable)
# print(sys.path)

HOME_PATH = Path.home()
NOTES_SYNTAX_PATH = HOME_PATH / Path(".vim/after/syntax/wiki.vim")


def print_country():
    print("Country")


def mock_get_local_concepts(notes_path):
    return [
        "Concept",
        "Concept Name",
        "Concept Name 2",
    ]


# XXX Swap this out
# get_local_concepts = mock_get_local_concepts
get_local_concepts = run.get_highlightables


def regenerate_local_syntax(notes_path):
    '''
    :notes_path - full path to file with notes.

    Regex explanations:
    - \< and \> will ensure it matches beginning and end of word.
    - \c will ensure that it is case insensitive.

    # noqa
    '''
    tokens = get_local_concepts(notes_path)
    single_tokens = [tok for tok in tokens if " " not in tok]
    compound_tokens = [tok for tok in tokens if " " in tok]
    s = ""
    for token in single_tokens:
        # s += f"\nsyn keyword localConceptTag {token} containedin=T0,T4,T8,T12,T16,T20,T24,T28,T32 contained"
        s += f'\nsyn match localConceptTag "\<{token}\>\c" containedin=T0,T4,T8,T12,T16,T20,T24,T28,T32 contained'
    for token in compound_tokens:
        s += f'\nsyn match localConceptTag "\<{token}\>\c" containedin=T0,T4,T8,T12,T16,T20,T24,T28,T32 contained'
    s += "\nhighlight link localConceptTag LocalConcept"
    # s += "\nhighlight LocalConcept ctermfg=magenta guifg=magenta ctermbg=black guibg=black"
    s += "\nhighlight LocalConcept ctermfg=magenta guifg=magenta"
    with open(NOTES_SYNTAX_PATH, 'w') as f:
        f.write(s)


def update_coverage_file(notes_path, output_path):
    run.update_coverage_file(notes_path, output_path)
