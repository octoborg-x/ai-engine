# W5 D5 — PyTorch training loop and inference

## Build
- `model.py`: custom `nn.Module` (Linear → ReLU → Linear)
- `train.py`: dataset / DataLoader, train/val split, manual loop with backward/step/zero_grad, validation with `torch.no_grad()`, inference on unseen data

## Interview answers

1. What does `backward()` calculate?
   It computes gradients of the loss with respect to all model parameters via backpropagation.

2. What does the optimizer actually update?
   It updates the model's weight and bias tensors using the computed gradients (e.g., SGD: `w = w - lr * grad`).

3. Why do we zero gradients?
   PyTorch accumulates gradients by default; zeroing prevents leftover gradients from previous batches from corrupting the update.

4. Why separate training and validation?
   Validation measures generalization on unseen data; using it for updates causes overfitting and invalid metrics.

5. What does `eval()` change?
   It sets the module to evaluation mode (disables dropout, uses running stats for BatchNorm/LayerNorm instead of batch stats).

6. Why disable gradients during inference?
   `torch.no_grad()` avoids building the computation graph, saving memory and compute; we don't need gradients for predictions.

7. What would indicate overfitting?
   Training loss keeps decreasing while validation loss stops improving or increases; validation accuracy stalls or drops.
