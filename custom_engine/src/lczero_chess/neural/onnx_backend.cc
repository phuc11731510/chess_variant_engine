#include "neural/onnx_backend.h"
#include "neural/network_output.h"
#include "neural/ort_loader.h"
#include "chess/encoder.h"
#include "neural/shared_params.h"
#include "utils/exception.h"
#include <sstream>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <algorithm>
#include <limits>
#ifdef USE_DML
// DirectML EP factory (only in the DirectML ONNX Runtime package).
#include "dml_provider_factory.h"
#endif
#ifdef __ANDROID__
// NNAPI EP factory (in the Android ONNX Runtime package): hands the graph to the phone's accelerator driver.
#include "nnapi_provider_factory.h"
#endif

namespace lczero {

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

OnnxComputation::OnnxComputation(Ort::Session* session, Ort::MemoryInfo& memory_info, float softmax_temp, bool fixed_batch, size_t fixed_batch_size,
                                 const std::vector<std::pair<size_t, Ort::Session*>>* small_sessions)
    : session_(session), small_sessions_(small_sessions), memory_info_(memory_info),
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
      mlh_output_buffer_(new float[slots_ * MlhOutputSize]),
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

    // Encode board features using position history. ALWAYS is fixed here (lc0's "always" mode): the
    // HistoryFill option is NOT read. A history board that does not exist yet (the first moves of a game)
    // is a copy of the first position of the game, for every game, whatever its start position -- the
    // training records (training_extract.cc) are encoded the same way. (Before 2026-10-17 the encoder
    // treated FEN_ONLY as NO, so a position given as a bare FEN reached the net with 7 all-zero history
    // boards -- never seen in training -- and gen79's raw value was off by 0.87 on average. 2026-11-20:
    // ALWAYS instead of FEN_ONLY, so a game from the variant's own start position is filled too.)
    alignas(64) InputPlanes planes;
    int transform = 0;
    EncodePositionForNN(*pos.history, kMoveHistory, FillEmptyHistory::ALWAYS, &planes, &transform);

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
std::atomic<uint64_t> g_eval_run_ns{0};
std::atomic<uint64_t> g_eval_compute_ns{0};
uint64_t NsSince(std::chrono::steady_clock::time_point t0) {
    return static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                                     std::chrono::steady_clock::now() - t0).count());
}
}  // namespace

OnnxEvalCounters OnnxGetEvalCounters() {
    return {g_eval_real.load(std::memory_order_relaxed),
            g_eval_padded.load(std::memory_order_relaxed),
            g_eval_runs.load(std::memory_order_relaxed),
            g_eval_run_ns.load(std::memory_order_relaxed),
            g_eval_compute_ns.load(std::memory_order_relaxed)};
}

void OnnxResetEvalCounters() {
    g_eval_real.store(0, std::memory_order_relaxed);
    g_eval_padded.store(0, std::memory_order_relaxed);
    g_eval_runs.store(0, std::memory_order_relaxed);
    g_eval_run_ns.store(0, std::memory_order_relaxed);
    g_eval_compute_ns.store(0, std::memory_order_relaxed);
}

void OnnxCountRun(uint64_t real, uint64_t padded, uint64_t run_ns) {
    g_eval_real.fetch_add(real, std::memory_order_relaxed);
    g_eval_padded.fetch_add(padded, std::memory_order_relaxed);
    g_eval_runs.fetch_add(1, std::memory_order_relaxed);
    g_eval_run_ns.fetch_add(run_ns, std::memory_order_relaxed);
}

void OnnxCountCompute(uint64_t compute_ns) { g_eval_compute_ns.fetch_add(compute_ns, std::memory_order_relaxed); }

