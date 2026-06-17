project('custom_engine', 'cpp',
  version: '1.0.0',
  default_options: [
    'cpp_std=gnu++20',
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
  'third_party/onnxruntime-win-x64-1.18.0/include',
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
  'src/lczero_chess/chess/position.cc',
  'src/lczero_chess/chess/encoder.cc',
  'src/lczero_chess/utils/string.cc'
)

# Classic search source files (Lc0-master)
search_sources = files(
  'src/search/classic/node.cc',
  'src/search/classic/search.cc',
  'src/search/classic/params.cc',
  'src/search/classic/stoppers/timemgr.cc'
)

# Phase 4 neural backend source files
neural_sources = files(
  'src/lczero_chess/neural/onnx_backend.cc',
  'src/lczero_chess/neural/zero_heap_cache.cc'
)

# Engine sources
engine_sources = files(
  'src/main.cc'
)

# ONNX Runtime link dependency
onnx_lib_dir = meson.current_source_dir() / 'third_party/onnxruntime-win-x64-1.18.0/lib'
onnx_dep = cc.find_library('onnxruntime', dirs: onnx_lib_dir, required: true)

if host_machine.system() == 'windows'
  configure_file(
    input: 'third_party/onnxruntime-win-x64-1.18.0/lib/onnxruntime.dll',
    output: 'onnxruntime.dll',
    copy: true
  )
endif

# Allocator options linking
deps = [thread_dep, onnx_dep]
malloc_opt = get_option('malloc')
if malloc_opt == 'mimalloc' and cc.get_id() == 'msvc'
  if get_option('b_vscrt') != 'md' and get_option('b_vscrt') != 'mdd'
    error('You need -Db_vscrt=md (or mdd) to use mimalloc')
  endif
  add_project_link_arguments('/INCLUDE:mi_version', language : 'cpp')
  deps += cc.find_library('mimalloc-override', dirs: get_option('mimalloc_libdir'), required: true)
elif malloc_opt != ''
  deps += cc.find_library(malloc_opt, required: true)
endif

# Build the executable
executable('custom_engine',
  sources: [chess_sources, search_sources, neural_sources, engine_sources],
  include_directories: inc_dirs,
  dependencies: deps,
  install: true
)
