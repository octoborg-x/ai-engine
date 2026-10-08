from torch import nn


class BinaryClassifier(nn.Module):
    def __init__(self, in_features=3, hidden=16):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_features, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 1),
        )

    def forward(self, x):
        return self.net(x)
