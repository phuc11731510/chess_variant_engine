#include "neural/onnx_backend.h"
#include "chess/encoder.h"
#include "neural/shared_params.h"
#include "utils/exception.h"
#include <sstream>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <algorithm>
#include <limits>
#if defined(__x86_64__) || defined(__i386__) || defined(_M_X64) || defined(_M_IX86)
#define FZ_X86_SIMD 1
#include <immintrin.h>
#else
#define FZ_X86_SIMD 0   // ARM/Android (or other): use portable scalar fallbacks below
#endif

#ifdef USE_DML
// DirectML EP factory (only in the DirectML ONNX Runtime package).
#include "dml_provider_factory.h"
#endif

namespace lczero {

// ---- Output post-processing -------------------------------------------------
//
// Softmax over the legal moves' logits. It used to exponentiate with the
// approximation (1 + x/1024)^1024, whose error grows with the distance from the
// best move: -2% at x = -5, -5% at x = -10, -18% at x = -20. The priors of the
// weaker moves were therefore lower than the ones the network was trained to
// output (PyTorch uses the exact softmax). The gen-0/gen-1 nets are too flat for
// it to matter (their legal logits span ~1), a sharp policy is not. The version
// below is the Cephes expf (range reduction + degree-5 polynomial, a few ulp),
// at about the same cost. The padding lanes of the last vector are masked to 0;
// before, they were -100 and summed in, which only stayed harmless while the
// best logit was well above -100.
#if FZ_X86_SIMD
#if defined(__GNUC__) || defined(__clang__)
__attribute__((target("avx2,fma")))
#endif
static inline __m256 Exp256(__m256 x) {
    // Operand order matters: max/min return their SECOND operand when one is
    // NaN, so a NaN logit stays NaN (and the caller reports it) instead of
    // turning into a tiny probability. Below -87.3 exp() is denormal: those
    // lanes give 2^-126, i.e. nothing next to the best move's 1.
    x = _mm256_max_ps(_mm256_set1_ps(-87.3f), x);
    x = _mm256_min_ps(_mm256_set1_ps(88.3f), x);
    const __m256 k = _mm256_round_ps(_mm256_mul_ps(x, _mm256_set1_ps(1.44269504088896341f)),
                                     _MM_FROUND_TO_NEAREST_INT | _MM_FROUND_NO_EXC);
    __m256 r = _mm256_fnmadd_ps(k, _mm256_set1_ps(0.693359375f), x);   // x - k*ln2, in two
    r = _mm256_fnmadd_ps(k, _mm256_set1_ps(-2.12194440e-4f), r);        // parts (Cody-Waite)
    __m256 p = _mm256_set1_ps(1.9875691500e-4f);
    p = _mm256_fmadd_ps(p, r, _mm256_set1_ps(1.3981999507e-3f));
    p = _mm256_fmadd_ps(p, r, _mm256_set1_ps(8.3334519073e-3f));
    p = _mm256_fmadd_ps(p, r, _mm256_set1_ps(4.1665795894e-2f));
    p = _mm256_fmadd_ps(p, r, _mm256_set1_ps(1.6666665459e-1f));
    p = _mm256_fmadd_ps(p, r, _mm256_set1_ps(5.0000001201e-1f));
    p = _mm256_fmadd_ps(p, _mm256_mul_ps(r, r), r);
    p = _mm256_add_ps(p, _mm256_set1_ps(1.0f));
    const __m256i e = _mm256_slli_epi32(
        _mm256_add_epi32(_mm256_cvtps_epi32(k), _mm256_set1_epi32(127)), 23);  // 2^k
    return _mm256_mul_ps(p, _mm256_castsi256_ps(e));
}

#if defined(__GNUC__) || defined(__clang__)
__attribute__((target("avx2,fma")))
#endif
static float SoftmaxLegalAvx2(float* logits, size_t n, float inv_temp, float max_logit,
                              float* out_p, size_t max_out) {
    const __m256 vmax = _mm256_set1_ps(max_logit);
    const __m256 vinv = _mm256_set1_ps(inv_temp);
    const size_t full = n & ~size_t{7};
    __m256 vsum = _mm256_setzero_ps();
    for (size_t i = 0; i < full; i += 8) {
        const __m256 e = Exp256(_mm256_mul_ps(_mm256_sub_ps(_mm256_load_ps(logits + i), vmax), vinv));
        _mm256_store_ps(logits + i, e);
        vsum = _mm256_add_ps(vsum, e);
    }
    if (full < n) {  // last partial vector: zero the lanes past n
        const int rem = static_cast<int>(n - full);
        const __m256 keep = _mm256_castsi256_ps(_mm256_cmpgt_epi32(
            _mm256_set1_epi32(rem), _mm256_setr_epi32(0, 1, 2, 3, 4, 5, 6, 7)));
        const __m256 x = _mm256_mul_ps(_mm256_sub_ps(_mm256_load_ps(logits + full), vmax), vinv);
        const __m256 e = _mm256_and_ps(Exp256(x), keep);
        _mm256_store_ps(logits + full, e);
        vsum = _mm256_add_ps(vsum, e);
    }
    alignas(32) float lanes[8];
    _mm256_store_ps(lanes, vsum);
    const float sum = ((lanes[0] + lanes[1]) + (lanes[2] + lanes[3])) +
                      ((lanes[4] + lanes[5]) + (lanes[6] + lanes[7]));
    const float inv_sum = 1.0f / sum;
    const size_t out_n = std::min(n, max_out);
    for (size_t i = 0; i < out_n; ++i) out_p[i] = logits[i] * inv_sum;
    return sum;
}
#endif  // FZ_X86_SIMD

float SoftmaxLegal(float* logits, size_t n, float temp, float max_logit, float* out_p,
                   size_t max_out) {
    const float inv_temp = 1.0f / std::max(1e-3f, temp);
#if FZ_X86_SIMD
    return SoftmaxLegalAvx2(logits, n, inv_temp, max_logit, out_p, max_out);
#else  // ARM/Android: output processing is ~0% of the run time, scalar is fine.
    float sum = 0.0f;
    for (size_t i = 0; i < n; ++i) {
        logits[i] = std::exp((logits[i] - max_logit) * inv_temp);
        sum += logits[i];
    }
    const float inv_sum = 1.0f / sum;
    const size_t out_n = std::min(n, max_out);
    for (size_t i = 0; i < out_n; ++i) out_p[i] = logits[i] * inv_sum;
    return sum;
#endif
}

bool IsWdlDistribution(const float* v) {
    // Written so that NaN fails every test.
    for (int i = 0; i < 3; ++i)
        if (!(v[i] >= -1e-4f && v[i] <= 1.0f + 1e-4f)) return false;
    return std::fabs(v[0] + v[1] + v[2] - 1.0f) <= 1e-3f;
}

size_t OnnxBufferSlots(bool fixed_batch, size_t fixed_batch_size) {
    if (!fixed_batch || fixed_batch_size == 0) return MaxBatchSize;
    return (MaxBatchSize + fixed_batch_size - 1) / fixed_batch_size * fixed_batch_size;
}

// Helper function to split strings
static std::vector<std::string> split_options(const std::string& s, char delimiter) {
    std::vector<std::string> tokens;
    std::string token;
    std::istringstream tokenStream(s);
    while (std::getline(tokenStream, token, delimiter)) {
        tokens.push_back(token);
    }
    return tokens;
}

// ==========================================
// OnnxComputation Implementation
// ==========================================

OnnxComputation::OnnxComputation(Ort::Session* session, Ort::MemoryInfo& memory_info, float softmax_temp, bool fixed_batch, size_t fixed_batch_size)
    : session_(session), memory_info_(memory_info),
      // Capacity is how many positions the SEARCH may pile into one
      // computation, which is NOT the same as the ORT session's fixed batch:
      // ComputeBlocking deliberately slices `enqueued_` into several Run()s of
      // fixed_batch_size_ each. Sizing this to fixed_batch_size_ made AddInput
      // throw "Maximum batch size exceeded" as soon as the search gathered more
      // than one session-batch worth of leaves.
      capacity_(MaxBatchSize),
      // With a fixed batch f the last Run() covers slots up to the next multiple
      // of f. Sizing the buffers to capacity_ alone let that Run() write past
      // their end when f does not divide MaxBatchSize and more than
      // floor(64/f)*f inputs were queued (e.g. --fixed-batch 24 or 48 with
      // --batch-aggregate, whose shared computation fills up to 64): the padding
      // memset, ORT's input read and its policy/value writes all overran the
      // heap blocks.
      slots_(OnnxBufferSlots(fixed_batch, fixed_batch_size)),
      input_buffer_(new float[slots_ * InputBufferUnitSize]),
      policy_output_buffer_(new float[slots_ * PolicyOutputSize]),
      value_output_buffer_(new float[slots_ * ValueOutputSize]),
      results_(capacity_),
      position_moves_(capacity_),
      softmax_temp_(softmax_temp), fixed_batch_(fixed_batch),
      fixed_batch_size_(fixed_batch_size) {
    // NO buffer memset here, deliberately.
    //
    // A fresh OnnxComputation is built for EVERY Run(), so anything this ctor
    // touches is paid on every single NN call. These buffers used to be arrays
    // of MaxBatchSize and to be memset in full, which cost the same whether the
    // real batch was 1 or 256. Measured on a Colab T4: ~20.8 ms of fixed cost
    // per Run at MaxBatchSize 256, i.e. five sixths of the whole inference at
    // batch 16. Removing the memset cut that to ~3.6 ms; sizing the buffers to
    // `capacity_` (above) removes what was left.
    //
    // (An older CPU profiling pass concluded this memset was negligible. It was
    // -- on CPU, where one eval took ~27 ms. On GPU an eval takes ~5 ms and the
    // very same memset dominates. The conclusion did not survive the hardware.)
    //
    // It is also redundant:
    //   * input_buffer_  -- UnpackInputPlanes (encoder.cc) memsets exactly the
    //                       22600 floats of each slot before filling it, and
    //                       ComputeBlocking memsets exactly the fixed-batch
    //                       padding tail. Every byte ORT reads is written first.
    //   * policy/value   -- written wholesale by ORT's Run().
}

BackendComputation::AddInputResult OnnxComputation::AddInput(
    const EvalPosition& pos,
    EvalResultPtr result) {
    
    // Reserve this input's slot FIRST, atomically: several search task threads
    // may be in here at once, and each must write only its own slot. (Reading
    // enqueued_ here and incrementing it at the end let two threads fill the
    // same slot and left another one unwritten.)
    const size_t slot = enqueued_.fetch_add(1, std::memory_order_acq_rel);
    if (slot >= capacity_) {
        enqueued_.fetch_sub(1, std::memory_order_acq_rel);
        throw Exception("ONNX Backend: Maximum batch size exceeded!");
    }

    // Save pointers to output destination
    results_[slot] = result;

    // Save legal moves list
    size_t num_moves = std::min(pos.legal_moves.size(), static_cast<size_t>(384));
    position_moves_[slot].resize(num_moves);
    for (size_t i = 0; i < num_moves; ++i) {
        position_moves_[slot][i] = pos.legal_moves[i];
    }

    // Encode board features using position history
    alignas(64) InputPlanes planes;
    int transform = 0;
    EncodePositionForNN(*pos.history, kMoveHistory, FillEmptyHistory::FEN_ONLY, &planes, &transform);

    // Unpack bits into flat float buffer
    float* current_input_ptr = input_buffer_.get() + slot * InputBufferUnitSize;
    UnpackInputPlanes(planes, current_input_ptr, BoardWidth, BoardHeight);

    return ENQUEUED_FOR_EVAL;
}

namespace {
// See OnnxEvalCounters in the header. Relaxed ordering: these are statistics,
// never used to synchronise anything.
std::atomic<uint64_t> g_eval_real{0};
std::atomic<uint64_t> g_eval_padded{0};
std::atomic<uint64_t> g_eval_runs{0};
}  // namespace

OnnxEvalCounters OnnxGetEvalCounters() {
    return {g_eval_real.load(std::memory_order_relaxed),
            g_eval_padded.load(std::memory_order_relaxed),
            g_eval_runs.load(std::memory_order_relaxed)};
}

void OnnxResetEvalCounters() {
    g_eval_real.store(0, std::memory_order_relaxed);
    g_eval_padded.store(0, std::memory_order_relaxed);
    g_eval_runs.store(0, std::memory_order_relaxed);
}

void OnnxComputation::ComputeBlocking() {
    // Every AddInput has returned by now (the search joins its task threads
    // first), so this count is final and every slot below it is filled.
    const size_t enqueued = enqueued_.load(std::memory_order_acquire);
    if (enqueued == 0) return;
    if (!session_) {
        throw Exception("ONNX Backend: ORT session is not initialized!");
    }

    size_t offset = 0;
    while (offset < enqueued) {
        size_t current_batch = enqueued - offset;
        if (fixed_batch_ && current_batch > fixed_batch_size_) {
            current_batch = fixed_batch_size_;
        }
        
        size_t run_batch = fixed_batch_ ? fixed_batch_size_ : current_batch;
        
        if (fixed_batch_ && run_batch > current_batch) {
            size_t pad_count = run_batch - current_batch;
            std::memset(input_buffer_.get() + (offset + current_batch) * InputBufferUnitSize, 0, pad_count * InputBufferUnitSize * sizeof(float));
        }
        
        // 1. Direct Memory Mapping: map C++ float arrays directly into Ort::Value (zero-copy)
        std::array<int64_t, 4> input_shape = { static_cast<int64_t>(run_batch), static_cast<int64_t>(InputPlanesCount), static_cast<int64_t>(BoardHeight), static_cast<int64_t>(BoardWidth) };
        Ort::Value input_tensor = Ort::Value::CreateTensor<float>(
            memory_info_,
            input_buffer_.get() + offset * InputBufferUnitSize,
            run_batch * InputBufferUnitSize,
            input_shape.data(),
            input_shape.size()
        );
        
        std::array<int64_t, 2> policy_shape = { static_cast<int64_t>(run_batch), static_cast<int64_t>(PolicyOutputSize) };
        Ort::Value policy_tensor = Ort::Value::CreateTensor<float>(
            memory_info_,
            policy_output_buffer_.get() + offset * PolicyOutputSize,
            run_batch * PolicyOutputSize,
            policy_shape.data(),
            policy_shape.size()
        );
        
        std::array<int64_t, 2> value_shape = { static_cast<int64_t>(run_batch), static_cast<int64_t>(ValueOutputSize) };
        Ort::Value value_tensor = Ort::Value::CreateTensor<float>(
            memory_info_,
            value_output_buffer_.get() + offset * ValueOutputSize,
            run_batch * ValueOutputSize,
            value_shape.data(),
            value_shape.size()
        );
        
        // 2. Setup inputs and outputs pointers
        const char* input_names[] = { "input" };
        char* output_names[] = { "policy", "value" };
        
        Ort::Value inputs[] = { std::move(input_tensor) };
        Ort::Value outputs[] = { std::move(policy_tensor), std::move(value_tensor) };
        
        // 3. Execute inference synchronously on CPU/GPU
        session_->Run(
            Ort::RunOptions{nullptr},
            input_names,
            inputs,
            1,
            output_names,
            outputs,
            2
        );
        
        // Instrumentation (see OnnxEvalCounters): current_batch is what the
        // search asked for, run_batch is what the device actually computed.
        g_eval_real.fetch_add(current_batch, std::memory_order_relaxed);
        g_eval_padded.fetch_add(run_batch, std::memory_order_relaxed);
        g_eval_runs.fetch_add(1, std::memory_order_relaxed);

        offset += current_batch;
    }
    
    // 4. Fill results and execute Softmax for legal moves
    for (size_t b = 0; b < enqueued; ++b) {
        const float* raw_policy = policy_output_buffer_.get() + b * PolicyOutputSize;
        const float* raw_value = value_output_buffer_.get() + b * ValueOutputSize;
        EvalResultPtr res = results_[b];

        // 4.1. WDL value. The graph must end with a softmax (python/train.py's
        // ExportNet does); raw logits here would give a meaningless q = W - L,
        // and a NaN would spread through the tree, both without any error.
        if (!IsWdlDistribution(raw_value)) {
            std::ostringstream msg;
            msg << "ONNX Backend: the network's value output is not a W/D/L probability "
                   "distribution (got " << raw_value[0] << ", " << raw_value[1] << ", "
                << raw_value[2] << "). The model must end with a softmax over its 3 value "
                   "outputs, as python/train.py exports it; NaN means broken weights.";
            std::cerr << msg.str() << std::endl;
            throw Exception(msg.str());
        }
        if (res.q) *res.q = raw_value[0] - raw_value[2];
        if (res.d) *res.d = raw_value[1];
        if (res.m) *res.m = 50.0f;      // no moves-left head (has_mlh = false)

        // 4.2. Policy: softmax over the legal moves' logits.
        const size_t num_legal = std::min(position_moves_[b].size(), static_cast<size_t>(384));
        if (num_legal > 0 && !res.p.empty()) {
            alignas(64) float legal_logits[384];
            float max_logit = -std::numeric_limits<float>::infinity();
            for (size_t i = 0; i < num_legal; ++i) {
                const uint16_t index = MoveToNNIndex(position_moves_[b][i], 0);
                // Every legal move has an index (--test-policy); an unmapped one
                // gets probability 0 rather than an arbitrary logit.
                const float l = index < PolicyOutputSize
                                    ? raw_policy[index]
                                    : -std::numeric_limits<float>::infinity();
                legal_logits[i] = l;
                max_logit = std::max(max_logit, l);
            }
            const float sum = SoftmaxLegal(legal_logits, num_legal, softmax_temp_, max_logit,
                                           res.p.data(), res.p.size());
            if (!std::isfinite(sum) || !(sum >= 1.0f)) {  // >= 1: the best move gives exp(0)
                std::ostringstream msg;
                msg << "ONNX Backend: the network's policy logits are not finite (NaN/inf) for a "
                       "position with " << num_legal << " legal moves; the weights are broken.";
                std::cerr << msg.str() << std::endl;
                throw Exception(msg.str());
            }
        }
    }
    
    // Reset batch counter
    enqueued_.store(0, std::memory_order_release);
}

// ==========================================
// OnnxBackend Implementation
// ==========================================

OnnxBackend::OnnxBackend()
    : env_(ORT_LOGGING_LEVEL_WARNING, "ONNX_Backend"),
      memory_info_(Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault)) {
}

