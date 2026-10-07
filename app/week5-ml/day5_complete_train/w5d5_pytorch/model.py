import torch
import torch.nn as nn


class BinaryClassifier(nn.Module):
    def __init__(self, in_features=3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_features, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
        )

    def forward(self, x):
        return self.net(x)
