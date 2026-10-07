import model
import torch
from torch.utils.data import DataLoader, Dataset, random_split


class TabularDataset(Dataset):
    def __init__(self, n=200):
        torch.manual_seed(42)
        self.X = torch.randn(n, 3)
        # binary target: roughly when x0 + x1 > 0
        self.y = (self.X[:, 0] + self.X[:, 1] > 0).float().unsqueeze(1)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


def main():
    dataset = TabularDataset(n=200)
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_ds, val_ds = random_split(
        dataset, [train_size, val_size], generator=torch.Generator().manual_seed(42)
    )

    train_loader = DataLoader(train_ds, batch_size=16, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=16)

    net = model.BinaryClassifier(in_features=3)
    criterion = torch.nn.BCEWithLogitsLoss()
    optimizer = torch.optim.SGD(net.parameters(), lr=0.05)

    for epoch in range(1, 21):
        net.train()
        train_losses = []
        for bx, by in train_loader:
            optimizer.zero_grad()
            pred = net(bx)
            loss = criterion(pred, by)
            loss.backward()
            optimizer.step()
            train_losses.append(loss.item())

        net.eval()
        val_losses = []
        correct = 0
        total = 0
        with torch.no_grad():
            for bx, by in val_loader:
                pred = net(bx)
                loss = criterion(pred, by)
                val_losses.append(loss.item())
                probs = torch.sigmoid(pred)
                preds = (probs >= 0.5).float()
                correct += (preds == by).sum().item()
                total += by.size(0)

        avg_train = sum(train_losses) / len(train_losses)
        avg_val = sum(val_losses) / len(val_losses)
        acc = correct / total
        print(
            f"epoch={epoch:02d} train_loss={avg_train:.4f} val_loss={avg_val:.4f} val_acc={acc:.3f}"
        )

    # inference on unseen samples
    net.eval()
    unseen = torch.tensor([[0.5, 0.5, -0.2], [-1.0, -0.8, 0.1]])
    with torch.no_grad():
        out = net(unseen)
        probs = torch.sigmoid(out)
        preds = (probs >= 0.5).float()
    print(
        "inference unseen:",
        probs.squeeze().tolist(),
        "preds:",
        preds.squeeze().tolist(),
    )


if __name__ == "__main__":
    main()
