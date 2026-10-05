import numpy as np


def sigmoid(z):
    return 1 / (1 + np.exp(-z))


def sigmoid_derivative(z):
    s = sigmoid(z)
    return s * (1 - s)


def binary_cross_entropy(y_pred, y_true):
    eps = 1e-8
    y_pred = np.clip(y_pred, eps, 1 - eps)
    return -np.mean(y_true * np.log(y_pred) + (1 - y_true) * np.log(1 - y_pred))


class NeuralNetwork:
    def __init__(self, input_size, hidden_size, output_size):
        self.W1 = np.random.randn(input_size, hidden_size) * 0.5
        self.b1 = np.zeros((1, hidden_size))
        self.W2 = np.random.randn(hidden_size, output_size) * 0.5
        self.b2 = np.zeros((1, output_size))

    def forward(self, X):
        self.z1 = X @ self.W1 + self.b1
        self.a1 = sigmoid(self.z1)
        self.z2 = self.a1 @ self.W2 + self.b2
        self.a2 = sigmoid(self.z2)
        return self.a2

    def backward(self, X, y, output):
        m = X.shape[0]
        dz2 = output - y.reshape(-1, 1)
        dW2 = (self.a1.T @ dz2) / m
        db2 = np.sum(dz2, axis=0, keepdims=True) / m

        da1 = dz2 @ self.W2.T
        dz1 = da1 * sigmoid_derivative(self.z1)
        dW1 = (X.T @ dz1) / m
        db1 = np.sum(dz1, axis=0, keepdims=True) / m

        return {"W1": dW1, "b1": db1, "W2": dW2, "b2": db2}

    def update(self, grads, lr):
        self.W1 -= lr * grads["W1"]
        self.b1 -= lr * grads["b1"]
        self.W2 -= lr * grads["W2"]
        self.b2 -= lr * grads["b2"]


def train():
    np.random.seed(42)
    X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
    y = np.array([0, 1, 1, 0])

    nn = NeuralNetwork(input_size=2, hidden_size=4, output_size=1)
    epochs = 10000
    lr = 1.0
    print_every = 1000

    for epoch in range(1, epochs + 1):
        out = nn.forward(X)
        loss = binary_cross_entropy(out, y)
        if epoch % print_every == 0 or epoch == 1:
            print(f"Epoch {epoch:5d} | Loss: {loss:.6f}")

        grads = nn.backward(X, y, out)
        nn.update(grads, lr)

    final = nn.forward(X)
    preds = (final >= 0.5).astype(int).flatten()
    acc = np.mean(preds == y) * 100

    print("\nFinal predictions:", final.flatten())
    print("Predicted classes:", preds)
    print("True labels:     ", y)
    print(f"Accuracy: {acc:.0f}%")


if __name__ == "__main__":
    train()
