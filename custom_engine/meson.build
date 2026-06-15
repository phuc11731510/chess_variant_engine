project('custom_engine', 'cpp',
  version: '1.0.0',
  default_options: [
    'cpp_std=c++20',
    'optimization=3',
    'warning_level=1',
  ]
)

cc = meson.get_compiler('cpp')

# Preprocessor definitions
add_project_arguments('-DLARGEBOARDS', language: 'cpp')
add_project_arguments('-DALLVARS', language: 'cpp')
add_project_arguments('-DPRECOMPUTED_MAGICS', language: 'cpp')
add_project_arguments('-DNNUE_EMBEDDING_OFF', language: 'cpp')
add_project_arguments('-DNDEBUG', language: 'cpp')
add_project_arguments('-DLCZERO_MCTS', language: 'cpp')

# OS-specific flags
if host_machine.system() == 'windows'
  add_project_arguments('-DNOMINMAX', language: 'cpp')
else
  add_project_arguments('-DUSE_PTHREADS', language: 'cpp')
endif

# Include directories
inc_dirs = include_directories(
  'src/lczero_chess',
  'src',
  'src/chess',
  'src/chess/nnue',
  'src/chess/syzygy'
)

# Threading dependency
thread_dep = dependency('threads')

# Chess variant source files (Fairy-Stockfish)
chess_sources = files(
  'src/chess/benchmark.cpp',
  'src/chess/bitbase.cpp',
  'src/chess/bitboard.cpp',
  'src/chess/endgame.cpp',
  'src/chess/evaluate.cpp',
  'src/chess/material.cpp',
  'src/chess/misc.cpp',
  'src/chess/movegen.cpp',
  'src/chess/movepick.cpp',
  'src/chess/pawns.cpp',
  'src/chess/position.cpp',
  'src/chess/psqt.cpp',
  'src/chess/search.cpp',
  'src/chess/thread.cpp',
  'src/chess/timeman.cpp',
  'src/chess/tt.cpp',
  'src/chess/uci.cpp',
  'src/chess/ucioption.cpp',
  'src/chess/tune.cpp',
  'src/chess/partner.cpp',
  'src/chess/parser.cpp',
  'src/chess/piece.cpp',
  'src/chess/variant.cpp',
  'src/chess/xboard.cpp',
  'src/chess/syzygy/tbprobe.cpp',
  'src/chess/nnue/evaluate_nnue.cpp',
  'src/chess/nnue/features/half_ka_v2.cpp',
  'src/chess/nnue/features/half_ka_v2_variants.cpp',
  'src/lczero_chess/chess/board.cc',
  'src/lczero_chess/chess/position.cc'
)

# Engine sources
engine_sources = files(
  'src/main.cc'
)

# Build the executable
executable('custom_engine',
  sources: [chess_sources, engine_sources],
  include_directories: inc_dirs,
  dependencies: [thread_dep],
  install: true
)
