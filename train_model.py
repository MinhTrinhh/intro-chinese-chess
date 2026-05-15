"""
Training script for the neural network model using self-play data.

Usage:
  python train_model.py --data-path data/combined_dataset_config2.pkl --epochs 50 --device cuda
"""

import argparse
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
from pathlib import Path
import pickle

from src.ml.model import create_model, save_checkpoint, count_parameters


def load_training_batch(pickle_path):
    print(f"Loading data from {pickle_path}...")
    with open(pickle_path, 'rb') as f:
        data = pickle.load(f)
    
    print(f"Loaded {len(data)} samples")
    
    # Unpack board states and labels
    X = np.array([sample[0] for sample in data], dtype=np.float32)  # Convert to float32
    y = np.array([sample[1] for sample in data], dtype=np.float32)  # Convert to float32
    
    print(f"X shape: {X.shape}, dtype: {X.dtype}")
    print(f"y shape: {y.shape}, dtype: {y.dtype}")
    print(f"y unique values: {np.unique(y)}")
    
    # Stats
    red_wins = (y > 0).sum()
    black_wins = (y < 0).sum()
    draws = (y == 0).sum()
    print(f"Label distribution - Red wins: {red_wins}, Black wins: {black_wins}, Draws: {draws}")
    
    return X, y


def train_epoch(model, train_loader, optimizer, loss_fn, device):
    """Train for one epoch."""
    model.train()
    total_loss = 0.0
    
    for batch_X, batch_y in train_loader:
        batch_X = batch_X.to(device)
        batch_y = batch_y.to(device)
        
        # Forward pass
        predictions = model(batch_X).squeeze()
        loss = loss_fn(predictions, batch_y)
        
        # Backward pass
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
    
    avg_loss = total_loss / len(train_loader)
    return avg_loss


def evaluate(model, val_loader, loss_fn, device):
    model.eval()
    total_loss = 0.0
    
    with torch.no_grad():
        for batch_X, batch_y in val_loader:
            batch_X = batch_X.to(device)
            batch_y = batch_y.to(device)
            
            predictions = model(batch_X).squeeze()
            loss = loss_fn(predictions, batch_y)
            total_loss += loss.item()
    
    avg_loss = total_loss / len(val_loader)
    return avg_loss


def main():
    parser = argparse.ArgumentParser(description="Train neural network on self-play data")
    
    # Data parameters
    parser.add_argument('--data-path', type=str, required=True, help='Path to pickle file with training data')
    parser.add_argument('--validation-split', type=float, default=0.2, help='Validation split ratio')
    
    # Training parameters
    parser.add_argument('--epochs', type=int, default=50, help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=64, help='Batch size')
    parser.add_argument('--learning-rate', type=float, default=0.001, help='Learning rate')
    parser.add_argument('--device', type=str, default='cuda', choices=['cuda', 'cpu'], help='Device to use')
    
    # Model parameters
    parser.add_argument('--hidden1', type=int, default=256, help='Size of first hidden layer')
    parser.add_argument('--hidden2', type=int, default=128, help='Size of second hidden layer')
    
    # Output parameters
    parser.add_argument('--output-dir', type=str, default='models', help='Directory to save checkpoint')
    parser.add_argument('--checkpoint-name', type=str, default='trained_model.pth', help='Checkpoint filename')
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("Neural Network Training - Self-Play Data")
    print("=" * 60)
    
    # Check device
    if args.device == 'cuda':
        if not torch.cuda.is_available():
            print("⚠️  CUDA not available, falling back to CPU")
            args.device = 'cpu'
        else:
            print(f"✓ Using GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("✓ Using CPU")
    
    # Load data
    print(f"\n[Loading Data]")
    X, y = load_training_batch(args.data_path)
    
    # Split train/validation
    n_samples = len(X)
    n_val = int(n_samples * args.validation_split)
    n_train = n_samples - n_val
    
    indices = np.random.permutation(n_samples)
    train_indices = indices[:n_train]
    val_indices = indices[n_train:]
    
    X_train, y_train = X[train_indices], y[train_indices]
    X_val, y_val = X[val_indices], y[val_indices]
    
    print(f"Train samples: {len(X_train)}, Val samples: {len(X_val)}")
    
    # Create data loaders
    train_dataset = TensorDataset(
        torch.from_numpy(X_train).float(),
        torch.from_numpy(y_train).float()
    )
    val_dataset = TensorDataset(
        torch.from_numpy(X_val).float(),
        torch.from_numpy(y_val).float()
    )
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False)
    
    # Create model
    print(f"\n[Model Architecture]")
    model = create_model(input_size=90, hidden1=args.hidden1, hidden2=args.hidden2)
    params = count_parameters(model)
    print(f"Input: 90")
    print(f"Hidden 1: {args.hidden1} (ReLU)")
    print(f"Hidden 2: {args.hidden2} (ReLU)")
    print(f"Output: 1 (Tanh, range [-1, 1])")
    print(f"Total parameters: {params:,}")
    
    model.to(args.device)
    
    # Loss function and optimizer
    loss_fn = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=args.learning_rate)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    
    # Training loop
    print(f"\n[Training]")
    print(f"Epochs: {args.epochs}")
    print(f"Batch size: {args.batch_size}")
    print(f"Learning rate: {args.learning_rate}")
    print("-" * 60)
    
    best_val_loss = float('inf')
    patience = 10
    patience_counter = 0
    
    for epoch in range(1, args.epochs + 1):
        train_loss = train_epoch(model, train_loader, optimizer, loss_fn, args.device)
        val_loss = evaluate(model, val_loader, loss_fn, args.device)
        scheduler.step()
        
        print(f"Epoch {epoch:3d}/{args.epochs} | Train Loss: {train_loss:.6f} | Val Loss: {val_loss:.6f}")
        
        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            # Save best model
            checkpoint_path = Path(args.output_dir) / args.checkpoint_name
            save_checkpoint(
                model, 
                checkpoint_path,
                metadata={
                    'epoch': epoch,
                    'train_loss': train_loss,
                    'val_loss': val_loss,
                    'params': params,
                }
            )
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"\n Early stopping at epoch {epoch} (no improvement for {patience} epochs)")
                break
    
    print("\n" + "=" * 60)
    print(f"Training completed!")
    print(f"Best validation loss: {best_val_loss:.6f}")
    print(f"Model saved to: {Path(args.output_dir) / args.checkpoint_name}")
    print("=" * 60)


if __name__ == '__main__':
    main()
