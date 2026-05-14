"""
MLP Evaluator: Simple neural network for board position evaluation.

Architecture:
  Input (90) → Dense (256, ReLU) → Dense (128, ReLU) → Output (1, Tanh)
  
Output range: [-1, 1] via Tanh
  -1: very bad for red
  +1: very good for red
"""

import torch
import torch.nn as nn
from pathlib import Path


def create_model(input_size=90, hidden1=256, hidden2=128):
    model = nn.Sequential(
        nn.Linear(input_size, hidden1),
        nn.ReLU(),
        nn.Linear(hidden1, hidden2),
        nn.ReLU(),
        nn.Linear(hidden2, 1),
        nn.Tanh()  # output ∈ [-1, 1]
    )
    
    # Initialize weights (He initialization for ReLU)
    for module in model:
        if isinstance(module, nn.Linear):
            nn.init.kaiming_normal_(module.weight, mode='fan_in', nonlinearity='relu')
            nn.init.zeros_(module.bias)
    
    return model


def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def save_checkpoint(model, path, metadata=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    checkpoint = {
        'model_state': model.state_dict(),
        'metadata': metadata or {},
    }
    
    torch.save(checkpoint, path)
    print(f"✓ Model saved to {path}")


def load_checkpoint(path, device='cpu'):
    checkpoint = torch.load(path, map_location=device)
    
    model = create_model()
    model.load_state_dict(checkpoint['model_state'])
    model.to(device)
    print(f"✓ Model loaded from {path}")
    
    return model


def evaluate(model, board_tensor):
    with torch.no_grad():
        if board_tensor.dim() == 1:
            board_tensor = board_tensor.unsqueeze(0)
        
        score = model(board_tensor)
        return score.squeeze().item()


def evaluate_batch(model, batch_tensors):
    with torch.no_grad():
        scores = model(batch_tensors)
        return scores.squeeze()


def test_model():
    """
    Unit test: Create model, forward pass, save/load.
    """
    print("[TEST] MLP Evaluator")
    print("-" * 50)
    
    # Create model
    model = create_model(input_size=90, hidden1=256, hidden2=128)
    params = count_parameters(model)
    
    print(f"""
MLP Architecture:
  Input:      90
  Hidden 1:   256 (ReLU)
  Hidden 2:   128 (ReLU)
  Output:     1 (Tanh, range [-1, 1])
  Parameters: {params:,}
    """.strip())
    
    # Test single board
    board_tensor = torch.randn(90)
    score = evaluate(model, board_tensor)
    print(f"\n✓ Single board evaluation: {score:.4f} (in [-1, 1])")
    assert -1.0 <= score <= 1.0, f"Score {score} out of range [-1, 1]"
    
    # Test batch
    batch = torch.randn(16, 90)
    scores = evaluate_batch(model, batch)
    print(f"✓ Batch evaluation: shape {scores.shape}")
    assert scores.shape == (16,), f"Expected shape (16,), got {scores.shape}"
    assert torch.all((scores >= -1.0) & (scores <= 1.0)), "Some scores out of range"
    
    # Test forward pass
    x = torch.randn(32, 90)
    output = model(x)
    print(f"✓ Forward pass: input {x.shape} → output {output.shape}")
    assert output.shape == (32, 1), f"Expected shape (32, 1), got {output.shape}"
    
    # Test save/load
    checkpoint_path = "models/test_checkpoint.pth"
    save_checkpoint(model, checkpoint_path, metadata={"epoch": 0, "loss": 0.5})
    
    model_loaded = load_checkpoint(checkpoint_path)
    
    # Compare outputs
    with torch.no_grad():
        output_original = model(x)
        output_loaded = model_loaded(x)
    
    diff = torch.abs(output_original - output_loaded).max().item()
    print(f"✓ Save/Load: max difference {diff:.2e}")
    assert diff < 1e-6, f"Loaded model differs: {diff}"
    
    print("-" * 50)
    print("✅ All model tests passed!")


if __name__ == "__main__":
    # test_model()
    pass
