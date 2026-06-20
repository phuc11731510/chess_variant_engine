project('custom_engine', 'cpp',
  version: '1.0.0',
  default_options: [
    'cpp_std=gnu++20',
    'optimization=3',
    'warning_level=1',
  ]
)

cc = meson.get_compiler('cpp')

# CPU Architecture specific flags
if cc.get_id() == 'msvc'
  add_project_arguments('/arch:AVX2', language: 'cpp')
else
  add_project_arguments('-mavx2', '-mfma', language: 'cpp')
endif


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

# CUDA Execution Provider (Linux/Colab GPU). Requires a GPU ONNX Runtime package.
if get_option('use_cuda')
  add_project_arguments('-DUSE_CUDA', language: 'cpp')
  message('CUDA Execution Provider ENABLED (-DUSE_CUDA)')
endif

# ONNX Runtime root: platform-specific. Windows uses the bundled CPU package;
# non-Windows (Linux/Colab) uses the GPU package pointed to by -Donnxruntime_dir=.
if host_machine.system() == 'windows'
  onnx_root = 'third_party/onnxruntime-win-x64-1.18.0'
else
  onnx_root = get_option('onnxruntime_dir')
endif

# Include directories
inc_dirs = include_directories(
  onnx_root / 'include',
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

# Training data (self-play) source files
trainingdata_sources = files(
  'src/lczero_chess/trainingdata/writer.cc',
  'src/lczero_chess/selfplay/training_extract.cc',
  'src/lczero_chess/selfplay/selfplay_game.cc',
  'src/lczero_chess/selfplay/selfplay_driver.cc'
)

# Engine sources
engine_sources = files(
  'src/main.cc'
)

# ONNX Runtime link dependency (platform-specific root resolved above).
onnx_lib_dir = meson.current_source_dir() / onnx_root / 'lib'
onnx_dep = cc.find_library('onnxruntime', dirs: onnx_lib_dir, required: true)

if host_machine.system() == 'windows'
  # Bundle the DLL next to the .exe (Windows loader needs it alongside).
  configure_file(
    input: onnx_root / 'lib/onnxruntime.dll',
    output: 'onnxruntime.dll',
    copy: true
  )
endif
# On Linux the loader finds libonnxruntime.so via the executable rpath below
# (build_rpath) or LD_LIBRARY_PATH; no copy needed.

# zlib for gzip training data (optional: falls back to raw .bin if absent)
zlib_dep = dependency('zlib', required: false)
if not zlib_dep.found()
  zlib_dep = cc.find_library('z', required: false)
endif
if zlib_dep.found()
  add_project_arguments('-DHAVE_ZLIB', language: 'cpp')
  message('zlib found: training data will be gzip-compressed (.gz)')
else
  message('zlib NOT found: training data will be uncompressed (.bin)')
endif

# Allocator options linking
deps = [thread_dep, onnx_dep]
if zlib_dep.found()
  deps += zlib_dep
endif
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

# Build the executable. On Linux, embed the ONNX Runtime lib dir as an rpath so
# the binary loads libonnxruntime.so without needing LD_LIBRARY_PATH.
exe_kwargs = {}
if host_machine.system() != 'windows'
  exe_kwargs += {'build_rpath': onnx_lib_dir}
endif
executable('custom_engine',
  sources: [chess_sources, search_sources, neural_sources, trainingdata_sources, engine_sources],
  include_directories: inc_dirs,
  dependencies: deps,
  install: true,
  kwargs: exe_kwargs
)