void OnnxComputation::ComputeBlocking() {
    // Every AddInput has returned by now (the search joins its task threads
    // first), so this count is final and every slot below it is filled.
    const size_t enqueued = enqueued_.load(std::memory_order_acquire);
    if (enqueued == 0) return;
    if (!session_) {
        throw Exception("ONNX Backend: ORT session is not initialized!");
    }
    const auto t_compute = std::chrono::steady_clock::now();

    size_t offset = 0;
    while (offset < enqueued) {
        size_t current_batch = enqueued - offset;
        if (fixed_batch_ && current_batch > fixed_batch_size_) {
            current_batch = fixed_batch_size_;
        }
        
        size_t run_batch = fixed_batch_ ? fixed_batch_size_ : current_batch;
        // B3: a smaller pinned session that still fits pads less (each session
        // always runs its own fixed shape, so nothing is re-planned per Run).
        Ort::Session* run_session = session_;
        if (fixed_batch_ && small_sessions_ && current_batch < fixed_batch_size_) {
            for (const auto& [size, sess] : *small_sessions_) {
                if (size >= current_batch) {
                    run_batch = size;
                    run_session = sess;
                    break;
                }
            }
        }
        
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
        
        std::array<int64_t, 2> mlh_shape = { static_cast<int64_t>(run_batch), static_cast<int64_t>(MlhOutputSize) };
        Ort::Value mlh_tensor = Ort::Value::CreateTensor<float>(
            memory_info_,
            mlh_output_buffer_.get() + offset * MlhOutputSize,
            run_batch * MlhOutputSize,
            mlh_shape.data(),
            mlh_shape.size()
        );
        
        // 2. Setup inputs and outputs pointers
        const char* input_names[] = { "input" };
        char* output_names[] = { "policy", "value", "mlh" };
        
        Ort::Value inputs[] = { std::move(input_tensor) };
        Ort::Value outputs[] = { std::move(policy_tensor), std::move(value_tensor), std::move(mlh_tensor) };
        
        // 3. Execute inference synchronously on CPU/GPU
        const auto t_run = std::chrono::steady_clock::now();
        run_session->Run(
            Ort::RunOptions{nullptr},
            input_names,
            inputs,
            1,
            output_names,
            outputs,
            3
        );
        
        // Instrumentation (see OnnxEvalCounters): current_batch is what the
        // search asked for, run_batch is what the device actually computed.
        g_eval_real.fetch_add(current_batch, std::memory_order_relaxed);
        g_eval_padded.fetch_add(run_batch, std::memory_order_relaxed);
        g_eval_runs.fetch_add(1, std::memory_order_relaxed);
        g_eval_run_ns.fetch_add(NsSince(t_run), std::memory_order_relaxed);

        offset += current_batch;
    }
    
    // 4. Fill results: the legal moves' logits are gathered from the full policy output, FillEvalResult checks the
    // outputs and does the rest (WDL, moves left, softmax over the legal moves).
    for (size_t b = 0; b < enqueued; ++b) {
        const float* raw_policy = policy_output_buffer_.get() + b * PolicyOutputSize;
        const size_t num_legal = std::min(position_moves_[b].size(), static_cast<size_t>(384));
        alignas(64) float legal_logits[384];
        for (size_t i = 0; i < num_legal; ++i) {
            const uint16_t index = MoveToNNIndex(position_moves_[b][i], 0);
            // Every legal move has an index (--test-policy); an unmapped one gets probability 0 rather than an
            // arbitrary logit.
            legal_logits[i] = index < PolicyOutputSize ? raw_policy[index] : -std::numeric_limits<float>::infinity();
        }
        FillEvalResult(results_[b], value_output_buffer_.get() + b * ValueOutputSize, mlh_output_buffer_[b * MlhOutputSize],
                       legal_logits, num_legal, softmax_temp_, "ONNX Backend");
    }

    // Reset batch counter
    enqueued_.store(0, std::memory_order_release);
    g_eval_compute_ns.fetch_add(NsSince(t_compute), std::memory_order_relaxed);
}

// ==========================================
// OnnxBackend Implementation
// ==========================================