BackendAttributes OnnxBackend::GetAttributes() const {
    int rec_batch = fixed_batch_ ? static_cast<int>(fixed_batch_size_) : 16;
    int max_batch = fixed_batch_ ? static_cast<int>(fixed_batch_size_) : static_cast<int>(MaxBatchSize);
    return BackendAttributes{
        .has_mlh = false,
        .has_wdl = true,
        .runs_on_cpu = (provider_ == "cpu"),
        .suggested_num_search_threads = 2,
        .recommended_batch_size = rec_batch,
        .maximum_batch_size = max_batch
    };
}

std::unique_ptr<BackendComputation> OnnxBackend::CreateComputation() {
    return std::make_unique<OnnxComputation>(
        session_.get(),
        memory_info_,
        softmax_temp_,
        fixed_batch_,
        fixed_batch_size_
    );
}

void OnnxBackend::InitializeSession() {
    if (weights_path_.empty()) {
        throw Exception("ONNX Backend: Weight path is not set!");
    }
    
    // Reset any old session
    session_.reset();
    
    // Reset and rebuild session options
    session_options_ = Ort::SessionOptions();
    session_options_.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
    
    bool gpu_ep = false;   // true only if a real GPU Execution Provider was appended
    if (provider_ != "cpu") {
        // GPU-class provider: CUDA (Colab, -Duse_cuda) or DirectML (Windows iGPU/GPU,
        // -Duse_dml). The CUDA path keeps its fixed-batch profile; DirectML usually
        // runs dynamic batch (play = batch 1). EPs below are compiled in only when
        // the matching build flag is set, so the plain CPU build is unaffected.
        if (fixed_batch_ && fixed_batch_size_ > 0) {
            session_options_.EnableMemPattern();
            try {
                Ort::ThrowOnError(Ort::GetApi().AddFreeDimensionOverrideByName(session_options_, "batch", fixed_batch_size_));
                std::cout << "[ONNX Backend] GPU profile: fixed batch size = " << fixed_batch_size_ << std::endl;
            } catch (const std::exception& e) {
                std::cerr << "[ONNX Backend] Warning: batch-size override failed: " << e.what() << std::endl;
            }
        }
#ifdef USE_CUDA
        if (provider_ == "cuda") {
            // EXPERIMENTAL, opt-in via backend_opts "cuda_graph=1" (see --bench-nn
            // --cuda-graph). UNVERIFIED on real hardware -- no local GPU to run it.
            //
            // Why this might matter: --bench-nn's own linear fit (ms/Run ~= a +
            // b*batch) separates a FIXED per-Run cost from a per-position cost. At
            // the production profile (fixed_batch=16) that fixed cost was a large
            // share of the measured 482 us/pos (vs 322 us/pos at batch 64, where
            // the same fixed cost is amortized over 4x more positions) -- the
            // shape you'd expect from CUDA kernel-launch/dispatch overhead across
            // the ~12-block SE-ResNet, NOT from FLOPs (FLOPs/position is constant
            // across batch sizes). CUDA Graph capture replays a whole Run's kernel
            // sequence as one launch, which is aimed exactly at that fixed cost.
            //
            // Preconditions this relies on (see AddFreeDimensionOverrideByName
            // above and OnnxComputation::ComputeBlocking's padding branch): the
            // session's "batch" dim is pinned to fixed_batch_size_ at session
            // build time, and every Run() -- including padded ones -- always
            // executes at EXACTLY that shape. CUDA Graph capture requires a
            // static shape across replays; a session that ever varied its batch
            // would silently either fail or (worse) replay stale data. Do not
            // enable cuda_graph without fixed_batch.
            //
            // Before trusting this for real self-play/arena data: verify with
            // `--bench-nn --provider cuda --fixed-batch 16 --cuda-graph`, which
            // checks BOTH speed AND that graph-mode output (q/d/policy) matches
            // the non-graph path bit-for-bit-ish on the same position -- a silent
            // correctness bug here would corrupt training data, not just crash.
            if (cuda_graph_ && !(fixed_batch_ && fixed_batch_size_ > 0)) {
                std::cerr << "[ONNX Backend] WARNING: cuda_graph=1 requires fixed_batch > 0; "
                             "ignoring cuda_graph (dynamic-shape graph capture is not supported here)."
                          << std::endl;
                cuda_graph_ = false;
            }
            if (cuda_graph_) {
                OrtCUDAProviderOptionsV2* cuda_options_v2 = nullptr;
                Ort::ThrowOnError(Ort::GetApi().CreateCUDAProviderOptions(&cuda_options_v2));
                std::unique_ptr<OrtCUDAProviderOptionsV2, void(*)(OrtCUDAProviderOptionsV2*)> guard(
                    cuda_options_v2,
                    [](OrtCUDAProviderOptionsV2* p) { Ort::GetApi().ReleaseCUDAProviderOptions(p); });
                const char* keys[] = {"device_id", "enable_cuda_graph"};
                const char* values[] = {"0", "1"};
                Ort::ThrowOnError(Ort::GetApi().UpdateCUDAProviderOptions(cuda_options_v2, keys, values, 2));
                session_options_.AppendExecutionProvider_CUDA_V2(*cuda_options_v2);
                std::cout << "[ONNX Backend] CUDA Execution Provider appended WITH GRAPH CAPTURE "
                             "(device 0, EXPERIMENTAL -- verify correctness, see onnx_backend.cc)." << std::endl;
            } else {
                OrtCUDAProviderOptions cuda_options{};
                cuda_options.device_id = 0;
                session_options_.AppendExecutionProvider_CUDA(cuda_options);
                std::cout << "[ONNX Backend] CUDA Execution Provider appended (device 0)." << std::endl;
            }
            gpu_ep = true;
        }
#endif
#ifdef USE_DML
        if (provider_ == "dml") {
            // DirectML requires sequential execution and no memory-pattern optimization.
            session_options_.DisableMemPattern();
            session_options_.SetExecutionMode(ExecutionMode::ORT_SEQUENTIAL);
            Ort::ThrowOnError(OrtSessionOptionsAppendExecutionProvider_DML(session_options_, 0));
            std::cout << "[ONNX Backend] DirectML Execution Provider appended (device 0)." << std::endl;
            gpu_ep = true;
        }
#endif
        if (gpu_ep) {
            std::cout << "[ONNX Backend] GPU profile activated (" << provider_ << ")." << std::endl;
        } else {
            std::cout << "[ONNX Backend] WARNING: provider='" << provider_
                      << "' requested but its EP is not compiled into this binary "
                      << "(rebuild with -Duse_cuda=true or -Duse_dml=true) -> CPU fallback." << std::endl;
        }
    }
    if (!gpu_ep) {
        // CPU profile (also the fallback when a GPU EP isn't compiled in).
        session_options_.SetIntraOpNumThreads(intra_op_threads_);
        session_options_.SetInterOpNumThreads(1);
        session_options_.DisableMemPattern();
        std::cout << "[ONNX Backend] CPU profile activated: Dynamic batching, DisableMemPattern, IntraOp="
                  << intra_op_threads_ << std::endl;
    }
    
    std::cout << "[ONNX Backend] Loading model weights from: " << weights_path_ << std::endl;
              
    try {
#ifdef _WIN32
        std::wstring wpath(weights_path_.begin(), weights_path_.end());
        session_ = std::make_unique<Ort::Session>(env_, wpath.c_str(), session_options_);
#else
        session_ = std::make_unique<Ort::Session>(env_, weights_path_.c_str(), session_options_);
#endif
        std::cout << "[ONNX Backend] ORT Session initialized successfully." << std::endl;
    } catch (const std::exception& e) {
        throw Exception(std::string("ONNX Backend: Failed to load ONNX model: ") + e.what());
    }
}

