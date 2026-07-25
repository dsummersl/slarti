" lua << EOF
" require('lazy-loader')()
" EOF

let g:gutentags_ctags_exclude += ['*/.venv/*']
let g:projectionist_heuristics = {
      \ 'pyproject.toml': {
      \   'slarti/*.py': {
      \     'type': 'function',
      \     'alternate': [
      \       'tests/{dirname}test_{basename}.py',
      \       'tests/{dirname}/test_{basename}.py',
      \     ]
      \   },
      \   'tests/**/test_*.py': {
      \     'type': 'test',
      \     'alternate': [
      \       'slarti/{dirname}{basename}.py',
      \       'slarti/{dirname}/{basename}.py',
      \     ]
      \   },
      \ },
      \ }
