import sys
import io
# Thiết lập mã hóa stdout/stderr thành UTF-8 để khắc phục lỗi in emoji trên Windows Console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import torch
import torch.nn as nn
import os

class ResidualBlock(nn.Module):
    def __init__(self, filters):
        super(ResidualBlock, self).__init__()
        self.conv1 = nn.Conv2d(filters, filters, kernel_size=3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(filters)
        self.relu = nn.ReLU()
        self.conv2 = nn.Conv2d(filters, filters, kernel_size=3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(filters)

    def forward(self, x):
        residual = x
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.conv2(out)
        out = self.bn2(out)
        out += residual
        out = self.relu(out)
        return out

class ChessNet10x10(nn.Module):
    def __init__(self, num_blocks=10, filters=128):
        super(ChessNet10x10, self).__init__()
        
        # 1. Conv Block đầu tiên: 226 input planes -> 128 filters
        self.conv_in = nn.Conv2d(226, filters, kernel_size=3, padding=1, bias=False)
        self.bn_in = nn.BatchNorm2d(filters)
        self.relu = nn.ReLU()
        
        # 2. Backbone: 10 Residual Blocks
        self.backbone = nn.Sequential(*[ResidualBlock(filters) for _ in range(num_blocks)])
        
        # 3. Policy Head: 
        # Tích chập 1x1 từ 128 -> 118 channels
        self.policy_conv = nn.Conv2d(filters, 118, kernel_size=1, bias=False)
        self.policy_bn = nn.BatchNorm2d(118)
        # Lưu ý: Softmax sẽ được thực thi trong C++ trên tập hợp các legal moves 
        # nên ở đây chúng ta chỉ xuất logits thô phẳng [batch_size, 10600].
        
        # 4. Value Head (WDL):
        # Tích chập 1x1 từ 128 -> 32 channels
        self.value_conv = nn.Conv2d(filters, 32, kernel_size=1, bias=False)
        self.value_bn = nn.BatchNorm2d(32)
        # Fully connected layer 1: 32 * 10 * 10 -> 128
        self.value_fc1 = nn.Linear(32 * 10 * 10, 128)
        # Fully connected layer 2: 128 -> 3 (Win, Draw, Loss)
        self.value_fc2 = nn.Linear(128, 3)
        self.softmax = nn.Softmax(dim=1)

    def forward(self, x):
        # x shape: [batch_size, 226, 10, 10]
        out = self.conv_in(x)
        out = self.bn_in(out)
        out = self.relu(out)
        
        out = self.backbone(out) # shape: [batch_size, 128, 10, 10]
        
        # Policy Head
        pol = self.policy_conv(out)
        pol = self.policy_bn(pol)
        pol = self.relu(pol)
        pol_flat = pol.reshape(-1, 11800) # shape: [batch_size, 11800]
        
        # Value Head (WDL)
        val = self.value_conv(out)
        val = self.value_bn(val)
        val = self.relu(val)
        val_flat = val.reshape(-1, 32 * 10 * 10) # shape: [batch_size, 3200]
        val_fc = self.value_fc1(val_flat)
        val_fc = self.relu(val_fc)
        val_logits = self.value_fc2(val_fc)      # shape: [batch_size, 3]
        val_wdl = self.softmax(val_logits)        # shape: [batch_size, 3]
        
        return pol_flat, val_wdl

def export_model():
    print("Initializing ChessNet10x10 model (10 blocks, 128 filters)...")
    model = ChessNet10x10(num_blocks=10, filters=128)
    model.eval() # đặt ở chế độ evaluation
    
    # Tạo dummy input với shape [batch_size=1, channels=226, height=10, width=10]
    dummy_input = torch.randn(1, 226, 10, 10)
    
    # Output file path
    output_filename = "weights_0_elo.onnx"
    
    print(f"Exporting model to {output_filename}...")
    torch.onnx.export(
        model,
        dummy_input,
        output_filename,
        export_params=True,
        opset_version=15, # ONNX opset version
        do_constant_folding=True,
        input_names=["input"],
        output_names=["policy", "value"],
        dynamic_axes={
            "input": {0: "batch_size"},
            "policy": {0: "batch_size"},
            "value": {0: "batch_size"}
        }
    )
    # Tự động gộp external weights (nếu có) thành file self-contained duy nhất
    import onnx
    try:
        onnx_model = onnx.load(output_filename)
        onnx.save(onnx_model, output_filename)
        data_file = output_filename + ".data"
        if os.path.exists(data_file):
            os.remove(data_file)
    except Exception as e:
        print(f"Error post-processing ONNX model: {e}")

    print("Model exported successfully!")
    file_size = os.path.getsize(output_filename) / (1024 * 1024)
    print(f"File size: {file_size:.2f} MB")

if __name__ == "__main__":
    export_model()
