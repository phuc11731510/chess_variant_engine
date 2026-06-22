#include "neural/onnx_backend.h"
#include "chess/encoder.h"
#include "neural/shared_params.h"
#include "utils/exception.h"
#include <sstream>
#include <cmath>
#include <iostream>
#include <algorithm>
#include <immintrin.h>

#ifdef USE_DML
// DirectML EP factory (only in the DirectML ONNX Runtime package).
#include "dml_provider_factory.h"
#endif

namespace lczero {

// AVX2 exp approximation helper function compiled with AVX2 and FMA
#if defined(__GNUC__) || defined(__clang__)
__attribute__((target("avx2,fma")))
#endif
inline __m256 avx2_exp_approx(__m256 x) {
    // Clamp to prevent negative base when squaring
    __m256 x_clamped = _mm256_max_ps(x, _mm256_set1_ps(-80.0f));
    
    // (1 + x/1024)^1024
    __m256 y = _mm256_fmadd_ps(x_clamped, _mm256_set1_ps(1.0f / 1024.0f), _mm256_set1_ps(1.0f));
    
    // 10 squarings to compute power of 1024
    y = _mm256_mul_ps(y, y); // 2nd power
    y = _mm256_mul_ps(y, y); // 4th
    y = _mm256_mul_ps(y, y); // 8th
    y = _mm256_mul_ps(y, y); // 16th
    y = _mm256_mul_ps(y, y); // 32nd
    y = _mm256_mul_ps(y, y); // 64th
    y = _mm256_mul_ps(y, y); // 128th
    y = _mm256_mul_ps(y, y); // 256th
    y = _mm256_mul_ps(y, y); // 512th
    y = _mm256_mul_ps(y, y); // 1024th
    
    return y;
}

#if defined(__GNUC__) || defined(__clang__)
__attribute__((target("avx2,fma")))
#endif
inline void avx2_softmax(float* legal_logits, size_t num_legal, float softmax_temp, float max_logit, float* out_p, size_t max_out_size) {
    size_t num_legal_rounded = (num_legal + 7) & ~7;
    for (size_t i = num_legal; i < num_legal_rounded; ++i) {
        legal_logits[i] = -100.0f;
    }
    
    float temp = std::max(1e-3f, softmax_temp);
    float inv_temp = 1.0f / temp;
    
    __m256 max_val_vec = _mm256_set1_ps(max_logit);
    __m256 inv_temp_vec = _mm256_set1_ps(inv_temp);
    __m256 sum_vec = _mm256_setzero_ps();
    
    for (size_t i = 0; i < num_legal_rounded; i += 8) {
        __m256 val = _mm256_load_ps(&legal_logits[i]);
        __m256 diff = _mm256_sub_ps(val, max_val_vec);
        __m256 scaled = _mm256_mul_ps(diff, inv_temp_vec);
        __m256 res_exp = avx2_exp_approx(scaled);
        _mm256_store_ps(&legal_logits[i], res_exp);
        sum_vec = _mm256_add_ps(sum_vec, res_exp);
    }
    
    alignas(32) float sum_arr[8];
    _mm256_store_ps(sum_arr, sum_vec);
    float sum = 0.0f;
    for (int i = 0; i < 8; ++i) {
        sum += sum_arr[i];
    }
    
    float inv_sum = 1.0f / (sum > 0.0f ? sum : 1.0f);
    __m256 inv_sum_vec = _mm256_set1_ps(inv_sum);
    
    for (size_t i = 0; i < num_legal_rounded; i += 8) {
        __m256 val = _mm256_load_ps(&legal_logits[i]);
        __m256 normalized = _mm256_mul_ps(val, inv_sum_vec);
        _mm256_store_ps(&legal_logits[i], normalized);
    }
    
    for (size_t i = 0; i < num_legal && i < max_out_size; ++i) {
        out_p[i] = legal_logits[i];
    }
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
    : session_(session), memory_info_(memory_info), softmax_temp_(softmax_temp), fixed_batch_(fixed_batch), fixed_batch_size_(fixed_batch_size) {
    std::memset(input_buffer_, 0, sizeof(input_buffer_));
    std::memset(policy_output_buffer_, 0, sizeof(policy_output_buffer_));
    std::memset(value_output_buffer_, 0, sizeof(value_output_buffer_));
}

BackendComputation::AddInputResult OnnxComputation::AddInput(
    const EvalPosition& pos,
    EvalResultPtr result) {
    
    if (enqueued_ >= MaxBatchSize) {
        throw Exception("ONNX Backend: Maximum batch size exceeded!");
    }
    
    // Save pointers to output destination
    results_[enqueued_] = result;
    
    // Save legal moves list
    size_t num_moves = std::min(pos.legal_moves.size(), static_cast<size_t>(384));
    position_moves_[enqueued_].resize(num_moves);
    for (size_t i = 0; i < num_moves; ++i) {
        position_moves_[enqueued_][i] = pos.legal_moves[i];
    }
    
    // Encode board features using position history
    alignas(64) InputPlanes planes;
    int transform = 0;
    EncodePositionForNN(*pos.history, kMoveHistory, FillEmptyHistory::FEN_ONLY, &planes, &transform);
    
    // Unpack bits into flat float buffer
    float* current_input_ptr = input_buffer_ + enqueued_ * InputBufferUnitSize;
    UnpackInputPlanes(planes, current_input_ptr, BoardWidth, BoardHeight);
    
    enqueued_++;
    return ENQUEUED_FOR_EVAL;
}

void OnnxComputation::ComputeBlocking() {
    if (enqueued_ == 0) return;
    if (!session_) {
        throw Exception("ONNX Backend: ORT session is not initialized!");
    }
    
    size_t offset = 0;
    while (offset < enqueued_) {
        size_t current_batch = enqueued_ - offset;
        if (fixed_batch_ && current_batch > fixed_batch_size_) {
            current_batch = fixed_batch_size_;
        }
        
        size_t run_batch = fixed_batch_ ? fixed_batch_size_ : current_batch;
        
        if (fixed_batch_ && run_batch > current_batch) {
            size_t pad_count = run_batch - current_batch;
            std::memset(input_buffer_ + (offset + current_batch) * InputBufferUnitSize, 0, pad_count * InputBufferUnitSize * sizeof(float));
        }
        
        // 1. Direct Memory Mapping: map C++ float arrays directly into Ort::Value (zero-copy)
        std::array<int64_t, 4> input_shape = { static_cast<int64_t>(run_batch), static_cast<int64_t>(InputPlanesCount), static_cast<int64_t>(BoardHeight), static_cast<int64_t>(BoardWidth) };
        Ort::Value input_tensor = Ort::Value::CreateTensor<float>(
            memory_info_,
            input_buffer_ + offset * InputBufferUnitSize,
            run_batch * InputBufferUnitSize,
            input_shape.data(),
            input_shape.size()
        );
        
        std::array<int64_t, 2> policy_shape = { static_cast<int64_t>(run_batch), static_cast<int64_t>(PolicyOutputSize) };
        Ort::Value policy_tensor = Ort::Value::CreateTensor<float>(
            memory_info_,
            policy_output_buffer_ + offset * PolicyOutputSize,
            run_batch * PolicyOutputSize,
            policy_shape.data(),
            policy_shape.size()
        );
        
        std::array<int64_t, 2> value_shape = { static_cast<int64_t>(run_batch), static_cast<int64_t>(ValueOutputSize) };
        Ort::Value value_tensor = Ort::Value::CreateTensor<float>(
            memory_info_,
            value_output_buffer_ + offset * ValueOutputSize,
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
        
        offset += current_batch;
    }
    
    // 4. Fill results and execute Softmax for legal moves
    for (size_t b = 0; b < enqueued_; ++b) {
        float* raw_policy = policy_output_buffer_ + b * PolicyOutputSize;
        float* raw_value = value_output_buffer_ + b * ValueOutputSize;
        EvalResultPtr res = results_[b];
        
        // 4.1. Extract WDL value (win, draw, loss probabilities)
        float win = raw_value[0];
        float draw = raw_value[1];
        float loss = raw_value[2];
        
        if (res.q) *res.q = win - loss; // Q value in [-1.0, 1.0]
        if (res.d) *res.d = draw;       // Draw probability in [0.0, 1.0]
        if (res.m) *res.m = 50.0f;      // Fallback moves left value
        
        // 4.2. Extract Policy probabilities
        size_t num_legal = std::min(position_moves_[b].size(), static_cast<size_t>(384));
        if (num_legal > 0 && !res.p.empty()) {
            alignas(64) float legal_logits[384];
            float max_logit = -1e9f;
            
            // Map legal moves to ONNX output indices and fetch logits
            for (size_t i = 0; i < num_legal; ++i) {
                Move NN_move = position_moves_[b][i];
                int index = MoveToNNIndex(NN_move, 0);
                if (index >= 0 && index < 10600) {
                    legal_logits[i] = raw_policy[index];
                } else {
                    legal_logits[i] = -100.0f; // An extremely low probability for safety
                }
                if (legal_logits[i] > max_logit) {
                    max_logit = legal_logits[i];
                }
            }
            
            // Calculate Softmax using AVX2 SIMD helper
            avx2_softmax(legal_logits, num_legal, softmax_temp_, max_logit, res.p.data(), res.p.size());
        }
    }
    
    // Reset batch counter
    enqueued_ = 0;
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
            OrtCUDAProviderOptions cuda_options{};
            cuda_options.device_id = 0;
            session_options_.AppendExecutionProvider_CUDA(cuda_options);
            std::cout << "[ONNX Backend] CUDA Execution Provider appended (device 0)." << std::endl;
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
                    try {
                        fixed_batch_size_ = std::stoi(parts[1]);
                        fixed_batch_ = true;
                    } catch (...) {}
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
    if (provider_ != "cpu" && provider_ != "cuda" && provider_ != "tensorrt") {
        std::cerr << "[ONNX Backend] Warning: Unknown provider '" << provider_ 
                  << "', fallback to 'cpu'" << std::endl;
        provider_ = "cpu";
    }

    // Single source of truth for fixed batch
    fixed_batch_ = (provider_ != "cpu" && fixed_batch_size_ > 0);

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
