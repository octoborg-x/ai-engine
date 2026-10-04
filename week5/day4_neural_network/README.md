# Week 5 Day 4 — Neural Network from Scratch

No PyTorch. Just NumPy, so every piece of training is visible.

## What a neuron computes
- Weighted sum: z = Wx + b
- Activation (sigmoid): squashes z to (0, 1)

## Why activation is needed
Without it, stacking layers is just a linear map — can’t learn XOR. Sigmoid introduces non-linearity.

## Training loop (in my own words)
1. Forward pass: input flows through hidden → output; sigmoid at each layer.
2. Prediction: output is probability-like; threshold at 0.5 for class.
3. Loss: binary cross-entropy measures how far predictions are from true labels.
4. Gradient calculation: backprop uses chain rule to find how much each W/b contributed to error.
5. Parameter update: gradient descent shifts weights opposite to gradient (parameter -= lr * gradient).
6. Repeat: loop until loss drops and predictions match labels.

## Dataset
XOR — not linearly separable, so a hidden layer is required.

## Components implemented manually
- Neuron (weighted sum + sigmoid)
- Forward pass
- Binary cross-entropy loss
- Backpropagation / gradients
- Gradient descent optimizer