void OnnxBackend::UpdateConfiguration(const OptionsDict& opts) {
    weights_path_ = opts.Get<std::string>(SharedBackendParams::kWeightsId);
    backend_opts_ = opts.GetOrDefault<std::string>(SharedBackendParams::kBackendOptionsId, "");

    softmax_temp_ = opts.GetOrDefault<float>(SharedBackendParams::kPolicySoftmaxTemp, 1.0f);

    // Parse backend options (e.g. "threads=4,inter_op_threads=1,provider=cpu,fixed_batch=16")
    intra_op_threads_ = 1;
    inter_op_threads_ = 1;
    provider_ = "cpu";
    fixed_batch_ = false;
    fixed_batch_size_ = 16;
    cuda_graph_ = false;

    if (!backend_opts_.empty()) {
        for (const auto& opt : split_options(backend_opts_, ',')) {
            auto parts = split_options(opt, '=');
            if (parts.size() == 2) {
                if (parts[0] == "threads" || parts[0] == "intra_op_threads") {
                    try {
                        intra_op_threads_ = std::stoi(parts[1]);
                    } catch (...) {}
                } else if (parts[0] == "inter_op_threads") {
                    try {
                        inter_op_threads_ = std::stoi(parts[1]);
                    } catch (...) {}
                } else if (parts[0] == "provider") {
                    provider_ = parts[1];
                } else if (parts[0] == "fixed_batch") {
                    // <= 0 means dynamic batch. (Kept as "fixed" on CPU/DML,
                    // fixed_batch=0 made ComputeBlocking loop forever on
                    // Run()s of batch 0, and a negative value wrapped around.)
                    try {
                        const int n = std::stoi(parts[1]);
                        fixed_batch_ = n > 0;
                        fixed_batch_size_ = n > 0 ? static_cast<size_t>(n) : 0;
                    } catch (...) {}
                } else if (parts[0] == "cuda_graph") {
                    cuda_graph_ = (parts[1] == "1" || parts[1] == "true");
                }
            }
        }
    }

    // Clamp fixed_batch_size to MaxBatchSize to prevent static buffer overflow
    if (fixed_batch_size_ > MaxBatchSize) {
        std::cerr << "[ONNX Backend] Warning: fixed_batch (" << fixed_batch_size_ 
                  << ") exceeds MaxBatchSize (" << MaxBatchSize 
                  << "). Clamping to " << MaxBatchSize << std::endl;
        fixed_batch_size_ = MaxBatchSize;
    }

    // Validate provider
    if (provider_ != "cpu" && provider_ != "cuda" && provider_ != "tensorrt" && provider_ != "dml") {
        std::cerr << "[ONNX Backend] Warning: Unknown provider '" << provider_ 
                  << "', fallback to 'cpu'" << std::endl;
        provider_ = "cpu";
    }

    // CUDA/TensorRT always use a fixed-batch profile. DirectML and CPU keep the
    // parsed value (dynamic batch unless the caller explicitly passed fixed_batch=),
    // which suits iGPU play at batch 1 — forcing batch 16 there wastes GPU work.
    if (provider_ != "cpu" && provider_ != "dml") {
        fixed_batch_ = (fixed_batch_size_ > 0);
    }

    // Reload model with new settings
    InitializeSession();
}

bool OnnxBackend::IsSameConfiguration(const OptionsDict& opts) const {
    if (!opts.Exists<std::string>(SharedBackendParams::kWeightsId)) {
        return false;
    }
    
    std::string new_weights = opts.Get<std::string>(SharedBackendParams::kWeightsId);
    std::string new_opts = opts.GetOrDefault<std::string>(SharedBackendParams::kBackendOptionsId, "");
    
    return (new_weights == weights_path_ && new_opts == backend_opts_);
}

} // namespace lczero
