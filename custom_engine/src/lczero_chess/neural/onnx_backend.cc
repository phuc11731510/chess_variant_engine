#include "neural/onnx_backend.h"
#include "chess/encoder.h"
#include "neural/shared_params.h"
#include "utils/exception.h"
#include <sstream>
#include <cmath>
#include <iostream>
#include <algorithm>

namespace lczero {

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

OnnxComputation::OnnxComputation(Ort::Session* session, Ort::MemoryInfo& memory_info, float softmax_temp)
    : session_(session), memory_info_(memory_info), softmax_temp_(softmax_temp) {
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
    size_t num_moves = pos.legal_moves.size();
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
    
    // 1. Direct Memory Mapping: map C++ float arrays directly into Ort::Value (zero-copy)
    std::array<int64_t, 4> input_shape = { static_cast<int64_t>(enqueued_), static_cast<int64_t>(InputPlanesCount), static_cast<int64_t>(BoardHeight), static_cast<int64_t>(BoardWidth) };
    Ort::Value input_tensor = Ort::Value::CreateTensor<float>(
        memory_info_,
        input_buffer_,
        enqueued_ * InputBufferUnitSize,
        input_shape.data(),
        input_shape.size()
    );
    
    std::array<int64_t, 2> policy_shape = { static_cast<int64_t>(enqueued_), static_cast<int64_t>(PolicyOutputSize) };
    Ort::Value policy_tensor = Ort::Value::CreateTensor<float>(
        memory_info_,
        policy_output_buffer_,
        enqueued_ * PolicyOutputSize,
        policy_shape.data(),
        policy_shape.size()
    );
    
    std::array<int64_t, 2> value_shape = { static_cast<int64_t>(enqueued_), static_cast<int64_t>(ValueOutputSize) };
    Ort::Value value_tensor = Ort::Value::CreateTensor<float>(
        memory_info_,
        value_output_buffer_,
        enqueued_ * ValueOutputSize,
        value_shape.data(),
        value_shape.size()
    );
    
    // 2. Setup inputs and outputs pointers
    const char* input_names[] = { "input" };
    char* output_names[] = { "policy", "value" };
    
    Ort::Value inputs[] = { std::move(input_tensor) };
    Ort::Value outputs[] = { std::move(policy_tensor), std::move(value_tensor) };
    
    // 3. Execute inference synchronously on CPU
    session_->Run(
        Ort::RunOptions{nullptr},
        input_names,
        inputs,
        1,
        output_names,
        outputs,
        2
    );
    
    // 4. Fill results and execute Softmax for legal moves
    for (size_t b = 0; b < enqueued_; ++b) {
        float* raw_policy = policy_output_buffer_ + b * PolicyOutputSize;
        float* raw_value = value_output_buffer_ + b * ValueOutputSize;
        EvalResultPtr res = results_[b];
        
        // 4.1. Extract WDL value (win, draw, loss probabilities)
        float win = raw_value[0];
        float draw = raw_value[1];
        float loss = raw_value[2];
        
        // Softmax normalization for WDL output (raw logits to probabilities)
        float max_wdl = std::max({win, draw, loss});
        float exp_w = std::exp(win - max_wdl);
        float exp_d = std::exp(draw - max_wdl);
        float exp_l = std::exp(loss - max_wdl);
        float sum_wdl = exp_w + exp_d + exp_l;
        win = exp_w / sum_wdl;
        draw = exp_d / sum_wdl;
        loss = exp_l / sum_wdl;
        
        if (res.q) *res.q = win - loss; // Q value in [-1.0, 1.0]
        if (res.d) *res.d = draw;       // Draw probability in [0.0, 1.0]
        if (res.m) *res.m = 50.0f;      // Fallback moves left value
        
        // 4.2. Extract Policy probabilities
        size_t num_legal = position_moves_[b].size();
        if (num_legal > 0 && !res.p.empty()) {
            alignas(64) float legal_logits[384];
            float max_logit = -1e9f;
            
            // Map legal moves to ONNX output indices and fetch logits
            for (size_t i = 0; i < num_legal; ++i) {
                Move NN_move = position_moves_[b][i];
                int index = MoveToNNIndex(NN_move, 0);
                legal_logits[i] = raw_policy[index];
                if (legal_logits[i] > max_logit) {
                    max_logit = legal_logits[i];
                }
            }
            
            // Calculate Softmax
            float sum = 0.0f;
            float temp = std::max(1e-3f, softmax_temp_); // Avoid division by zero
            for (size_t i = 0; i < num_legal; ++i) {
                legal_logits[i] = std::exp((legal_logits[i] - max_logit) / temp);
                sum += legal_logits[i];
            }
            
            for (size_t i = 0; i < num_legal && i < res.p.size(); ++i) {
                res.p[i] = legal_logits[i] / sum;
            }
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
    session_options_.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
}

BackendAttributes OnnxBackend::GetAttributes() const {
    return BackendAttributes{
        .has_mlh = false,
        .has_wdl = true,
        .runs_on_cpu = true,
        .suggested_num_search_threads = 1,
        .recommended_batch_size = 1,
        .maximum_batch_size = static_cast<int>(MaxBatchSize)
    };
}

std::unique_ptr<BackendComputation> OnnxBackend::CreateComputation() {
    return std::make_unique<OnnxComputation>(session_.get(), memory_info_, softmax_temp_);
}

void OnnxBackend::InitializeSession() {
    if (weights_path_.empty()) {
        throw Exception("ONNX Backend: Weight path is not set!");
    }
    
    // Reset any old session
    session_.reset();
    
    // Configure CPU performance settings
    session_options_.SetIntraOpNumThreads(intra_op_threads_);
    session_options_.SetInterOpNumThreads(inter_op_threads_);
    
    std::cout << "[ONNX Backend] Loading model weights from: " << weights_path_ << std::endl;
    std::cout << "[ONNX Backend] Threading configuration: IntraOp=" << intra_op_threads_ 
              << ", InterOp=" << inter_op_threads_ << std::endl;
              
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
    
    // Parse backend options (e.g. "threads=4,inter_op_threads=1")
    intra_op_threads_ = 1;
    inter_op_threads_ = 1;
    
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
                }
            }
        }
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