namespace {
// ONNX Runtime must be loaded (a Linux build that dlopens it) before the first Ort:: object, and env_ is the first one.
Ort::Env MakeEnv() {
    EnsureOnnxRuntime();
    return Ort::Env(ORT_LOGGING_LEVEL_WARNING, "ONNX_Backend");
}
}  // namespace

OnnxBackend::OnnxBackend()
    : env_(MakeEnv()),
      memory_info_(Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault)) {
}

std::string OnnxBackend::EndProfilingForBench() {
    if (profile_prefix_.empty() || !session_) return "";
    Ort::AllocatorWithDefaultOptions alloc;
    return session_->EndProfilingAllocated(alloc).get();
}

BackendAttributes OnnxBackend::GetAttributes() const {
    int rec_batch = fixed_batch_ ? static_cast<int>(fixed_batch_size_) : 16;
    int max_batch = fixed_batch_ ? static_cast<int>(fixed_batch_size_) : static_cast<int>(MaxBatchSize);
    return BackendAttributes{
        .has_mlh = true,
        .has_wdl = true,
        .runs_on_cpu = (provider_ == "cpu" || provider_ == "xnnpack"),
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
        fixed_batch_size_,
        &small_sessions_
    );
}

void OnnxBackend::InitializeSession() {
    session_.reset();
    small_sessions_.clear();
    small_owned_.clear();
    session_ = BuildSession(fixed_batch_ ? fixed_batch_size_ : 0);
    // B3: extra sessions only make sense with a pinned batch on a GPU provider.
    if (fixed_batch_ && provider_ != "cpu" && provider_ != "xnnpack") {
        std::vector<size_t> sizes;
        for (size_t b : extra_batches_)
            if (b > 0 && b < fixed_batch_size_) sizes.push_back(b);
        std::sort(sizes.begin(), sizes.end());
        sizes.erase(std::unique(sizes.begin(), sizes.end()), sizes.end());
        for (size_t b : sizes) {
            small_owned_.push_back(BuildSession(b));
            small_sessions_.emplace_back(b, small_owned_.back().get());
        }
        if (!sizes.empty()) {
            std::cout << "[ONNX Backend] extra batch sessions:";
            for (size_t b : sizes) std::cout << " " << b;
            std::cout << " (+ " << fixed_batch_size_ << ")" << std::endl;
        }
    }
}

