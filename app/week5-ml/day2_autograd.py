"""Autograd and gradient descent demonstration using PyTorch."""

import torch

# 1. Parameters we want to learn
w = torch.tensor(2.0, requires_grad=True)
b = torch.tensor(1.0, requires_grad=True)

# 2. Training example
x = torch.tensor(3.0)
y_true = torch.tensor(10.0)

learning_rate = 0.01

for i in range(20):
    # Forward pass
    y_pred = w * x + b
    loss = (y_pred - y_true) ** 2

    # Backpropagation
    loss.backward()

    # Manual gradient-descent update (no optimization abstraction)
    with torch.no_grad():
        w -= learning_rate * w.grad
        b -= learning_rate * b.grad

    # Gradients accumulate; zero before next backward
    w.grad.zero_()
    b.grad.zero_()

    if (i + 1) % 5 == 0:
        print(
            f"iter {i + 1}: prediction={y_pred.item():.4f}, "
            f"loss={loss.item():.4f}, w={w.item():.4f}, b={b.item():.4f}"
        )

print("updated w:", w.item())
print("updated b:", b.item())