std::unique_ptr<Ort::Session> OnnxBackend::BuildSession(size_t batch) {
    if (weights_path_.empty()) {
        throw Exception("ONNX Backend: Weight path is not set!");
    }

    // Reset and rebuild session options
    session_options_ = Ort::SessionOptions();
    session_options_.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
    if (!profile_prefix_.empty()) {
#ifdef _WIN32
        const std::wstring wprefix(profile_prefix_.begin(), profile_prefix_.end());
        session_options_.EnableProfiling(wprefix.c_str());
#else
        session_options_.EnableProfiling(profile_prefix_.c_str());
#endif
        std::cout << "[ONNX Backend] ORT profiling ON (prefix " << profile_prefix_ << ")" << std::endl;
    }

    bool gpu_ep = false;   // true only if a real GPU Execution Provider was appended
    if (provider_ != "cpu" && provider_ != "xnnpack") {
        // GPU-class provider: CUDA (Colab, -Duse_cuda) or DirectML (Windows iGPU/GPU,
        // -Duse_dml). The CUDA path keeps its fixed-batch profile; DirectML usually
        // runs dynamic batch (play = batch 1). EPs below are compiled in only when
        // the matching build flag is set, so the plain CPU build is unaffected.
        if (batch > 0) {
            session_options_.EnableMemPattern();
            try {
                Ort::ThrowOnError(Ort::GetApi().AddFreeDimensionOverrideByName(session_options_, "batch", batch));
                std::cout << "[ONNX Backend] GPU profile: fixed batch size = " << batch << std::endl;
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
            if (cuda_graph_ && !(batch > 0)) {
                std::cerr << "[ONNX Backend] WARNING: cuda_graph=1 requires fixed_batch > 0; "
                             "ignoring cuda_graph (dynamic-shape graph capture is not supported here)."
                          << std::endl;
                cuda_graph_ = false;
            }
            if (cuda_graph_ || !cuda_opts_.empty()) {
                // V2 options: graph capture and/or --cuda-opt keys. An unknown key
                // or bad value throws here -> the run stops (no silent default).
                OrtCUDAProviderOptionsV2* cuda_options_v2 = nullptr;
                Ort::ThrowOnError(Ort::GetApi().CreateCUDAProviderOptions(&cuda_options_v2));
                std::unique_ptr<OrtCUDAProviderOptionsV2, void(*)(OrtCUDAProviderOptionsV2*)> guard(
                    cuda_options_v2,
                    [](OrtCUDAProviderOptionsV2* p) { Ort::GetApi().ReleaseCUDAProviderOptions(p); });
                std::vector<const char*> keys{"device_id"};
                std::vector<const char*> values{"0"};
                if (cuda_graph_) {
                    keys.push_back("enable_cuda_graph");
                    values.push_back("1");
                }
                for (const auto& kv : cuda_opts_) {
                    keys.push_back(kv.first.c_str());
                    values.push_back(kv.second.c_str());
                }
                Ort::ThrowOnError(Ort::GetApi().UpdateCUDAProviderOptions(
                    cuda_options_v2, keys.data(), values.data(), keys.size()));
                session_options_.AppendExecutionProvider_CUDA_V2(*cuda_options_v2);
                std::cout << "[ONNX Backend] CUDA Execution Provider appended (device 0";
                if (cuda_graph_)
                    std::cout << ", WITH GRAPH CAPTURE -- EXPERIMENTAL, verify correctness";
                for (const auto& kv : cuda_opts_) std::cout << ", " << kv.first << "=" << kv.second;
                std::cout << ")." << std::endl;
            } else {
                OrtCUDAProviderOptions cuda_options{};
                cuda_options.device_id = 0;
                session_options_.AppendExecutionProvider_CUDA(cuda_options);
                std::cout << "[ONNX Backend] CUDA Execution Provider appended (device 0)." << std::endl;
            }
            gpu_ep = true;
        }
        if (provider_ == "tensorrt") {
            // TensorRT EP (A2): builds an engine for this net on first use (minutes),
            // cached on disk under trt_engine_cache_path and reused. Needs the
            // TensorRT 10 libs (libnvinfer*.so.10, libnvonnxparser.so.10) on
            // LD_LIBRARY_PATH. fp32 only (trt_fp16_enable=0). Nodes TensorRT cannot
            // take fall back to the CUDA EP appended after it. --trt-opt key=value
            // adds/overrides any TensorRT EP option (an unknown key stops the run).
            std::vector<std::pair<std::string, std::string>> kv = {
                {"device_id", "0"},
                {"trt_fp16_enable", "0"},
                {"trt_engine_cache_enable", "1"},
                {"trt_engine_cache_path", "trt_cache"},
                {"trt_timing_cache_enable", "1"},
                {"trt_timing_cache_path", "trt_cache"},
            };
            if (!(batch > 0)) {
                // Dynamic batch: one optimization profile 1..MaxBatchSize, tuned at the max.
                const std::string dims = "x" + std::to_string(InputPlanesCount) + "x" +
                                         std::to_string(BoardHeight) + "x" + std::to_string(BoardWidth);
                kv.push_back({"trt_profile_min_shapes", "input:1" + dims});
                kv.push_back({"trt_profile_max_shapes", "input:" + std::to_string(MaxBatchSize) + dims});
                kv.push_back({"trt_profile_opt_shapes", "input:" + std::to_string(MaxBatchSize) + dims});
            }
            for (const auto& o : trt_opts_) {
                bool replaced = false;
                for (auto& d : kv)
                    if (d.first == o.first) { d.second = o.second; replaced = true; }
                if (!replaced) kv.push_back(o);
            }
            OrtTensorRTProviderOptionsV2* trt = nullptr;
            Ort::ThrowOnError(Ort::GetApi().CreateTensorRTProviderOptions(&trt));
            std::unique_ptr<OrtTensorRTProviderOptionsV2, void(*)(OrtTensorRTProviderOptionsV2*)> guard(
                trt, [](OrtTensorRTProviderOptionsV2* p) { Ort::GetApi().ReleaseTensorRTProviderOptions(p); });
            std::vector<const char*> keys, values;
            for (const auto& p : kv) {
                keys.push_back(p.first.c_str());
                values.push_back(p.second.c_str());
            }
            Ort::ThrowOnError(Ort::GetApi().UpdateTensorRTProviderOptions(
                trt, keys.data(), values.data(), keys.size()));
            session_options_.AppendExecutionProvider_TensorRT_V2(*trt);
            OrtCUDAProviderOptions cuda_options{};
            cuda_options.device_id = 0;
            session_options_.AppendExecutionProvider_CUDA(cuda_options);
            std::cout << "[ONNX Backend] TensorRT Execution Provider appended (+ CUDA fallback):";
            for (const auto& p : kv) std::cout << " " << p.first << "=" << p.second;
            std::cout << std::endl;
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
#ifdef __ANDROID__
        if (provider_ == "nnapi") {
            // NNAPI compiles a fixed-shape model (the batch override above); the nodes it cannot take run on the CPU EP.
            // nnapi_opts_: fp16 (allow FP16 arithmetic), cpu_disabled (no NNAPI CPU reference device), cpu_only (debug).
            uint32_t flags = NNAPI_FLAG_USE_NONE;
            for (const auto& kv : nnapi_opts_) {
                const bool on = kv.second == "1" || kv.second == "true";
                if (kv.first == "fp16") { if (on) flags |= NNAPI_FLAG_USE_FP16; }
                else if (kv.first == "cpu_disabled") { if (on) flags |= NNAPI_FLAG_CPU_DISABLED; }
                else if (kv.first == "cpu_only") { if (on) flags |= NNAPI_FLAG_CPU_ONLY; }
                else throw Exception("ONNX Backend: unknown NNAPI option nnapi." + kv.first + " (fp16, cpu_disabled, cpu_only)");
            }
            session_options_.SetIntraOpNumThreads(intra_op_threads_);   // the CPU EP still runs what NNAPI leaves
            Ort::ThrowOnError(OrtSessionOptionsAppendExecutionProvider_Nnapi(session_options_, flags));
            std::cout << "[ONNX Backend] NNAPI Execution Provider appended (flags " << flags << ")." << std::endl;
            gpu_ep = true;
        }
#endif
        if (gpu_ep) {
            std::cout << "[ONNX Backend] GPU profile activated (" << provider_ << ")." << std::endl;
        } else {
            std::cout << "[ONNX Backend] WARNING: provider='" << provider_
                      << "' requested but its EP is not compiled into this binary "
                      << "(rebuild with -Duse_cuda=true or -Duse_dml=true; nnapi needs the Android build) -> CPU fallback." << std::endl;
        }
    }
    if (!gpu_ep) {
        // CPU profile (also the fallback when a GPU EP isn't compiled in).
        session_options_.SetIntraOpNumThreads(intra_op_threads_);
        session_options_.SetInterOpNumThreads(1);
        session_options_.DisableMemPattern();
        if (provider_ == "xnnpack") {
            // XNNPACK (ARM / x86 CPU kernels, in the Android and the default packages) runs its own thread pool: ORT's
            // pool stays at one thread without spinning so the two do not compete (ONNX Runtime's XNNPACK guidance).
            session_options_.SetIntraOpNumThreads(1);
            session_options_.AddConfigEntry("session.intra_op.allow_spinning", "0");
            session_options_.AppendExecutionProvider("XNNPACK", {{"intra_op_num_threads", std::to_string(intra_op_threads_)}});
            std::cout << "[ONNX Backend] XNNPACK Execution Provider appended (" << intra_op_threads_ << " threads)." << std::endl;
        }
        std::cout << "[ONNX Backend] CPU profile activated: Dynamic batching, DisableMemPattern, IntraOp="
                  << intra_op_threads_ << std::endl;
    }
    
    std::cout << "[ONNX Backend] Loading model weights from: " << weights_path_ << std::endl;
              
    try {
#ifdef _WIN32
        std::wstring wpath(weights_path_.begin(), weights_path_.end());
        auto session = std::make_unique<Ort::Session>(env_, wpath.c_str(), session_options_);
#else
        auto session = std::make_unique<Ort::Session>(env_, weights_path_.c_str(), session_options_);
#endif
        // The graph must have exactly the interface this backend reads: input "input", outputs "policy",
        // "value", "mlh" (python/train.py's ExportNet). A network from before the moves-left head, or a
        // renamed output, would otherwise fail inside Run() with an opaque message.
        {
            Ort::AllocatorWithDefaultOptions alloc;
            std::vector<std::string> outs;
            for (size_t i = 0; i < session->GetOutputCount(); ++i)
                outs.push_back(session->GetOutputNameAllocated(i, alloc).get());
            for (const char* want : {"policy", "value", "mlh"}) {
                if (std::find(outs.begin(), outs.end(), want) == outs.end())
                    throw Exception(std::string("ONNX Backend: the network has no output named \"") + want +
                                    "\" (it needs policy, value and mlh; see python/train.py ExportNet). "
                                    "A network trained before the moves-left head cannot be used.");
            }
        }
        std::cout << "[ONNX Backend] ORT Session initialized successfully." << std::endl;
        return session;
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
    cuda_opts_.clear();
    trt_opts_.clear();
    nnapi_opts_.clear();
    extra_batches_.clear();
    profile_prefix_.clear();

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
                } else if (parts[0].rfind("trt.", 0) == 0 && parts[0].size() > 4) {
                    trt_opts_.emplace_back(parts[0].substr(4), parts[1]);
                } else if (parts[0] == "extra_batches") {
                    for (const auto& v : split_options(parts[1], ':')) {
                        try {
                            const int n = std::stoi(v);
                            if (n > 0) extra_batches_.push_back(static_cast<size_t>(n));
                        } catch (...) {}
                    }
                } else if (parts[0] == "profile") {
                    profile_prefix_ = parts[1];
                } else if (parts[0].rfind("nnapi.", 0) == 0 && parts[0].size() > 6) {
                    nnapi_opts_.emplace_back(parts[0].substr(6), parts[1]);
                } else if (parts[0].rfind("cuda.", 0) == 0 && parts[0].size() > 5) {
                    cuda_opts_.emplace_back(parts[0].substr(5), parts[1]);
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
    if (provider_ != "cpu" && provider_ != "cuda" && provider_ != "tensorrt" && provider_ != "dml" &&
        provider_ != "nnapi" && provider_ != "xnnpack") {
        std::cerr << "[ONNX Backend] Warning: Unknown provider '" << provider_ 
                  << "', fallback to 'cpu'" << std::endl;
        provider_ = "cpu";
    }

    // CUDA/TensorRT always use a fixed-batch profile. DirectML and CPU keep the
    // parsed value (dynamic batch unless the caller explicitly passed fixed_batch=),
    // which suits iGPU play at batch 1 — forcing batch 16 there wastes GPU work.
    if (provider_ != "cpu" && provider_ != "dml" && provider_ != "xnnpack") {
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
